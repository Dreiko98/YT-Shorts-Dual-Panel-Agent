#!/bin/bash

# 🚀 Script de Despliegue Nativo (sin Docker) - YT-Shorts-Dual-Panel-Agent
set -e

echo "🚀 YT-Shorts Dual Panel Agent - Despliegue Nativo"
echo "=================================================="

SERVER_IP="100.87.242.53"
SERVER_USER="germanmallo"
SERVER_PASSWORD="0301"

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

log_info "1. Verificando conexión al servidor..."
if ! remote_exec "echo 'Conexión OK'"; then
    log_error "No se puede conectar al servidor"
    exit 1
fi
log_success "Conexión establecida"

log_info "2. Preparando servidor..."
remote_exec "
    # Crear estructura de directorios
    mkdir -p ~/proyectos/yt-shorts-agent/{data,logs,outputs}
    cd ~/proyectos/yt-shorts-agent
    
    # Verificar Python
    python3 --version || (echo 'Instalando Python...' && sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv)
    
    # Verificar ffmpeg
    ffmpeg -version >/dev/null 2>&1 || (echo 'Instalando FFmpeg...' && sudo apt-get update && sudo apt-get install -y ffmpeg)
    
    echo 'Dependencias del sistema verificadas'
"
log_success "Servidor preparado"

log_info "3. Transfiriendo código fuente..."

# Crear archivo temporal excluyendo archivos innecesarios
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
node_modules/
yt-shorts-image.tar
*.tar.gz
EOF

# Comprimir y transferir
tar --exclude-from=.deployignore -czf yt-shorts-code.tar.gz .
copy_to_server "yt-shorts-code.tar.gz" "~/proyectos/yt-shorts-agent/"

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
DATABASE_PATH=./data/pipeline.db
FLASK_ENV=production
PYTHONPATH=./src
EOF
fi

copy_to_server ".env" "~/proyectos/yt-shorts-agent/"

# Extraer código en el servidor
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    tar -xzf yt-shorts-code.tar.gz
    rm yt-shorts-code.tar.gz
    chmod +x *.sh *.py
"

# Limpiar archivos temporales locales
rm yt-shorts-code.tar.gz .deployignore
log_success "Código transferido"

log_info "4. Configurando entorno Python..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    
    # Crear entorno virtual
    python3 -m venv venv
    source venv/bin/activate
    
    # Instalar dependencias
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo 'Entorno Python configurado'
"
log_success "Entorno Python listo"

log_info "5. Inicializando base de datos..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    source venv/bin/activate
    export PYTHONPATH=./src
    
    # Inicializar BD
    python3 -c \"from src.pipeline.db import PipelineDB; PipelineDB()\" || echo 'BD ya existe o error menor'
    
    echo 'Base de datos inicializada'
"
log_success "Base de datos lista"

log_info "6. Creando servicio systemd..."
remote_exec "
    # Crear archivo de servicio
    sudo tee /etc/systemd/system/yt-shorts-web.service > /dev/null << 'EOF'
[Unit]
Description=YT Shorts Web Interface
After=network.target

[Service]
Type=simple
User=germanmallo
WorkingDirectory=/home/germanmallo/proyectos/yt-shorts-agent
Environment=PYTHONPATH=/home/germanmallo/proyectos/yt-shorts-agent/src
EnvironmentFile=/home/germanmallo/proyectos/yt-shorts-agent/.env
ExecStart=/home/germanmallo/proyectos/yt-shorts-agent/venv/bin/python /home/germanmallo/proyectos/yt-shorts-agent/web_interface.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    # Recargar systemd y habilitar servicio
    sudo systemctl daemon-reload
    sudo systemctl enable yt-shorts-web
    sudo systemctl start yt-shorts-web
    
    # Esperar un momento
    sleep 5
    
    # Verificar estado
    sudo systemctl status yt-shorts-web --no-pager
"
log_success "Servicio systemd configurado"

log_info "7. Verificando despliegue..."
sleep 5

if remote_exec "curl -f http://localhost:8090/health >/dev/null 2>&1"; then
    log_success "¡Despliegue nativo exitoso! 🎉"
    echo ""
    echo "==============================================="
    echo "🌐 Accesos disponibles:"
    echo "   Web Interface: http://$SERVER_IP:8090"
    echo "   API Health: http://$SERVER_IP:8090/health"
    echo ""
    echo "🔧 Comandos útiles en el servidor:"
    echo "   Ver logs: sudo journalctl -u yt-shorts-web -f"
    echo "   Estado: sudo systemctl status yt-shorts-web"
    echo "   Reiniciar: sudo systemctl restart yt-shorts-web"
    echo "   Detener: sudo systemctl stop yt-shorts-web"
    echo ""
    echo "📁 Ubicación: ~/proyectos/yt-shorts-agent"
    echo "🐍 Entorno virtual: ~/proyectos/yt-shorts-agent/venv"
    echo "==============================================="
    
    # Mostrar logs recientes
    log_info "Estado del servicio:"
    remote_exec "sudo systemctl status yt-shorts-web --no-pager -l"
    
else
    log_error "El servicio web no responde en puerto 8090"
    log_info "Revisando logs del servicio:"
    remote_exec "sudo journalctl -u yt-shorts-web -n 20 --no-pager"
    log_info "Verificando si el puerto está en uso:"
    remote_exec "sudo lsof -i :8090 || echo 'Puerto 8090 no está en uso'"
    exit 1
fi

log_success "¡Despliegue nativo completado exitosamente! 🚀"

log_info "Próximos pasos:"
echo "1. Accede a http://$SERVER_IP:8090 para ver la interfaz web"
echo "2. Añade tus API keys (OpenAI, YouTube) en el archivo .env en el servidor"
echo "3. Reinicia el servicio: sudo systemctl restart yt-shorts-web"
echo "4. Usa la interfaz web para añadir canales y gestionar el pipeline"
