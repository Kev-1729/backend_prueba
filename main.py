# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importamos los routers de la capa de infraestructura
from app.infrastructure.api.routers import operations_router

app = FastAPI(
    title="API de Procesamiento de Operaciones de Factoring",
    description="Sistema para procesar operaciones de factoring de forma asíncrona.",
    version="4.0.0-DDD"
)

# Configuración de CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(operations_router.router)


@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "ok", "message": "Bienvenido a la API de Capital Express"}