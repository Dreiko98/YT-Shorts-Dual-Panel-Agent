#!/bin/bash

# 🚀 Script de Despliegue con Imagen Local - YT-Shorts-Dual-Panel-Agent
set -e

echo "🚀 YT-Shorts Dual Panel Agent - Despliegue con Imagen Local"
echo "==========================================================="

SERVER_IP="100.87.242.53"
SERVER_USER="germanmallo"
SERVER_PASSWORD="0301"
IMAGE_NAME="yt-shorts-agent:latest"
CONTAINER_NAME="yt-shorts-pipeline"

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

log_info "1. Construyendo imagen localmente..."

# Construir imagen local
docker build -t "$IMAGE_NAME" .
log_success "Imagen construida localmente"

log_info "2. Exportando imagen..."
docker save "$IMAGE_NAME" -o yt-shorts-image.tar
log_success "Imagen exportada"

log_info "3. Verificando conexión al servidor..."
if ! remote_exec "echo 'Conexión OK'"; then
    log_error "No se puede conectar al servidor"
    exit 1
fi
log_success "Conexión establecida"

log_info "4. Preparando servidor..."
remote_exec "
    mkdir -p ~/proyectos/yt-shorts-agent/{data,logs,outputs}
    cd ~/proyectos/yt-shorts-agent
"
log_success "Servidor preparado"

log_info "5. Transfiriendo imagen y archivos..."
copy_to_server "yt-shorts-image.tar" "~/proyectos/yt-shorts-agent/"

# Crear .env si no existe
if [ ! -f ".env" ]; then
    cat > .env << EOF
WEB_PORT=8090
LOG_LEVEL=INFO
TZ=Europe/Madrid
PIPELINE_ENABLED=true
AUTO_DISCOVER_ENABLED=false
AUTO_PROCESS_ENABLED=false
AUTO_PUBLISH_ENABLED=false
DATABASE_PATH=/app/data/pipeline.db
FLASK_ENV=production
EOF
fi

copy_to_server ".env" "~/proyectos/yt-shorts-agent/"
log_success "Archivos transferidos"

log_info "6. Cargando imagen y ejecutando contenedor..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    
    # Cargar imagen
    docker load < yt-shorts-image.tar
    rm yt-shorts-image.tar
    
    # Detener contenedor anterior si existe
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
    
    # Ejecutar nuevo contenedor
    docker run -d \\
        --name $CONTAINER_NAME \\
        --restart unless-stopped \\
        -p 8090:8090 \\
        -v \$(pwd)/data:/app/data \\
        -v \$(pwd)/logs:/app/logs \\
        -v \$(pwd)/outputs:/app/outputs \\
        --env-file .env \\
        $IMAGE_NAME
    
    # Esperar inicio
    sleep 15
    
    # Mostrar estado
    docker ps --filter name=$CONTAINER_NAME
"

log_info "7. Verificando despliegue..."
sleep 5

if remote_exec "curl -f http://localhost:8090/health >/dev/null 2>&1"; then
    log_success "¡Despliegue exitoso! 🎉"
    echo ""
    echo "==============================================="
    echo "🌐 Accesos disponibles:"
    echo "   Web Interface: http://$SERVER_IP:8090"
    echo "   API Health: http://$SERVER_IP:8090/health"
    echo ""
    echo "🐋 Comandos útiles en el servidor:"
    echo "   Ver logs: docker logs -f $CONTAINER_NAME"
    echo "   Estado: docker ps"
    echo "   Reiniciar: docker restart $CONTAINER_NAME"
    echo "   Detener: docker stop $CONTAINER_NAME"
    echo ""
    echo "📁 Ubicación en servidor: ~/proyectos/yt-shorts-agent"
    echo "==============================================="
    
    # Mostrar logs recientes
    log_info "Últimos logs del contenedor:"
    remote_exec "docker logs --tail=20 $CONTAINER_NAME"
    
else
    log_error "El servicio web no responde en puerto 8090"
    log_info "Revisando estado del contenedor:"
    remote_exec "docker ps -a --filter name=$CONTAINER_NAME"
    log_info "Revisando logs del contenedor:"
    remote_exec "docker logs --tail=30 $CONTAINER_NAME 2>/dev/null || echo 'No se pudieron obtener logs'"
    exit 1
fi

# Limpiar archivos locales
rm -f yt-shorts-image.tar

log_success "¡Despliegue completado exitosamente! 🚀"
