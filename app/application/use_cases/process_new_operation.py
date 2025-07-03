# app/application/use_cases/process_new_operation.py
import os
import shutil
from typing import List, Dict, Any
from datetime import datetime, timedelta
from lxml import etree
from collections import defaultdict

from app.domain.ports.file_storage import FileStorage
from app.domain.ports.invoice_validator import InvoiceValidator
from app.domain.ports.task_manager import TaskManager
from app.domain.ports.notification import Notification
from app.domain.ports.operation_repository import OperationRepository

# Importaciones de Modelos de Dominio y otros
from app.domain.models.invoice import Invoice
from lxml import etree
from datetime import datetime, timedelta
import logging

class ProcessNewOperationUseCase:
    def __init__(
        self,
        operation_repo: OperationRepository,
        file_storage: FileStorage,
        invoice_validator: InvoiceValidator,
        task_manager: TaskManager,
        notification_service: Notification
    ):
        self.operation_repo = operation_repo
        self.file_storage = file_storage
        self.invoice_validator = invoice_validator
        self.task_manager = task_manager
        self.notification_service = notification_service


    def _parse_xml_files(self, xml_files: List[Dict[str, Any]]) -> List[Invoice]:
            """
            Parsea una lista de archivos XML y los transforma en modelos de dominio `Invoice`.
            """
            parsed_data: List[Invoice] = []
            
            for xml_file in xml_files:
                filename = xml_file.get('filename', 'N/A')
                xml_content_bytes = xml_file.get('content_bytes')

                if not xml_content_bytes:
                    print(f"ADVERTENCIA: Archivo {filename} está vacío. Omitiendo.")
                    continue

                try:
                    try:
                        xml_content = xml_content_bytes.decode('iso-8859-1')
                        root = etree.fromstring(xml_content.encode('utf-8'))
                    except Exception:
                        xml_content = xml_content_bytes.decode('utf-8').lstrip('\ufeff')
                        root = etree.fromstring(xml_content.encode('utf-8'))

                    ns = {
                        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
                        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
                    }

                    def find_text(xpath, default=None):
                        element = root.find(xpath, ns)
                        return element.text.strip() if element is not None and element.text is not None else default

                    fecha_emision_str = find_text('.//cbc:IssueDate')

                    total_factura = float(find_text('.//cac:LegalMonetaryTotal/cbc:PayableAmount', '0'))
                    monto_detraccion = float(find_text(".//cac:PaymentTerms[cbc:ID='Detraccion']/cbc:PaymentPercent", '0'))
                    monto_neto = total_factura  * (100 - monto_detraccion)/100

                    forma_pago = find_text(".//cac:PaymentTerms[cbc:ID='FormaPago']/cbc:PaymentMeansID")

                    fecha_emision_dt = datetime.strptime(fecha_emision_str, '%Y-%m-%d') if fecha_emision_str else None
                    fecha_vencimiento_str = find_text('.//cac:PaymentTerms/cbc:PaymentDueDate')

                    
                    fecha_vencimiento_dt = None
                    if fecha_vencimiento_str:
                        fecha_vencimiento_dt = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d')
                    elif forma_pago and forma_pago.lower() == 'contado' and fecha_emision_dt:
                        fecha_vencimiento_dt = fecha_emision_dt + timedelta(days=60)
                    elif fecha_emision_dt:
                        fecha_vencimiento_dt = fecha_emision_dt

                    moneda_element = root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns)
                    moneda = moneda_element.get('currencyID', 'N/A') if moneda_element is not None else 'N/A'

                    factura_info_dict = {
                        "document_id": find_text('./cbc:ID'),
                        "issue_date": fecha_emision_dt,
                        "due_date": fecha_vencimiento_dt,
                        "currency": moneda,
                        "total_amount": total_factura,
                        "net_amount": monto_neto,
                        "debtor_name": find_text('.//cac:AccountingCustomerParty//cac:PartyLegalEntity/cbc:RegistrationName'),
                        "debtor_ruc": find_text('.//cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID'),
                        "client_name": find_text('.//cac:AccountingSupplierParty//cac:PartyLegalEntity/cbc:RegistrationName'),
                        "client_ruc": find_text('.//cac:AccountingSupplierParty//cac:PartyIdentification/cbc:ID')
                    }
                    
                    invoice_obj = Invoice(**factura_info_dict)
                    parsed_data.append(invoice_obj)

                except Exception as e:
                    print(f"ADVERTENCIA: No se pudo parsear el archivo {filename}. Error: {e}")
                    
            return parsed_data

    def execute(self, operation_id: str, metadata: dict, temp_folder_path: str, all_filenames: List[str]):
        """
        Orquesta el flujo principal: procesa, ejecuta integraciones,
        guarda en la BD
        """
        try:
            # --- PASO 1: PREPARACIÓN DE DATOS ---
            print(f"[{operation_id}] Iniciando preparación de datos...")
            xml_filenames = [f for f in all_filenames if f.lower().endswith('.xml')]
            pdf_filenames = [f for f in all_filenames if f.lower().endswith('.pdf')]
            xml_content = [{'filename': f, 'content_bytes': open(os.path.join(temp_folder_path, f), 'rb').read()} for f in xml_filenames]
            
            invoices = self._parse_xml_files(xml_content)
            if not invoices:
                raise ValueError("No se pudo extraer información de ningún XML.")
            
            pdf_attachments = [{'filename': f, 'content': open(os.path.join(temp_folder_path, f), 'rb').read()} for f in pdf_filenames]

            # (Estas pueden ser optimizadas para correr en paralelo en el futuro)
            print(f"[{operation_id}] Ejecutando integraciones externas...")
            drive_url = self.file_storage.archive_operation_files(operation_id, temp_folder_path, all_filenames)
            cavali_responses = self.invoice_validator.validate_invoices_in_batches(xml_content)
            
            self.task_manager.create_operation_card(
                operation_id=operation_id,
                client_name=invoices[0].client_name,
                debtors_info={inv.debtor_ruc: inv.debtor_name for inv in invoices},
                operation_amounts=defaultdict(float, {inv.currency: inv.total_amount for inv in invoices}),
                initials=metadata.get('user_initials', 'CE'),
                tasa=metadata.get('tasaOperacion', 0.0),
                comision=metadata.get('comision', 0.0),
                drive_folder_url=drive_url,
                pdf_attachments=pdf_attachments,
                errors=[]
            )
            
            self.notification_service.send_confirmation_email(
                recipient='kevin.tupac@capitalexpress.cl',
                operation_id=operation_id,
                invoices=invoices,
                attachments=pdf_attachments
            )
            print(f"[{operation_id}] Integraciones externas completadas.")

            # 3. Consolidar la respuesta de Cavali
            cavali_results_map = {}
            for batch_result in cavali_responses:
                estado_res = batch_result.get("estado_resultado", {}).get("response", {}).get("Process", {})
                invoice_list = estado_res.get("ProcessInvoiceDetail", {}).get("Invoice", [])
                for inv_res in invoice_list:
                    doc_id = f"{inv_res.get('serie')}-{inv_res.get('numeration')}"
                    cavali_results_map[doc_id] = {
                        "message": inv_res.get("message"),
                        "process_id": str(estado_res.get("idProcess"))
                    }
            

            
             # 4. PASO FINAL: Guardar en la Base de Datos
            logging.info(f"[{operation_id}] Paso 4: Llamando al repositorio para guardar en la base de datos.")
            # --- INICIO DE LA SOLUCIÓN ---
            self.operation_repo.save_full_operation(
                metadata=metadata,
                drive_url=drive_url,
                invoices=invoices,
                cavali_results_map = cavali_results_map
            )
            # --- FIN DE LA SOLUCIÓN ---
            logging.info(f"[{operation_id}] El método save_full_operation del repositorio ha terminado.")

        except Exception as e:
            print(f"ERROR CRÍTICO en el caso de uso para la operación {operation_id}: {e}")
            raise