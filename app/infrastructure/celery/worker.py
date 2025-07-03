import os
import shutil
from celery import Celery
from typing import List
import logging

# --- ✅ NUEVA CONFIGURACIÓN DE CELERY PARA GOOGLE CLOUD PUB/SUB ---

# 1. El broker ahora es 'pubsub://'. Este es el protocolo para el transport de Celery.
CELERY_BROKER_URL = "pubsub://"

# 2. Leemos el nombre del TEMA de Pub/Sub desde una variable de entorno.
#    Tu API publicará las tareas en este tema.
CELERY_PUBSUB_TOPIC = os.environ.get("CELERY_PUBSUB_TOPIC", "factoring-operations-capitalexpress")

# 3. Inicializamos la aplicación Celery con la nueva configuración.
celery_app = Celery(
    'tasks',
    broker=CELERY_BROKER_URL,
    backend=None  # Pub/Sub no funciona como backend de resultados.
)

# 4. Añadimos las opciones de transporte específicas para Pub/Sub.
celery_app.conf.update(
    # Opciones clave para el broker
    broker_transport_options={
        # Tiempo en segundos que una tarea puede estar "en proceso" antes de que
        # Pub/Sub la vuelva a entregar. Ajústalo a la duración MÁXIMA de tus tareas.
        'visibility_timeout': 600,

        # El nombre del tema de Pub/Sub que escuchará este worker.
        'topic': CELERY_PUBSUB_TOPIC,

        # Celery creará una suscripción al tema con este prefijo.
        # No necesitas crear la suscripción manualmente.
        'subscription_name_prefix': 'celery-worker-sub'
    },
    # Es una buena práctica ignorar los resultados si no los vas a usar.
    task_ignore_result=True
)

# --- FIN DE LA NUEVA CONFIGURACIÓN ---


# El resto de tu código y lógica de negocio permanece exactamente igual.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s')

from app.application.use_cases.process_new_operation import ProcessNewOperationUseCase
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.operation_repository_adapter import PostgreSQLOperationRepository
from app.infrastructure.external.google_drive_adapter import GoogleDriveAdapter
from app.infrastructure.external.cavali_adapter import CavaliAdapter
from app.infrastructure.external.trello_adapter import TrelloAdapter
from app.infrastructure.external.gmail_adapter import GmailAdapter


@celery_app.task(name="tasks.process_operation_workflow")
def process_operation_workflow(operation_id: str, metadata: dict, temp_folder_path: str, all_filenames: List[str]):
    logging.info(f"[{operation_id}] >>> INICIO DE LA TAREA.")
    db_session = SessionLocal()
    try:
        use_case = ProcessNewOperationUseCase(
            operation_repo=PostgreSQLOperationRepository(db_session),
            file_storage=GoogleDriveAdapter(),
            invoice_validator=CavaliAdapter(),
            task_manager=TrelloAdapter(),
            notification_service=GmailAdapter()
        )
        logging.info(f"[{operation_id}] Ejecutando el caso de uso principal...")
        use_case.execute(operation_id, metadata, temp_folder_path, all_filenames)

        logging.warning(f"[{operation_id}] === A punto de ejecutar db_session.commit() ===")
        db_session.commit()
        logging.info(f"[{operation_id}] ¡ÉXITO! Commit ejecutado. Los datos están en PostgreSQL.")
    except Exception as e:
        logging.error(f"[{operation_id}] ¡ERROR! Se ha capturado una excepción. Iniciando rollback.", exc_info=True)
        db_session.rollback()
        raise
    finally:
        logging.info(f"[{operation_id}] Cerrando sesión de base de datos.")
        db_session.close()
        if os.path.exists(temp_folder_path):
            shutil.rmtree(temp_folder_path)
        logging.info(f"[{operation_id}] Directorio temporal eliminado.")