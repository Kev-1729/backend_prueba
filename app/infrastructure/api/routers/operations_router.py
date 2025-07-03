# app/infrastructure/api/routers/operations_router.py
from fastapi import APIRouter, Form, File, UploadFile, HTTPException
from typing import List
import uuid
import json
import os
import shutil
# Importamos la instancia de Celery, no la tarea específica
from app.infrastructure.celery.worker import celery_app

router = APIRouter(prefix="/api/v1/operaciones", tags=["Operaciones"])
TEMP_UPLOADS_DIR = "/tmp"

@router.post("/", status_code=202, summary="Crear una nueva operación de procesamiento")
async def create_operation(
    metadata: str = Form(..., description="Metadatos de la operación en formato JSON."),
    xml_files: List[UploadFile] = File(..., description="Archivos XML de las facturas."),
    pdf_files: List[UploadFile] = File(..., description="Archivos PDF de las facturas."),
    respaldo_files: List[UploadFile] = File(..., description="Otros archivos de respaldo de la operación.")
):
    """
    Recibe los archivos de una operación, los guarda temporalmente y
    lanza una tarea en segundo plano para su procesamiento completo.
    """
    operation_id = str(uuid.uuid4())
    operation_temp_path = os.path.join(TEMP_UPLOADS_DIR, operation_id)
    os.makedirs(operation_temp_path, exist_ok=True)
    
    # Combinamos todas las listas de archivos en una sola para procesarla
    all_files = xml_files + pdf_files + respaldo_files
    saved_filenames = []

    try:
        for file in all_files:
            if not file.filename or ".." in file.filename or "/" in file.filename:
                raise HTTPException(status_code=400, detail=f"Nombre de archivo inválido: {file.filename}")
            
            file_path = os.path.join(operation_temp_path, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_filenames.append(file.filename)
        
        celery_app.send_task(
            'tasks.process_operation_workflow',
            args=[
                operation_id,
                json.loads(metadata),
                operation_temp_path,
                saved_filenames
            ]
        )

        return {"status": "processing_queued", "operation_id": operation_id}
    except Exception as e:
        if os.path.exists(operation_temp_path):
            shutil.rmtree(operation_temp_path)
        raise HTTPException(status_code=500, detail=str(e))