#!/bin/bash

# 🚀 Script Final - Activar YT-Shorts en el Servidor
set -e

echo "🚀 Activando YT-Shorts en el servidor..."
echo "========================================="

SERVER_IP="100.87.242.53"
SERVER_USER="germanmallo"
SERVER_PASSWORD="0301"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Función para ejecutar comandos remotos
remote_exec() {
    sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "$1"
}

log_info "1. Creando archivo .env en el servidor..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    
    # Crear .env basado en .env.example con configuraciones para el servidor
    cat > .env << 'EOF'
# Web Interface
WEB_PORT=8090

# YouTube API Configuration (reemplaza con tus credenciales reales)
YOUTUBE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com  
YOUTUBE_CLIENT_SECRET=your_client_secret_here
YOUTUBE_SCOPES=https://www.googleapis.com/auth/youtube.upload
YOUTUBE_REDIRECT_URI=http://100.87.242.53:8090/callback

# OpenAI API (agrega tu clave real cuando la tengas)
# OPENAI_API_KEY=sk_tu_clave_aqui

# Timezone Configuration
TZ=Europe/Madrid

# Whisper Configuration
WHISPER_MODEL=base
WHISPER_DEVICE=cpu

# Pipeline Configuration
MAX_CLIPS_PER_VIDEO=3
MIN_CLIP_DURATION=20
MAX_CLIP_DURATION=60
TARGET_FPS=30
PIPELINE_ENABLED=true
AUTO_DISCOVER_ENABLED=false
AUTO_PROCESS_ENABLED=false
AUTO_PUBLISH_ENABLED=false

# Publishing Schedule (24h format)
PUBLISH_TIMES=10:00,22:00
PUBLISH_ENABLED=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=data/logs/pipeline.log

# Storage paths (relative to project root)
RAW_PODCAST_DIR=data/raw/podcast
RAW_BROLL_DIR=data/raw/broll
NORMALIZED_DIR=data/normalized
TRANSCRIPTIONS_DIR=data/transcriptions
SEGMENTS_DIR=data/segments
COMPOSITES_DIR=data/composites
ASSETS_DIR=assets

# Database
DATABASE_PATH=data/pipeline.db

# Development
DEBUG=false
SKIP_DOWNLOAD=false
FORCE_REPROCESS=false

# Flask
FLASK_ENV=production
PYTHONPATH=./src
EOF
    
    echo 'Archivo .env creado'
"
log_success "Archivo .env configurado"

log_info "2. Inicializando base de datos..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    source venv/bin/activate
    export PYTHONPATH=./src
    python3 -c \"from src.pipeline.db import PipelineDB; PipelineDB()\" || echo 'BD ya existe o error menor'
"
log_success "Base de datos inicializada"

log_info "3. Iniciando servidor web..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    source venv/bin/activate
    
    # Matar procesos anteriores
    pkill -f web_interface || true
    sleep 2
    
    # Crear directorio de logs si no existe
    mkdir -p logs
    
    # Iniciar servidor en background
    nohup python3 web_interface.py > logs/web.log 2>&1 &
    PID=\$!
    echo \$PID > web.pid
    
    echo \"Servidor iniciado con PID: \$PID\"
    sleep 5
    
    # Verificar que está corriendo
    if ps -p \$PID > /dev/null 2>&1; then
        echo '✅ Servidor web corriendo correctamente'
    else
        echo '❌ Error al iniciar servidor:'
        tail -10 logs/web.log
        exit 1
    fi
"
log_success "Servidor web iniciado"

log_info "4. Verificando acceso..."
sleep 3

if remote_exec "curl -f http://localhost:8090/health >/dev/null 2>&1"; then
    log_success "¡YT-Shorts desplegado exitosamente! 🎉"
    echo ""
    echo "=============================================="
    echo "🌐 ACCESOS DISPONIBLES:"
    echo "   Web Interface: http://$SERVER_IP:8090"
    echo "   API Health: http://$SERVER_IP:8090/health"
    echo ""
    echo "🔧 GESTIÓN DEL SERVIDOR:"
    echo "   Ver logs: ssh $SERVER_USER@$SERVER_IP 'tail -f ~/proyectos/yt-shorts-agent/logs/web.log'"
    echo "   Estado: ssh $SERVER_USER@$SERVER_IP 'ps aux | grep web_interface'"
    echo "   Parar: ssh $SERVER_USER@$SERVER_IP 'pkill -f web_interface'"
    echo "   Reiniciar: ssh $SERVER_USER@$SERVER_IP 'cd ~/proyectos/yt-shorts-agent && source venv/bin/activate && nohup python3 web_interface.py > logs/web.log 2>&1 &'"
    echo ""
    echo "📝 PRÓXIMOS PASOS:"
    echo "   1. Visita http://$SERVER_IP:8090 para acceder a la interfaz"
    echo "   2. Agrega tus API keys reales en el archivo .env del servidor"
    echo "   3. Usa la interfaz para añadir canales y gestionar shorts"
    echo "=============================================="
    
    # Mostrar información del proceso
    remote_exec "ps aux | grep web_interface | grep -v grep"
    
else
    echo "❌ El servidor no responde en puerto 8090"
    echo "Revisando logs..."
    remote_exec "tail -20 ~/proyectos/yt-shorts-agent/logs/web.log 2>/dev/null || echo 'Sin logs'"
    exit 1
fi

log_success "¡Despliegue completado exitosamente! 🚀"
