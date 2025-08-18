#!/bin/bash
set -e

echo "🐋 Starting YT-Shorts-Dual-Panel-Agent Container"
echo "📅 $(date)"

# Inicializar base de datos si no existe
if [ ! -f "data/pipeline.db" ]; then
    echo "🗄️ Initializing database..."
    python3 -c "from src.pipeline.db import PipelineDB; PipelineDB()"
fi

# Función para manejo de señales
cleanup() {
    echo "🛑 Shutting down services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# Iniciar servicios en paralelo
echo "🌐 Starting Web Interface..."
python3 web_interface.py &
WEB_PID=$!

echo "🤖 Starting Pipeline Daemon..."
python3 -c "
from src.pipeline.daemon import PipelineDaemon
daemon = PipelineDaemon()
daemon.start()
" &
DAEMON_PID=$!

# Si hay configuración de Telegram, iniciarlo
if [ -f ".env" ] && grep -q "TELEGRAM_BOT_TOKEN" .env; then
    echo "📱 Starting Telegram Bot..."
    python3 src/pipeline/telegram_bot.py &
    TELEGRAM_PID=$!
fi

echo "✅ All services started successfully!"
echo "🌐 Web Interface: http://localhost:8081"
echo "📊 Access dashboard for monitoring"

# Mantener el contenedor ejecutándose
wait
