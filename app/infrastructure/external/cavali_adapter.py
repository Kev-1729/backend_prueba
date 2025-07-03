# app/infrastructure/external/cavali_adapter.py
import os
import requests
import base64
import time
from typing import List, Dict, Any
from dotenv import load_dotenv
from app.domain.ports.invoice_validator import InvoiceValidator

load_dotenv()

#Modificacion, tokend pedir cada Hora 
class CavaliAdapter(InvoiceValidator):
    """
    Adaptador para la API de Cavali (Factrack), que envía facturas en lotes
    y consulta su estado, manejando errores de forma robusta.
    """
    def __init__(self):
        self.client_id = os.getenv("CAVALI_CLIENT_ID")
        self.client_secret = os.getenv("CAVALI_CLIENT_SECRET")
        self.scope = os.getenv("CAVALI_SCOPE")
        self.token_url = os.getenv("CAVALI_TOKEN_URL")
        self.api_key = os.getenv("CAVALI_API_KEY")
        self.block_url = os.getenv("CAVALI_BLOCK_URL")
        self.status_url = os.getenv("CAVALI_STATUS_URL")
        self.BATCH_SIZE = 30



    def _get_access_token(self) -> str:
        """
        Obtiene un token de acceso de la API de Cavali.
        """
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        print("Obteniendo token de Cavali...")
        try:
            response = requests.post(self.token_url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            print("Token de Cavali obtenido exitosamente.")
            return response.json()["access_token"]
        except requests.exceptions.RequestException as e:
            print(f"ERROR al obtener token de Cavali: {e}")
            if e.response is not None:
                print(f"Detalle del error: {e.response.text}")
            raise

    def _send_batch(self, batch: List[Dict[str, Any]], headers: Dict[str, str], batch_number: int) -> Dict[str, Any]:
        """
        Envía un único lote a Cavali (paso 1) y consulta su estado (paso 2).
        """
        resultado_bloqueo = None
        try:
            # PASO 1: Enviar el lote para bloqueo
            invoice_xml_list = [
                {"name": f['filename'], "fileXml": base64.b64encode(f['content_bytes']).decode("utf-8")}
                for f in batch
            ]
            process_number = int(time.time()) + batch_number
            payload_bloqueo = {
                "processDetail": {"processNumber": process_number},
                "invoiceXMLDetail": {"invoiceXML": invoice_xml_list}
            }
            
            print(f"Enviando Lote #{batch_number} ({len(batch)} facturas) a Cavali...")
            response_bloqueo = requests.post(self.block_url, json=payload_bloqueo, headers=headers, timeout=60)
            response_bloqueo.raise_for_status()
            resultado_bloqueo = response_bloqueo.json()
            print(f"Respuesta de Bloqueo para Lote #{batch_number}: {resultado_bloqueo}")

            id_proceso = resultado_bloqueo.get("response", {}).get("idProceso")
            if not id_proceso:
                raise ValueError("La respuesta de bloqueo de Cavali no contiene 'idProceso'.")

        except requests.exceptions.RequestException as e:
            print(f"Error en el Paso 1 (Bloqueo) para el Lote #{batch_number}: {e}")
            return {"bloqueo_resultado": {"status": "error", "message": str(e)}, "estado_resultado": None}
        
        # PASO 2: Consultar el estado del proceso
        try:
            payload_estado = {"ProcessFilter": {"idProcess": id_proceso}}
            print(f"Consultando estado del proceso {id_proceso} (Lote #{batch_number})...")
            response_estado = requests.post(self.status_url, json=payload_estado, headers=headers, timeout=30)
            response_estado.raise_for_status()
            resultado_estado = response_estado.json()
            print(f"Respuesta de Estado para Lote #{batch_number}: {resultado_estado}")
        
        except requests.exceptions.RequestException as e:
            print(f"Error en el Paso 2 (Estado) para el Lote #{batch_number}: {e}")
            return {"bloqueo_resultado": resultado_bloqueo, "estado_resultado": {"status": "error", "message": str(e)}}

        return {
            "bloqueo_resultado": resultado_bloqueo,
            "estado_resultado": resultado_estado
        }

    def validate_invoices_in_batches(self, xml_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Divide la lista completa de XML en lotes y procesa cada uno.
        Retorna una lista con todas las respuestas combinadas de Cavali.
        """

        if not xml_files:
            print("Lote de XML vacío. No se envía a Cavali.")
            return [{"status": "skipped", "message": "No XML files to process."}]

        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Dividir la lista de archivos en lotes (chunks)
        batches = [xml_files[i:i + self.BATCH_SIZE] for i in range(0, len(xml_files), self.BATCH_SIZE)]
        all_results = []
        
        print(f"Total de {len(xml_files)} XML a procesar en {len(batches)} lote(s) de hasta {self.BATCH_SIZE} c/u.")

        for i, batch in enumerate(batches):
            batch_result = self._send_batch(batch, headers, i + 1)
            all_results.append(batch_result)
            if i < len(batches) - 1:
                print("Siguiente lote...")
        
        return all_results
