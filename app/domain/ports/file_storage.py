# app/domain/ports/file_storage.py
from abc import ABC, abstractmethod
from typing import Dict, List

class FileStorage(ABC):
    """Puerto para el almacenamiento de archivos en la nube."""
    @abstractmethod
    def archive_operation_files(self, operation_id: str, local_folder_path: str, all_filenames: List[str]) -> str:
        """
        Crea una carpeta para la operación y sube todos los archivos.
        Retorna la URL de la carpeta creada.
        """
        pass