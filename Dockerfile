# YT-Shorts-Dual-Panel-Agent Docker Container
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Crear directorios necesarios
RUN mkdir -p data/videos data/raw data/transcripts data/segments data/outputs logs

# Configurar permisos
RUN chmod +x *.py

# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV FLASK_ENV=production

# Exponer puertos
EXPOSE 8081 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8081/health || exit 1

# Script de inicio
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
