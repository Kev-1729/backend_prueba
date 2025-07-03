# app/domain/ports/invoice_validator.py
from abc import ABC, abstractmethod
from typing import List, Dict

class InvoiceValidator(ABC):
    """Puerto para la validación de facturas con un servicio externo."""
    @abstractmethod
    def validate_invoices_in_batches(self, xml_files_content: List[Dict]) -> List[dict]:
        """
        Envía los XML a validar en lotes.
        `xml_files_content` es una lista de dicts: [{'filename': str, 'content_bytes': bytes}]
        """
        pass