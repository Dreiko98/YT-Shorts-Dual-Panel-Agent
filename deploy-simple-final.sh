#!/bin/bash

# 🚀 Script de Despliegue Simple sin Sudo - YT-Shorts-Dual-Panel-Agent
set -e

echo "🚀 YT-Shorts Dual Panel Agent - Despliegue Simple"
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
    
    # Verificar herramientas disponibles
    echo 'Python version:'
    python3 --version || echo 'Python3 no disponible'
    
    echo 'Pip disponible:'
    python3 -m pip --version || echo 'Pip no disponible, intentando instalarlo...'
    
    # Intentar instalar pip sin sudo
    if ! python3 -m pip --version >/dev/null 2>&1; then
        wget -q https://bootstrap.pypa.io/get-pip.py
        python3 get-pip.py --user
        export PATH=\"\$HOME/.local/bin:\$PATH\"
        echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc
    fi
    
    echo 'Servidor básico preparado'
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
venv/
EOF

# Comprimir y transferir
tar --exclude-from=.deployignore -czf yt-shorts-code.tar.gz .
copy_to_server "yt-shorts-code.tar.gz" "~/proyectos/yt-shorts-agent/"

# Crear .env optimizado
cat > .env << EOF
WEB_PORT=8090
LOG_LEVEL=INFO
TZ=Europe/Madrid
PIPELINE_ENABLED=false
AUTO_DISCOVER_ENABLED=false
AUTO_PROCESS_ENABLED=false
AUTO_PUBLISH_ENABLED=false
DATABASE_PATH=./data/pipeline.db
FLASK_ENV=production
PYTHONPATH=./src
EOF

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

log_info "4. Instalando dependencias básicas..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    export PATH=\"\$HOME/.local/bin:\$PATH\"
    
    # Instalar solo las dependencias esenciales
    python3 -m pip install --user flask
    python3 -m pip install --user pathlib
    python3 -m pip install --user requests
    
    echo 'Dependencias básicas instaladas'
"
log_success "Dependencias instaladas"

log_info "5. Simplificando web_interface.py..."
# Crear una versión simplificada sin dependencias complejas
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    
    # Backup del original
    cp web_interface.py web_interface_original.py
    
    # Crear versión simplificada
    cat > web_interface_simple.py << 'EOFPY'
#!/usr/bin/env python3
import os
import sys
from flask import Flask, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'message': 'YT Shorts Web Interface Running'
    })

