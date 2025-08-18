#!/bin/bash

# 🚀 Script de Despliegue Simple - YT-Shorts-Dual-Panel-Agent
# Despliegue directo con Docker (sin compose)

set -e

echo "🚀 YT-Shorts Dual Panel Agent - Despliegue Simple"
echo "================================================="

SERVER_IP="100.87.242.53"
SERVER_USER="germanmallo"
SERVER_PASSWORD="0301"
CONTAINER_NAME="yt-shorts-pipeline"
IMAGE_NAME="yt-shorts-agent:latest"

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

log_info "Iniciando despliegue simple en servidor $SERVER_IP..."

# 1. Verificar conexión al servidor
log_info "🔌 Verificando conexión al servidor..."
if ! remote_exec "echo 'Conexión OK'"; then
    log_error "No se puede conectar al servidor"
    exit 1
fi
log_success "Conexión al servidor establecida"

# 2. Preparar el servidor (instalación de Docker si es necesario)
log_info "🛠️ Preparando el servidor..."
remote_exec "
    # Crear directorio del proyecto
    mkdir -p ~/proyectos/yt-shorts-agent
    cd ~/proyectos/yt-shorts-agent
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        echo 'Instalando Docker...'
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker \$USER
        echo 'Docker instalado'
    fi
    
    # Crear directorios
    mkdir -p {data,logs,outputs}
    
    echo 'Servidor preparado'
"

# 3. Construir imagen localmente y transferir
log_info "🐋 Construyendo imagen Docker..."

# Crear el archivo .dockerignore
cat > .dockerignore << EOF
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
node_modules/
EOF

# Construir imagen
docker build -t "$IMAGE_NAME" .

# Guardar imagen como tar
log_info "💾 Exportando imagen..."
docker save "$IMAGE_NAME" > yt-shorts-image.tar

# 4. Transferir archivos
log_info "📤 Transfiriendo imagen y archivos..."

# Transferir imagen
copy_to_server "yt-shorts-image.tar" "~/proyectos/yt-shorts-agent/"

# Transferir configuración
copy_to_server ".env.server" "~/proyectos/yt-shorts-agent/.env"
copy_to_server "configs/" "~/proyectos/yt-shorts-agent/"

# 5. Desplegar en el servidor
log_info "🚀 Desplegando contenedor..."
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
        -p 8081:8081 \\
        -p 5001:5001 \\
        -v \$(pwd)/data:/app/data \\
        -v \$(pwd)/logs:/app/logs \\
        -v \$(pwd)/outputs:/app/outputs \\
        -v \$(pwd)/configs:/app/configs \\
        --env-file .env \\
        $IMAGE_NAME
    
    # Esperar inicio
    sleep 10
    
    # Verificar estado
    docker ps | grep $CONTAINER_NAME || echo 'Contenedor no está ejecutándose'
    
    # Mostrar logs
    echo '--- Últimos logs ---'
    docker logs --tail=20 $CONTAINER_NAME
"

# 6. Verificar despliegue
log_info "🔍 Verificando despliegue..."
sleep 5

if remote_exec "curl -f http://localhost:8081/health >/dev/null 2>&1"; then
    log_success "¡Despliegue exitoso! 🎉"
    echo ""
    echo "==============================================="
    echo "🌐 Accesos disponibles:"
    echo "   Web Interface: http://$SERVER_IP:8081"
    echo "   API Health: http://$SERVER_IP:8081/health"
    echo ""
    echo "🐋 Comandos útiles en el servidor:"
    echo "   Ver logs: docker logs -f $CONTAINER_NAME"
    echo "   Estado: docker ps"
    echo "   Reiniciar: docker restart $CONTAINER_NAME"
    echo "   Detener: docker stop $CONTAINER_NAME"
    echo ""
    echo "📁 Ubicación en servidor: ~/proyectos/yt-shorts-agent"
    echo "==============================================="
else
    log_error "El servicio web no responde correctamente"
    log_info "Revisando logs..."
    remote_exec "docker logs --tail=50 $CONTAINER_NAME"
    exit 1
fi

# Limpiar archivos locales
rm -f yt-shorts-image.tar .dockerignore

log_success "¡Despliegue completado exitosamente! 🚀"
