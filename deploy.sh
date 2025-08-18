#!/bin/bash

# 🚀 Script de Despliegue Automático - YT-Shorts-Dual-Panel-Agent
# Uso: ./deploy.sh

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
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
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
if ! sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "echo 'Conexión OK'"; then
    log_error "No se puede conectar al servidor"
    exit 1
fi
log_success "Conexión al servidor establecida"

# 2. Preparar el servidor
log_info "🛠️ Preparando el servidor..."
remote_exec "
    # Crear directorio del proyecto en el home del usuario
    mkdir -p ~/proyectos/yt-shorts-agent
    cd ~/proyectos/yt-shorts-agent
    
    # Verificar si Docker está instalado
    if ! command -v docker &> /dev/null; then
        echo 'Docker no está instalado. Instalando...'
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker \$USER
        echo 'Docker instalado. Puede que necesites hacer logout/login para usar Docker sin sudo.'
    else
        echo 'Docker ya está instalado'
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo 'Docker Compose no está instalado. Instalando...'
        sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    else
        echo 'Docker Compose ya está instalado'
    fi
    
    # Crear directorios necesarios
    mkdir -p {data,logs,outputs,ssl}
    
    echo 'Servidor preparado'
"
log_success "Servidor preparado"

# 3. Subir archivos del proyecto
log_info "📤 Subiendo archivos del proyecto..."

# Crear un archivo temporal con los archivos a excluir
cat > .deployignore << EOF
.venv/
__pycache__/
*.pyc
.git/
.pytest_cache/
.DS_Store
*.db
logs/
outputs/
data/videos/
data/raw/
temp/
EOF

# Crear un tar excluyendo archivos innecesarios
log_info "🗜️ Comprimiendo proyecto..."
tar --exclude-from=.deployignore -czf yt-shorts-deployment.tar.gz .

# Subir y extraer
log_info "📡 Transfiriendo archivos..."
copy_to_server "yt-shorts-deployment.tar.gz" "~/proyectos/yt-shorts-agent/"

remote_exec "
    cd ~/proyectos/yt-shorts-agent
    tar -xzf yt-shorts-deployment.tar.gz
    rm yt-shorts-deployment.tar.gz
    chmod +x *.sh
"

# Limpiar archivos temporales
rm yt-shorts-deployment.tar.gz .deployignore
log_success "Archivos transferidos"

# 4. Configurar variables de entorno
log_info "⚙️ Configurando variables de entorno..."
if [ ! -f ".env" ]; then
    log_warning "No se encontró archivo .env, creando uno por defecto..."
    cat > temp.env << EOF
# YouTube API Configuration
YOUTUBE_API_KEY=your_youtube_api_key_here

# Telegram Bot (opcional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Database
DATABASE_PATH=/app/data/pipeline.db

# Logging
LOG_LEVEL=INFO

# Pipeline Configuration
PIPELINE_ENABLED=true
AUTO_DISCOVER_ENABLED=true
AUTO_PROCESS_ENABLED=true
AUTO_PUBLISH_ENABLED=false

# Web Interface
FLASK_ENV=production
WEB_PORT=8081

# Timezone
TZ=Europe/Madrid
EOF
    copy_to_server "temp.env" "~/proyectos/yt-shorts-agent/.env"
    rm temp.env
else
    copy_to_server ".env" "~/proyectos/yt-shorts-agent/.env"
fi
log_success "Variables de entorno configuradas"

# 5. Construir y ejecutar contenedores
log_info "🐋 Construyendo y ejecutando contenedores..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    
    # Detener servicios anteriores si existen
    docker-compose down 2>/dev/null || true
    
    # Construir imágenes
    docker-compose build
    
    # Ejecutar servicios
    docker-compose up -d
    
    # Esperar a que los servicios estén listos
    sleep 10
    
    # Mostrar estado
    docker-compose ps
"

# 6. Verificar despliegue
log_info "🔍 Verificando despliegue..."
sleep 15

if remote_exec "curl -f http://localhost:8081/health >/dev/null 2>&1"; then
    log_success "¡Despliegue exitoso! 🎉"
    echo ""
    echo "==============================================="
    echo "🌐 Accesos disponibles:"
    echo "   Web Interface: http://$SERVER_IP:8081"
    echo "   API Health: http://$SERVER_IP:8081/health"
    echo ""
    echo "🐋 Comandos útiles en el servidor:"
    echo "   Ver logs: docker-compose logs -f"
    echo "   Estado: docker-compose ps"
    echo "   Reiniciar: docker-compose restart"
    echo "   Detener: docker-compose down"
    echo ""
    echo "📁 Ubicación en servidor: ~/proyectos/yt-shorts-agent"
    echo "==============================================="
else
    log_error "El servicio web no responde correctamente"
    log_info "Revisando logs..."
    remote_exec "cd ~/proyectos/yt-shorts-agent && docker-compose logs --tail=50"
    exit 1
fi

log_success "Despliegue completado exitosamente! 🚀"
