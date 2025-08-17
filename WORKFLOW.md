# Pipeline de YouTube Shorts - Flujo de Trabajo Completo

## Objetivo
Este documento muestra cómo usar el pipeline completo desde un video hasta Shorts listos para publicar.

## Flujo de Trabajo

### Paso 1: Preparar archivos
```bash
# Estructura de archivos necesaria:
data/
├── videos/
│   ├── podcast_episodio.mp4      # Video del podcast completo
│   └── broll_subway.mp4          # Video de B-roll para fondo
├── transcripts/                  # Se genera automáticamente
├── segments/                     # Se genera automáticamente
└── shorts/                       # Salida final
```

### Paso 2: Transcripción con Whisper
```bash
# Transcribir el podcast completo
make transcribe VIDEO=data/videos/podcast_episodio.mp4 MODEL=base DEVICE=auto

# O usando CLI directo:
python -m src.cli transcribe data/videos/podcast_episodio.mp4 \
    --output-dir data/transcripts \
    --model base \
    --language es \
    --device auto

# Resultado:
# - data/transcripts/podcast_episodio_transcript.json
# - data/transcripts/podcast_episodio_transcript.srt
```

### Paso 3: Segmentación de clips
```bash
# Segmentar en clips candidatos
make segment TRANSCRIPT=data/transcripts/podcast_episodio_transcript.json \
    KEYWORDS="tecnología,inteligencia artificial,programación"

# O usando CLI directo:
python -m src.cli segment data/transcripts/podcast_episodio_transcript.json \
    --output-dir data/segments \
    --keywords "tecnología,IA,programación" \
    --min-duration 15 \
    --max-duration 59

# Resultado:
# - data/segments/podcast_episodio_candidates.json
```

### Paso 4: Composición de Shorts
```bash
# Componer Shorts finales
make compose \
    CANDIDATES=data/segments/podcast_episodio_candidates.json \
    PODCAST=data/videos/podcast_episodio.mp4 \
    BROLL=data/videos/broll_subway.mp4 \
    TRANSCRIPT=data/transcripts/podcast_episodio_transcript.json

# O usando CLI directo:
python -m src.cli compose \
    data/segments/podcast_episodio_candidates.json \
    data/videos/podcast_episodio.mp4 \
    data/videos/broll_subway.mp4 \
    data/transcripts/podcast_episodio_transcript.json \
    --output-dir data/shorts \
    --max-shorts 5

# Resultado:
# - data/shorts/short_candidate_1_45s.mp4
# - data/shorts/short_candidate_2_30s.mp4
# - data/shorts/short_candidate_3_42s.mp4
```

## Características de los Shorts Generados

### Layout Dual-Panel
- **Panel Superior (960px)**: Video del podcast con audio
- **Panel Inferior (960px)**: B-roll sin audio (loop automático)
- **Dimensiones**: 1080x1920 (YouTube Shorts)
- **FPS**: 30
- **Duración**: 15-59 segundos

### Subtítulos Quemados
- **Posición**: Panel superior, zona segura
- **Estilo**: Arial, 48px, blanco con contorno negro
- **Timing**: Sincronizado con la transcripción de Whisper
- **Formato**: Quemados directamente en el video

### Calidad y Optimización
- **Codec**: H.264 (libx264)
- **Audio**: AAC, 128kbps
- **Video**: Bitrate optimizado para YouTube
- **Validación**: Automática de dimensiones y duración

## Comandos de Verificación

```bash
# Verificar setup
make doctor

# Ver información del entorno
make info

# Ejecutar tests
make test

# Limpiar archivos temporales
make clean
```

## Personalización

### Layout Personalizado
Edita `configs/layout.yml` para ajustar:
- Dimensiones de paneles
- Posición de subtítulos
- Colores de fondo
- Zonas de branding

### Estilo de Subtítulos
Modifica los parámetros en el código:
- Tamaño y fuente
- Colores y contornos
- Posición y márgenes
- Duración máxima por subtítulo

### Segmentación Inteligente
Ajusta parámetros en `segment`:
- Palabras clave importantes
- Duración mínima/máxima
- Umbral de solapamiento
- Pesos de scoring

## Solución de Problemas

### Error de memoria con Whisper
```bash
# Usar modelo más pequeño
make transcribe MODEL=tiny DEVICE=cpu

# O modelo base en CPU si no hay CUDA
make transcribe MODEL=base DEVICE=cpu
```

### Video B-roll muy corto
El sistema automáticamente hace loop del B-roll si es más corto que el clip del podcast.

### Calidad de transcripción baja
- Verificar que el audio sea claro
- Usar modelo más grande: `MODEL=medium`
- Especificar idioma: `LANGUAGE=es`

### Shorts demasiado largos/cortos
Ajustar parámetros de segmentación:
```bash
make segment MIN_DUR=20 MAX_DUR=55
```

## Estado del Proyecto

**✅ Funcionalidades Completadas:**
- Transcripción con Whisper (todos los modelos)
- Segmentación inteligente de clips
- Composición dual-panel con ffmpeg
- Subtítulos quemados automáticos
- Validación de formato YouTube Shorts
- CLI completo y funcional

**🚧 Próximas Funcionalidades:**
- Descarga automática con yt-dlp
- Normalización de audio/video
- Publicación directa en YouTube
- Interfaz web para gestión
