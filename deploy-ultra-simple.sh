#!/bin/bash

# 🚀 Script de Despliegue Ultra-Simple - Solo Python Estándar
set -e

echo "🚀 YT-Shorts Dual Panel Agent - Despliegue Ultra Simple"
echo "========================================================"

SERVER_IP="100.87.242.53"
SERVER_USER="germanmallo"
SERVER_PASSWORD="0301"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
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

log_info "1. Conectando al servidor..."
if ! remote_exec "echo 'OK'"; then
    log_error "No se puede conectar"
    exit 1
fi
log_success "Conectado"

log_info "2. Preparando directorio..."
remote_exec "
    mkdir -p ~/proyectos/yt-shorts-agent/{data,logs}
    cd ~/proyectos/yt-shorts-agent
    python3 --version
"
log_success "Directorio preparado"

log_info "3. Creando servidor web básico..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    
    cat > web_server.py << 'EOFPY'
#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs

class YTShortsHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'message': 'YT Shorts Server Running',
                'port': os.getenv('WEB_PORT', '8090')
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif parsed_path.path == '/' or parsed_path.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = f'''<!DOCTYPE html>
<html>
<head>
    <title>🎬 YT Shorts Control Panel</title>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; color: #333; margin-bottom: 40px; }}
        .status {{ padding: 20px; background: #d4edda; color: #155724; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745; }}
        .info {{ padding: 20px; background: #e7f3ff; color: #004085; border-radius: 8px; margin: 20px 0; border-left: 4px solid #007bff; }}
        .warning {{ padding: 20px; background: #fff3cd; color: #856404; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .card {{ padding: 20px; background: #f8f9fa; border-radius: 8px; text-align: center; }}
        .card h3 {{ margin-top: 0; color: #495057; }}
        .footer {{ text-align: center; margin-top: 40px; color: #666; font-size: 14px; }}
        .refresh {{ float: right; background: #007bff; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }}
        .refresh:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class=\"container\">
        <div class=\"header\">
            <h1>🎬 YT Shorts Control Panel</h1>
            <p>Interfaz Web Ultra-Simple - Servidor Python Básico</p>
            <button class=\"refresh\" onclick=\"location.reload()\">🔄 Actualizar</button>
        </div>
        
        <div class=\"status\">
            <h3>✅ Estado del Sistema</h3>
            <p><strong>Servidor Web:</strong> Activo en puerto {os.getenv('WEB_PORT', '8090')}</p>
            <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Python:</strong> Usando librerías estándar únicamente</p>
        </div>
        
        <div class=\"grid\">
            <div class=\"card\">
                <h3>🌐 Acceso Web</h3>
                <p>Puerto: {os.getenv('WEB_PORT', '8090')}</p>
                <p>Health: <a href=\"/health\">/health</a></p>
            </div>
            <div class=\"card\">
                <h3>📁 Ubicación</h3>
                <p>~/proyectos/yt-shorts-agent</p>
                <p>Logs: ~/proyectos/yt-shorts-agent/logs/</p>
            </div>
            <div class=\"card\">
                <h3>🔧 Estado</h3>
                <p>Servidor: <span style=\"color: #28a745;\">●</span> Online</p>
                <p>Modo: Básico (Sin dependencias)</p>
            </div>
        </div>
        
        <div class=\"warning\">
            <h3>⚠️ Limitaciones Actuales</h3>
            <p>Este es un servidor web básico usando solo Python estándar debido a restricciones del sistema.</p>
            <ul>
                <li>No hay acceso a pip/paquetes externos</li>
                <li>Pipeline completo requiere dependencias adicionales</li>
                <li>Funcionalidad limitada hasta configurar entorno completo</li>
            </ul>
        </div>
        
        <div class=\"info\">
            <h3>📋 Próximos Pasos para Pipeline Completo</h3>
            <ol>
                <li><strong>Instalar dependencias del sistema:</strong>
                    <br><code>sudo apt-get update && sudo apt-get install -y python3-pip python3-venv ffmpeg</code>
                </li>
                <li><strong>Crear entorno virtual:</strong>
                    <br><code>python3 -m venv venv && source venv/bin/activate</code>
                </li>
                <li><strong>Instalar dependencias Python:</strong>
                    <br><code>pip install -r requirements.txt</code>
                </li>
                <li><strong>Configurar APIs en .env:</strong>
                    <br>OPENAI_API_KEY, YOUTUBE_API_KEY, etc.
                </li>
                <li><strong>Ejecutar interfaz completa:</strong>
                    <br><code>python web_interface.py</code>
                </li>
            </ol>
        </div>
        
        <div class=\"info\">
            <h3>🔧 Comandos de Gestión</h3>
            <p><strong>Ver proceso:</strong> <code>ps aux | grep python</code></p>
            <p><strong>Parar servidor:</strong> <code>pkill -f web_server.py</code></p>
            <p><strong>Reiniciar:</strong> <code>cd ~/proyectos/yt-shorts-agent && nohup python3 web_server.py &</code></p>
            <p><strong>Ver logs:</strong> <code>tail -f ~/proyectos/yt-shorts-agent/logs/web.log</code></p>
        </div>
        
        <div class=\"footer\">
            <p>🚀 YT Shorts Dual Panel Agent - Versión Ultra-Simple</p>
            <p>Servidor corriendo con Python {'.'.join(map(str, __import__('sys').version_info[:3]))}</p>
        </div>
    </div>
    
    <script>
        // Auto-refresh cada 60 segundos
        setTimeout(() => location.reload(), 60000);
    </script>
</body>
</html>'''
            self.wfile.write(html.encode())
            
        else:
            self.send_error(404, \"Página no encontrada\")

if __name__ == '__main__':
    port = int(os.getenv('WEB_PORT', '8090'))
    
    with socketserver.TCPServer(('', port), YTShortsHandler) as httpd:
        print(f'🌐 Servidor iniciado en puerto {port}')
        print(f'📱 Accede en: http://localhost:{port}')
        print('💡 Usa Ctrl+C para detener')
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\\n🛑 Servidor detenido')
EOFPY

    chmod +x web_server.py
    echo 'Servidor web básico creado'
"
log_success "Servidor creado"

log_info "4. Creando archivo .env..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    cat > .env << 'EOF'
WEB_PORT=8090
LOG_LEVEL=INFO
TZ=Europe/Madrid
PIPELINE_ENABLED=false
DATABASE_PATH=./data/pipeline.db
PYTHONPATH=./src
EOF
    echo 'Archivo .env creado'
"

log_info "5. Iniciando servidor..."
remote_exec "
    cd ~/proyectos/yt-shorts-agent
    
    # Matar procesos anteriores
    pkill -f web_server.py || true
    pkill -f web_interface || true
    sleep 2
    
    # Iniciar servidor básico
    mkdir -p logs
    nohup python3 web_server.py > logs/web.log 2>&1 &
    PID=\$!
    echo \$PID > web.pid
    
    echo \"Servidor iniciado con PID: \$PID\"
    sleep 3
    
    # Verificar
    if ps -p \$PID > /dev/null 2>&1; then
        echo 'Servidor corriendo correctamente'
        echo \"PID \$PID activo\"
    else
        echo 'Error al iniciar servidor:'
        cat logs/web.log
        exit 1
    fi
"
log_success "Servidor iniciado"

log_info "6. Verificando acceso..."
sleep 3

if remote_exec "curl -f http://localhost:8090/health >/dev/null 2>&1"; then
    log_success "¡Despliegue ultra-simple exitoso! 🎉"
    echo ""
    echo "=============================================="
    echo "🌐 ACCESOS DISPONIBLES:"
    echo "   Web Interface: http://$SERVER_IP:8090"
    echo "   API Health: http://$SERVER_IP:8090/health" 
    echo ""
    echo "🔧 GESTIÓN DEL SERVIDOR:"
    echo "   Ver proceso: ssh $SERVER_USER@$SERVER_IP 'ps aux | grep web_server'"
    echo "   Ver logs: ssh $SERVER_USER@$SERVER_IP 'tail -f ~/proyectos/yt-shorts-agent/logs/web.log'"
    echo "   Parar: ssh $SERVER_USER@$SERVER_IP 'pkill -f web_server.py'"
    echo "   Reiniciar: ssh $SERVER_USER@$SERVER_IP 'cd ~/proyectos/yt-shorts-agent && nohup python3 web_server.py > logs/web.log 2>&1 &'"
    echo ""
    echo "📁 Ubicación en servidor: ~/proyectos/yt-shorts-agent"
    echo "=============================================="
    
    # Información del proceso
    remote_exec "cd ~/proyectos/yt-shorts-agent && ps aux | grep web_server | grep -v grep"
    
else
    log_error "El servidor no responde en puerto 8090"
    remote_exec "cd ~/proyectos/yt-shorts-agent && tail -10 logs/web.log 2>/dev/null || echo 'Sin logs'"
    remote_exec "ps aux | grep web_server | grep -v grep || echo 'Proceso no encontrado'"
    exit 1
fi

log_success "¡Servidor web básico desplegado y funcionando! 🚀"

echo ""
echo "🎯 RESUMEN:"
echo "✅ Servidor web básico funcionando en puerto 8090"  
echo "✅ Usando solo librerías estándar de Python"
echo "✅ Interfaz accesible desde navegador"
echo "⚠️  Para pipeline completo necesitas instalar dependencias"
echo ""
echo "🌍 Visita: http://$SERVER_IP:8090"
