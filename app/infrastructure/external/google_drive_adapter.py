# app/infrastructure/external/google_drive_adapter.py
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from app.domain.ports.file_storage import FileStorage
from .google_auth import get_google_credentials
import config
from typing import List

class GoogleDriveAdapter(FileStorage):
    """
    Implementación del adaptador de Google Drive que sube archivos
    de forma secuencial para garantizar la máxima estabilidad en entornos
    como Celery.
    """
    def __init__(self):
        creds = get_google_credentials()
        self.service = build('drive', 'v3', credentials=creds)

    def archive_operation_files(self, operation_id: str, local_folder_path: str, all_filenames: List[str]) -> str:
        """
        Crea una carpeta para la operación y sube todos los archivos
        uno por uno para asegurar la estabilidad del proceso.
        """
        print(f"[{operation_id}] Iniciando subida SECUENCIAL a Google Drive...")
        
        # 1. Crear la carpeta principal (esto no cambia)
        xml_base_name = next((fn for fn in all_filenames if fn.lower().endswith('.xml')), "operacion").split('.')[0]
        folder_name = f"Operacion_{xml_base_name}_{operation_id[:6]}"
        
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [config.DRIVE_PARENT_FOLDER_ID]
        }
        folder = self.service.files().create(body=folder_metadata, fields='id, webViewLink').execute()
        folder_id = folder.get('id')
        folder_url = folder.get('webViewLink')
        print(f"[{operation_id}] Carpeta '{folder_name}' creada. ID: {folder_id}")

        # 2. Subir cada archivo en un bucle simple y secuencial
        total_files = len(all_filenames)
        print(f"[{operation_id}] Se subirán {total_files} archivos uno por uno. Esto puede tardar...")

        for i, filename in enumerate(all_filenames):
            file_path = os.path.join(local_folder_path, filename)
            
            if os.path.exists(file_path):
                print(f"[{operation_id}] Subiendo archivo {i+1}/{total_files}: {filename}...")
                try:
                    file_metadata = {'name': filename, 'parents': [folder_id]}
                    media = MediaFileUpload(file_path, resumable=True)
                    
                    self.service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id' # Solo pedimos el ID, no necesitamos más
                    ).execute()
                except Exception as e:
                    # Si un archivo falla, registramos el error pero continuamos con los demás
                    print(f"ADVERTENCIA: Falló la subida de {filename}. Error: {e}")
            else:
                 print(f"ADVERTENCIA: El archivo {filename} no fue encontrado en la ruta temporal. Omitiendo.")

        print(f"[{operation_id}] Proceso de subida secuencial completado.")
            
        return folder_url