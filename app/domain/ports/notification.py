# app/domain/ports/notification.py
from abc import ABC, abstractmethod
from typing import List, Dict
from app.domain.models.invoice import Invoice

class Notification(ABC):
    """Puerto para el envío de notificaciones (Gmail)."""
    @abstractmethod
    def send_confirmation_email(self, recipient: str, operation_id: str, invoice_data: List[Invoice], attachments: List[Dict]) -> dict:
        """
        Compone y envía el correo de confirmación.
        `attachments` es una lista de dicts: [{'filename': str, 'content': bytes}]
        """
        pass