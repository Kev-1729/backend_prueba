# app/domain/ports/operation_repository.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.domain.models.invoice import Invoice
from app.infrastructure.persistence.models import Operacion

class OperationRepository(ABC):
    """
    Contrato final que define las operaciones con la base de datos PostgreSQL.
    """

    @abstractmethod
    def find_by_id(self, operation_id: str) -> Optional[Operacion]:
        """Busca una operación por su ID."""
        pass

    @abstractmethod
    def save_full_operation(self, metadata: dict, drive_url: str, invoices: List[Invoice], cavali_results_map: Dict[str, Any]) -> str:
        """
        Genera un ID único para la operación, y guarda la operación principal
        y todas sus facturas enriquecidas. Retorna el ID de la operación creada.
        """
        pass
    
    @abstractmethod
    def generar_siguiente_id_operacion(self) -> str:
        """
        Genera un ID de operación único y secuencial con el formato OP-YYYYMMDD-XXX.
        El contador XXX se reinicia cada día.
        """
        pass