# app/domain/ports/task_manager.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class TaskManager(ABC):
    """
    Puerto actualizado para la gestión de tareas en Trello,
    con parámetros específicos de la operación de factoring.
    """

    @abstractmethod
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
        errors: List[str] # Para registrar posibles errores del proceso
    ) -> str:
        """
        Crea una nueva tarjeta en Trello para la operación.

        Retorna:
            str: La URL de la tarjeta de Trello creada.
        """
        pass