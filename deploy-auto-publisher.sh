#!/bin/bash

echo "🚀 DESPLIEGUE AUTOMÁTICO - YT SHORTS AUTO-PUBLISHER"
echo "=================================================="

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 Verificando estado actual...${NC}"

# Verificar contenedores existentes
echo "🐳 Contenedores Docker actuales:"
docker ps -a | grep -E "yt-shorts|auto_thumbnail"

echo -e "\n${YELLOW}🛑 Deteniendo contenedor anterior...${NC}"
docker stop yt-shorts-container 2>/dev/null || echo "No hay contenedor previo"
docker rm yt-shorts-container 2>/dev/null || echo "No hay contenedor que eliminar"

echo -e "\n${YELLOW}🔨 Construyendo nueva imagen Docker...${NC}"
docker build -t yt-shorts-app-v2 . --no-cache

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Imagen construida exitosamente${NC}"
else
    echo -e "\n${RED}❌ Error construyendo imagen${NC}"
    exit 1
fi

echo -e "\n${YELLOW}🚀 Desplegando contenedor con AUTO-PUBLICACIÓN...${NC}"

docker run -d \
    --name yt-shorts-container \
    --restart=unless-stopped \
    -p 8093:8081 \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/.env:/app/.env \
    -e DAEMON_ENABLED=true \
    -e PUBLISH_ENABLED=true \
    -e AUTO_APPROVE_ENABLED=true \
    yt-shorts-app-v2

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Contenedor desplegado exitosamente${NC}"
else
    echo -e "\n${RED}❌ Error desplegando contenedor${NC}"
    exit 1
fi

echo -e "\n${YELLOW}⏳ Esperando que el contenedor se inicie...${NC}"
sleep 10

echo -e "\n${YELLOW}📊 Estado del contenedor:${NC}"
docker ps | grep yt-shorts

echo -e "\n${YELLOW}🧪 Probando conectividad...${NC}"
curl -s http://localhost:8093/health | head -5

echo -e "\n${GREEN}🎉 ¡DESPLIEGUE COMPLETADO!${NC}"
echo "======================================="
echo -e "📺 Dashboard: ${GREEN}http://100.87.242.53:8093/${NC}"
echo -e "🔍 Health Check: ${GREEN}http://100.87.242.53:8093/health${NC}"
echo ""
echo "🤖 FUNCIONALIDADES ACTIVAS:"
echo "  ✅ Auto-descubrimiento de videos"
echo "  ✅ Transcripción automática (Whisper)"
echo "  ✅ Segmentación inteligente"
echo "  ✅ Auto-aprobación por calidad"
echo "  ✅ Publicación automática en horarios"
echo "  ✅ Dashboard web con controles"
echo "  ✅ APIs de YouTube configuradas"
echo ""
echo "⏰ HORARIOS DE PUBLICACIÓN:"
echo "  - 10:00 (mañana)"
echo "  - 15:00 (tarde)"  
echo "  - 20:00 (noche)"
echo ""
echo "📊 LÍMITES CONFIGURADOS:"
echo "  - Máximo: 3 posts por día"
echo "  - Intervalo mínimo: 4 horas entre posts"
echo "  - Auto-aprobación: clips con score > 0.7"
echo ""
echo "🎛️ CONTROLES DISPONIBLES:"
echo "  - Activar/desactivar auto-publicación desde dashboard"
echo "  - Forzar publicación inmediata"
echo "  - Pausar/reanudar daemon"
echo "  - Revisar y aprobar clips manualmente"
echo ""
echo -e "${YELLOW}💡 PRÓXIMOS PASOS:${NC}"
echo "1. Ve al dashboard: http://100.87.242.53:8093/"
echo "2. Verifica que 'Auto-Publicación' esté activada"
echo "3. Añade canales de YouTube en la sección 'Canales'"
echo "4. ¡El sistema trabajará automáticamente!"
echo ""
echo -e "${GREEN}🌟 ¡Sistema completamente automatizado y listo!${NC}"
