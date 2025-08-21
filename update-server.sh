#!/bin/bash

echo "=== ACTUALIZACIÓN DEL SERVIDOR ==="
echo "1. Conectarse por SSH al servidor:"
echo "   ssh germanmallo@100.87.242.53"
echo "   Contraseña: 0301"
echo ""

echo "2. Navegar al directorio del proyecto:"
echo "   cd ~/proyectos/yt-shorts-agent"
echo ""

echo "3. Actualizar el archivo de base de datos (copiar el contenido actualizado):"
echo "   nano src/pipeline/db.py"
echo "   O usar vi src/pipeline/db.py"
echo ""

echo "4. Activar el entorno virtual:"
echo "   source venv/bin/activate"
echo ""

echo "5. Detener el servidor actual (si existe):"
echo "   pkill -f web_interface.py"
echo ""

echo "6. Iniciar el servidor:"
echo "   WEB_PORT=8092 python web_interface.py"
echo ""

echo "7. Verificar que funciona:"
echo "   curl http://100.87.242.53:8092/health"
echo "   curl http://100.87.242.53:8092/"
echo ""

echo "=== ALTERNATIVA: Script automático ==="
echo "Si tienes acceso local al archivo, puedes usar scp:"
echo "scp src/pipeline/db.py germanmallo@100.87.242.53:~/proyectos/yt-shorts-agent/src/pipeline/"
echo ""

echo "¡El archivo db.py ya está actualizado con todos los métodos necesarios!"
