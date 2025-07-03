# ---- Etapa 1: "Builder" ----
# En esta etapa, instalamos las dependencias. Usamos una imagen completa de Python.
FROM python:3.11-slim as builder

# Establecemos el directorio de trabajo dentro del contenedor.
WORKDIR /usr/src/app

# Configuramos variables de entorno para Python.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copiamos solo el archivo de requerimientos primero.
# Esto aprovecha el caché de Docker: si no cambias los requerimientos,
# esta capa no se reconstruirá, haciendo los builds más rápidos.
COPY requirements.txt .

# Instalamos las dependencias.
RUN pip install --no-cache-dir -r requirements.txt


# ---- Etapa 2: "Final" ----
# Esta es la etapa que crea la imagen final que desplegarás.
# Partimos de la misma imagen base para mantener la consistencia.
FROM python:3.11-slim

# Creamos un usuario no-root para correr la aplicación.
# ¡Esto es una práctica de seguridad muy importante!
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser

# Copiamos las dependencias instaladas desde la etapa "builder".
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiamos el código fuente de la aplicación.
# Se copia la carpeta 'app' y el archivo 'main.py' al directorio de trabajo.
COPY app/ ./app
COPY main.py .

# Damos la propiedad del directorio al nuevo usuario.
RUN chown -R appuser:appuser /home/appuser

# Cambiamos al usuario no-root.
USER appuser

# Exponemos el puerto en el que correrá la aplicación dentro del contenedor.
EXPOSE 8000

# Definimos el comando para ejecutar la aplicación usando Gunicorn.
# Este es el estándar de producción para aplicaciones ASGI/WSGI como FastAPI.
# Se puede sobreescribir en Cloud Run, pero es bueno tener un default.
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "main:app"]