# NEXORA · Pipeline DataOps + IA
# Python 3.11 (Microsoft devcontainer base) — compatible con nube y local
FROM mcr.microsoft.com/devcontainers/python:3.11

# Evitar que Python escriba .pyc y forcé salida sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer directorio de trabajo
WORKDIR /workspace

# Copiar archivos de dependencias primero (caching)
COPY requirements.txt .
COPY nexora-ml/requirements.txt nexora-ml/requirements.txt

# Instalar dependencias unificadas del pipeline + módulo IA
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r nexora-ml/requirements.txt && \
    rm -rf /tmp/*

# Copiar el resto del código
COPY . .

# Crear directorios de logs si no existen
RUN mkdir -p IA_Proyecto/logs nexora-ml/logs

# Puerto para Streamlit dashboard (opcional)
EXPOSE 8501

# Comando por defecto: ejecutar el pipeline
CMD ["python", "pipeline.py"]
