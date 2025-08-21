# YT-Shorts-Dual-Panel-Agent Docker Container
FROM ubuntu:22.04

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    ffmpeg \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Crear enlace simbólico para python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

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
# Health check usando puerto configurable (WEB_PORT) con fallback
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD bash -c 'curl -f http://localhost:${WEB_PORT:-8081}/health || exit 1'

# Script de inicio
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