@app.route('/')
def dashboard():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎬 YT Shorts Control Panel</title>
        <meta charset=\"utf-8\">
        <style>
            body { font-family: Arial; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .header { text-align: center; color: #333; margin-bottom: 30px; }
            .status { padding: 20px; background: #d4edda; border-radius: 8px; margin: 20px 0; }
            .info { padding: 15px; background: #e7f3ff; border-radius: 8px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class=\"container\">
            <div class=\"header\">
                <h1>🎬 YT Shorts Control Panel</h1>
                <p>Interfaz Web Básica - Servidor Funcionando</p>
            </div>
            
            <div class=\"status\">
                <h3>✅ Estado del Sistema</h3>
                <p><strong>Servidor Web:</strong> Activo en puerto {{ port }}</p>
                <p><strong>Timestamp:</strong> {{ timestamp }}</p>
                <p><strong>Ubicación:</strong> ~/proyectos/yt-shorts-agent</p>
            </div>
            
            <div class=\"info\">
                <h3>📋 Próximos Pasos</h3>
                <ol>
                    <li>El servidor web básico está funcionando correctamente</li>
                    <li>Agrega tus API keys en el archivo .env</li>
                    <li>Instala las dependencias completas cuando tengas acceso sudo</li>
                    <li>Activa el pipeline completo modificando PIPELINE_ENABLED=true</li>
                </ol>
            </div>
            
            <div class=\"info\">
                <h3>🔧 Comandos Útiles</h3>
                <p><strong>Ver este proceso:</strong> ps aux | grep python</p>
                <p><strong>Matar proceso:</strong> pkill -f web_interface</p>
                <p><strong>Reiniciar:</strong> cd ~/proyectos/yt-shorts-agent && python3 web_interface_simple.py</p>
            </div>
        </div>
    </body>
    </html>
    ''', port=os.getenv('WEB_PORT', '8090'), timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == '__main__':
    port = int(os.getenv('WEB_PORT', '8090'))
    print(f'🌐 Iniciando interfaz web básica en puerto {port}...')
    print(f'📱 Accede en: http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
EOFPY

    chmod +x web_interface_simple.py
    echo 'Versión simplificada creada'
"
log_success "Interface simplificada creada"

log_info "6. Iniciando servicio web..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    export PATH=\"\$HOME/.local/bin:\$PATH\"
    
    # Matar procesos anteriores
    pkill -f web_interface || true
    sleep 2
    
    # Iniciar en background
    nohup python3 web_interface_simple.py > logs/web.log 2>&1 &
    WEB_PID=\$!
    echo \$WEB_PID > web.pid
    
    echo \"Servicio iniciado con PID: \$WEB_PID\"
    sleep 5
    
    # Verificar que está corriendo
    if ps -p \$WEB_PID > /dev/null 2>&1; then
        echo 'Servicio web corriendo correctamente'
    else
        echo 'Error: El servicio no se inició correctamente'
        cat logs/web.log
        exit 1
    fi
"
log_success "Servicio web iniciado"

log_info "7. Verificando despliegue..."
sleep 3

if remote_exec "curl -f http://localhost:8090/health >/dev/null 2>&1"; then
    log_success "¡Despliegue básico exitoso! 🎉"
    echo ""
    echo "==============================================="
    echo "🌐 Accesos disponibles:"
    echo "   Web Interface: http://$SERVER_IP:8090"
    echo "   API Health: http://$SERVER_IP:8090/health"
    echo ""
    echo "🔧 Gestión del servicio:"
    echo "   Ver logs: ssh $SERVER_USER@$SERVER_IP 'tail -f ~/proyectos/yt-shorts-agent/logs/web.log'"
    echo "   Estado: ssh $SERVER_USER@$SERVER_IP 'ps aux | grep web_interface'"
    echo "   Parar: ssh $SERVER_USER@$SERVER_IP 'pkill -f web_interface'"
    echo "   Reiniciar: ssh $SERVER_USER@$SERVER_IP 'cd ~/proyectos/yt-shorts-agent && nohup python3 web_interface_simple.py > logs/web.log 2>&1 &'"
    echo ""
    echo "📁 Ubicación: ~/proyectos/yt-shorts-agent"
    echo "==============================================="
    
    # Mostrar información del proceso
    log_info "Información del proceso:"
    remote_exec "cd ~/proyectos/yt-shorts-agent && ps aux | grep web_interface | grep -v grep"
    
else
    log_error "El servicio web no responde en puerto 8090"
    log_info "Revisando logs:"
    remote_exec "cd ~/proyectos/yt-shorts-agent && tail -20 logs/web.log 2>/dev/null || echo 'No hay logs disponibles'"
    log_info "Verificando proceso:"
    remote_exec "ps aux | grep web_interface | grep -v grep || echo 'Proceso no encontrado'"
    exit 1
fi

log_success "¡Despliegue completado! 🚀"

echo ""
echo "🎯 IMPORTANTE:"
echo "Este es un despliegue básico sin todas las funcionalidades."
echo "Para el pipeline completo necesitarás:"
echo "1. Instalar FFmpeg (sudo apt-get install ffmpeg)"
echo "2. Instalar dependencias completas (pip install -r requirements.txt)"
echo "3. Configurar APIs (OpenAI, YouTube) en .env"
echo "4. Activar PIPELINE_ENABLED=true en .env"
