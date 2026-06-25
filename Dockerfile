# NEXORA · Servicio de Inteligencia Predictiva (FastAPI) + Pipeline DataOps
# Imagen ligera para Render Web Service — compatible con nube y local.
FROM python:3.11-slim

# Evitar .pyc y forzar salida sin buffer (logs en tiempo real en Render).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Copiar archivos de dependencias primero (aprovecha la caché de capas).
COPY requirements.txt .
COPY nexora-ml/requirements.txt nexora-ml/requirements.txt

# Instalar dependencias del pipeline + módulo IA + API.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r nexora-ml/requirements.txt

# Copiar el resto del código.
COPY . .

# Crear directorios de logs/artefactos si no existen.
RUN mkdir -p IA_Proyecto/logs nexora-ml/logs nexora-ml/models nexora-ml/reports

# Puerto del servicio web (Render inyecta $PORT en tiempo de ejecución).
EXPOSE 8000

# Levantar la API. ${PORT:-8000} permite local (8000) y Render (puerto dinámico).
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
