# app/infrastructure/external/trello_adapter.py
import os
import requests
import datetime
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from app.domain.ports.task_manager import TaskManager

load_dotenv()

class TrelloAdapter(TaskManager):
    def __init__(self):
        self.api_key = os.getenv("TRELLO_API_KEY")
        self.api_token = os.getenv("TRELLO_API_TOKEN")
        self.list_id = os.getenv("TRELLO_LIST_ID")
        self.label_ids_str = os.getenv("TRELLO_LABEL_IDS", "")

        if not all([self.api_key, self.api_token, self.list_id]):
            raise ValueError("Faltan variables de entorno para Trello (API_KEY, API_TOKEN, LIST_ID)")

    def _format_number(self, num: float) -> str:
        return "{:,.2f}".format(num)

    def _sanitize_name(self, name: str) -> str:
        return name.strip() if name else "—"

    def create_operation_card(
        self,
        operation_id: str,
        client_name: str,
        debtors_info: Dict[str, str],
        operation_amounts: Dict[str, float],
        initials: str,
        tasa: float,
        comision: float,
        drive_folder_url: str,
        pdf_attachments: List[Dict[str, Any]],
        errors: List[str] = []
    ) -> str:
        print("Creando tarjeta en Trello con formato detallado...")
        
        current_date = datetime.datetime.now().strftime('%d.%m')
        debtors_str = ', '.join(self._sanitize_name(name) for name in debtors_info.values() if name) or 'Ninguno'
        amount_str = ', '.join(f"{currency} {self._format_number(amount)}" for currency, amount in operation_amounts.items()) or "0.00"

        card_title = f"🤖 {current_date} // CLIENTE: {self._sanitize_name(client_name)} // DEUDOR: {debtors_str} // MONTO: {amount_str} // {initials} // OP: {operation_id[:8]}"

        debtors_markdown = '\n'.join(f"- RUC {ruc}: {self._sanitize_name(name)}" for ruc, name in debtors_info.items()) or '- Ninguno'

        card_description = (
            f"**ID Operación:** {operation_id}\n\n"
            f"**Deudores:**\n{debtors_markdown}\n\n"
            f"**Tasa:** {tasa}%\n"
            f"**Comisión:** {comision}\n"
            f"**Monto Operación:** {amount_str}\n\n"
            f"**Carpeta Drive:** {drive_folder_url}\n\n"
            f"**Errores:** {', '.join(errors) if errors else 'Ninguno'}"
        )
        
        url_card = "https://api.trello.com/1/cards"
        
        auth_params = {
            'key': self.api_key,
            'token': self.api_token
        }
        
        card_payload = {
            'idList': self.list_id,
            'name': card_title,
            'desc': card_description,
            'pos': 'bottom',
            'idLabels': self.label_ids_str
        }
        
        try:
            response = requests.post(url_card, params=auth_params, json=card_payload)
            response.raise_for_status()
            card_data = response.json()
            card_id = card_data['id']
            card_url = card_data['url']
            print(f"Tarjeta creada exitosamente: {card_url}")

            if pdf_attachments:
                url_attachment = f"https://api.trello.com/1/cards/{card_id}/attachments"
                for pdf in pdf_attachments:
                    files = {'file': (pdf['filename'], pdf['content'], 'application/pdf')}
                    requests.post(url_attachment, params=auth_params, files=files)
                    print(f"Adjuntado {pdf['filename']} a la tarjeta de Trello.")

            return card_url

        except requests.exceptions.HTTPError as e:
            error_text = e.response.text
            print(f"Error HTTP al crear la tarjeta en Trello: {error_text}")
            raise ValueError(f"Error de Trello: {error_text}") from e
        except json.JSONDecodeError:
            print(f"Error al decodificar la respuesta de Trello (no era JSON válido). Respuesta recibida: {response.text}")
            raise ValueError(f"Respuesta inválida de Trello: {response.text}")
        except Exception as e:
            print(f"Error inesperado al crear tarjeta en Trello: {e}")
            raise
