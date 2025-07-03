# ---- Etapa 1: "Builder" ----
FROM python:3.11-slim as builder
WORKDIR /usr/src/app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Etapa 2: "Final" ----
FROM python:3.11-slim
WORKDIR /home/appuser
RUN useradd --create-home --shell /bin/bash appuser

# Copiamos las dependencias
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiamos el código
COPY app/ ./app
COPY main.py .

# ---- ✅ LÍNEA NUEVA Y CRUCIAL ----
# Le decimos a Python que incluya el directorio de trabajo actual
# al buscar módulos. Esto permite que "import app.infrastructure" funcione.
ENV PYTHONPATH /home/appuser
# -----------------------------------

RUN chown -R appuser:appuser /home/appuser
USER appuser

EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "main:app"]