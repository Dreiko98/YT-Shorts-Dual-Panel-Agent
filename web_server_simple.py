#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
from datetime import datetime
from urllib.parse import urlparse

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
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
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
    <div class="container">
        <div class="header">
            <h1>🎬 YT Shorts Control Panel</h1>
            <p>Interfaz Web Ultra-Simple - Servidor Python Básico</p>
            <button class="refresh" onclick="location.reload()">🔄 Actualizar</button>
        </div>
        
        <div class="status">
            <h3>✅ Estado del Sistema</h3>
            <p><strong>Servidor Web:</strong> Activo en puerto {os.getenv('WEB_PORT', '8090')}</p>
            <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Python:</strong> Usando librerías estándar únicamente</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>🌐 Acceso Web</h3>
                <p>Puerto: {os.getenv('WEB_PORT', '8090')}</p>
                <p>Health: <a href="/health">/health</a></p>
            </div>
            <div class="card">
                <h3>📁 Ubicación</h3>
                <p>~/proyectos/yt-shorts-agent</p>
                <p>Logs: ~/proyectos/yt-shorts-agent/logs/</p>
            </div>
            <div class="card">
                <h3>🔧 Estado</h3>
                <p>Servidor: <span style="color: #28a745;">●</span> Online</p>
                <p>Modo: Básico (Sin dependencias)</p>
            </div>
        </div>
        
        <div class="warning">
            <h3>⚠️ Limitaciones Actuales</h3>
            <p>Este es un servidor web básico usando solo Python estándar debido a restricciones del sistema.</p>
            <ul>
                <li>No hay acceso a pip/paquetes externos</li>
                <li>Pipeline completo requiere dependencias adicionales</li>
                <li>Funcionalidad limitada hasta configurar entorno completo</li>
            </ul>
        </div>
        
        <div class="info">
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
        
        <div class="info">
            <h3>🔧 Comandos de Gestión</h3>
            <p><strong>Ver proceso:</strong> <code>ps aux | grep python</code></p>
            <p><strong>Parar servidor:</strong> <code>pkill -f web_server.py</code></p>
            <p><strong>Reiniciar:</strong> <code>cd ~/proyectos/yt-shorts-agent && nohup python3 web_server.py &</code></p>
            <p><strong>Ver logs:</strong> <code>tail -f ~/proyectos/yt-shorts-agent/logs/web.log</code></p>
        </div>
        
        <div class="footer">
            <p>🚀 YT Shorts Dual Panel Agent - Versión Ultra-Simple</p>
            <p>Servidor corriendo con Python</p>
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
            self.send_error(404, "Página no encontrada")

if __name__ == '__main__':
    port = int(os.getenv('WEB_PORT', '8090'))
    
    with socketserver.TCPServer(('', port), YTShortsHandler) as httpd:
        print(f'🌐 Servidor iniciado en puerto {port}')
        print(f'📱 Accede en: http://localhost:{port}')
        print('💡 Usa Ctrl+C para detener')
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n🛑 Servidor detenido')
