#!/bin/bash

# 🚀 Script de Despliegue Automático Simplificado - YT-Shorts-Dual-Panel-Agent
set -e

echo "🚀 YT-Shorts Dual Panel Agent - Despliegue Automático"
echo "==============================================="

SERVER_IP="100.87.242.53"
SERVER_USER="germanmallo"
SERVER_PASSWORD="0301"
REMOTE_PATH="~/proyectos/yt-shorts-agent"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para ejecutar comandos remotos
remote_exec() {
    sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "$1"
}

# Función para copiar archivos
copy_to_server() {
    sshpass -p "$SERVER_PASSWORD" scp -r -o StrictHostKeyChecking=no "$1" "$SERVER_USER@$SERVER_IP:$2"
}

log_info "Iniciando despliegue en servidor $SERVER_IP..."

# 1. Verificar conexión al servidor
log_info "🔌 Verificando conexión al servidor..."
if ! remote_exec "echo 'Conexión OK'"; then
    log_error "No se puede conectar al servidor"
    exit 1
fi
log_success "Conexión al servidor establecida"

# 2. Preparar el servidor
log_info "🛠️ Preparando el servidor..."
remote_exec "
    # Crear directorio del proyecto
    mkdir -p ~/proyectos/yt-shorts-agent
    cd ~/proyectos/yt-shorts-agent
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        echo 'Docker no instalado. Por favor instala Docker manualmente primero.'
        exit 1
    fi
    
    # Instalar docker-compose en el directorio local del usuario
    if ! command -v docker-compose &> /dev/null; then
        echo 'Instalando Docker Compose en directorio local...'
        mkdir -p ~/.local/bin
        curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o ~/.local/bin/docker-compose
        chmod +x ~/.local/bin/docker-compose
        export PATH=\"\$HOME/.local/bin:\$PATH\"
        echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc
    fi
    
    # Crear directorios necesarios
    mkdir -p {data,logs,outputs}
    
    echo 'Servidor preparado'
"
log_success "Servidor preparado"

# 3. Subir archivos del proyecto
log_info "📤 Subiendo archivos del proyecto..."

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    log_info "Creando archivo .env..."
    cat > .env << EOF
# Web Interface
WEB_PORT=8090
LOG_LEVEL=INFO
TZ=Europe/Madrid

# Pipeline Configuration
PIPELINE_ENABLED=true
AUTO_DISCOVER_ENABLED=false
AUTO_PROCESS_ENABLED=false
AUTO_PUBLISH_ENABLED=false

# Database
DATABASE_PATH=/app/data/pipeline.db

# Flask
FLASK_ENV=production

# OpenAI (añade tu clave real)
# OPENAI_API_KEY=sk_xxx

# YouTube API (añade tus credenciales reales)
# YOUTUBE_API_KEY=xxx
EOF
fi

# Subir archivos importantes
copy_to_server ".env" "~/proyectos/yt-shorts-agent/"
copy_to_server "docker-compose.yml" "~/proyectos/yt-shorts-agent/"
copy_to_server "Dockerfile" "~/proyectos/yt-shorts-agent/"
copy_to_server "docker-entrypoint.sh" "~/proyectos/yt-shorts-agent/"
copy_to_server "requirements.txt" "~/proyectos/yt-shorts-agent/"
copy_to_server "web_interface.py" "~/proyectos/yt-shorts-agent/"
copy_to_server "src/" "~/proyectos/yt-shorts-agent/"
copy_to_server "configs/" "~/proyectos/yt-shorts-agent/"

log_success "Archivos transferidos"

# 4. Construir y ejecutar contenedores
log_info "🐋 Construyendo y ejecutando contenedores..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    export PATH=\"\$HOME/.local/bin:\$PATH\"
    
    # Detener servicios anteriores si existen
    docker-compose down 2>/dev/null || ~/.local/bin/docker-compose down 2>/dev/null || true
    
    # Construir imágenes
    if command -v docker-compose &> /dev/null; then
        docker-compose build --no-cache
    else
        ~/.local/bin/docker-compose build --no-cache
    fi
    
    # Ejecutar servicios
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        ~/.local/bin/docker-compose up -d
    fi
    
    # Esperar a que los servicios estén listos
    sleep 15
    
    # Mostrar estado
    docker ps --filter name=yt-shorts
"

# 5. Verificar despliegue
log_info "🔍 Verificando despliegue..."
sleep 10

if remote_exec "curl -f http://localhost:8090/health >/dev/null 2>&1"; then
    log_success "¡Despliegue exitoso! 🎉"
    echo ""
    echo "==============================================="
    echo "🌐 Accesos disponibles:"
    echo "   Web Interface: http://$SERVER_IP:8090"
    echo "   API Health: http://$SERVER_IP:8090/health"
    echo ""
    echo "🐋 Comandos útiles en el servidor:"
    echo "   Ver logs: cd ~/proyectos/yt-shorts-agent && docker-compose logs -f"
    echo "   Estado: docker ps"
    echo "   Reiniciar: cd ~/proyectos/yt-shorts-agent && docker-compose restart"
    echo ""
    echo "📁 Ubicación en servidor: ~/proyectos/yt-shorts-agent"
    echo "==============================================="
else
    log_error "El servicio web no responde correctamente en puerto 8090"
    log_info "Revisando logs..."
    remote_exec "cd ~/proyectos/yt-shorts-agent && docker logs --tail=50 \$(docker ps -q --filter name=yt-shorts) 2>/dev/null || echo 'No se pudieron obtener los logs'"
    
    log_info "Estado de los contenedores:"
    remote_exec "docker ps -a --filter name=yt-shorts"
    exit 1
fi

log_success "Despliegue completado exitosamente! 🚀"
