# 🎬 YT Shorts Dual-Panel Agent

Pipeline automatizado para generar YouTube Shorts 9:16 con dos paneles:
- **Superior:** Podcast con audio y subtítulos (50-52%)
- **Inferior:** B-roll muteado con loop automático (48-50%)

## 🔧 Prerequisitos

### Sistema
- **Python 3.11+**
- **ffmpeg** (con soporte libx264, libx265, libfdk_aac)
- **git**

### Instalación de prerequisitos

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip ffmpeg git
```

#### macOS (Homebrew)
```bash
brew install python@3.11 ffmpeg git
```

### Verificar instalación
```bash
python3 --version    # >= 3.11
ffmpeg -version      # debe mostrar versión
git --version        # cualquier versión reciente
```

## 🚀 Quick Start

1. **Clonar y configurar:**
```bash
git clone <tu-repo>
cd YT-Shorts-Dual-Panel-Agent
make setup
```

2. **Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tus credenciales de YouTube API
```

3. **Verificar que todo funciona:**
```bash
make doctor
```

4. **Probar con archivos de ejemplo:**
```bash
# Coloca un archivo .mp4 de podcast en data/raw/podcast/
# Coloca archivos de B-roll en data/raw/broll/subway/
make compose-test
```

## 📁 Estructura del proyecto

```
yt-shorts-pipeline/
├─ src/pipeline/         # Módulos principales del pipeline
├─ configs/             # Archivos de configuración YAML
├─ data/               # Datos y salidas (gitignored)
├─ assets/             # Recursos gráficos y fuentes
├─ tests/              # Tests unitarios
└─ cli.py              # Interfaz de línea de comandos
```

## 🎯 Comandos principales

```bash
make setup          # Instalar dependencias y crear estructura
make doctor         # Verificar prerequisitos
make discover       # Descubrir nuevos episodios (requiere API)
make download       # Descargar podcasts pendientes
make normalize      # Normalizar audio/video
make transcribe     # Generar transcripciones con Whisper ✅ IMPLEMENTADO
make segment        # Crear clips candidatos ✅ IMPLEMENTADO
make compose        # Generar Shorts finales
make publish        # Subir a YouTube (requiere OAuth)

# Nuevos comandos implementados:
# Transcribir un video específico:
make transcribe VIDEO=data/videos/mi_video.mp4 MODEL=base DEVICE=auto

# Segmentar transcripción en clips:
make segment TRANSCRIPT=data/transcripts/mi_video_transcript.json KEYWORDS="podcast,tecnología"

# Componer Shorts finales:
make compose CANDIDATES=data/segments/candidatos.json PODCAST=data/videos/podcast.mp4 BROLL=data/videos/broll.mp4 TRANSCRIPT=data/transcripts/transcript.json
```

## ⚡ Desarrollo

```bash
make lint           # Ejecutar linting (ruff + black)
make test           # Ejecutar tests
make clean          # Limpiar archivos temporales
```

## 📝 Configuración

Ver archivos en `configs/` para personalizar:
- `channels.yaml` - Canales a procesar
- `layout.yaml` - Diseño de paneles
- `segment_rules.yaml` - Reglas de segmentación
- `broll_pools.yaml` - Pools de B-roll
- `publish.yaml` - Configuración de publicación

## 🔐 APIs y autenticación

1. Crear proyecto en Google Cloud Console
2. Habilitar YouTube Data API v3
3. Crear credenciales OAuth 2.0
4. Configurar en `.env`

## � Estado de Desarrollo

### ✅ Completado
- **Configuración del Proyecto**: Estructura, configuración, dependencias
- **Base de Datos**: Schema SQLite para gestión de estado
- **CLI Principal**: Comandos básicos con Typer + Rich
- **Utilidades**: Módulos ffmpeg y text con funciones auxiliares
- **Transcripción**: Módulo completo con Whisper local ✅
- **Segmentación**: Análisis inteligente de transcripciones para clips ✅
- **Composición**: Sistema completo de layout dual-panel ✅
- **Subtítulos**: Subtítulos quemados con ffmpeg ✅
- **Editor Principal**: Compositor de Shorts finales ✅
- **Tests**: Suite completa de tests unitarios (36 tests passing)

### 🚧 En Desarrollo
- **Descarga de Videos**: Integración con yt-dlp (planificado)
- **Normalización**: Preparación de medios (planificado)
- **Control de Calidad**: Validación avanzada de outputs (planificado)
- **Publicación**: Integración con YouTube API (planificado)

### 🎯 Próximos Pasos
1. ~~Implementar módulo de composición (layout dual-panel)~~ ✅ COMPLETADO
2. ~~Desarrollar sistema de subtítulos quemados~~ ✅ COMPLETADO  
3. Integrar descarga y normalización de videos (Hito D)
4. Conectar con YouTube API para publicación (Hito E)
5. Implementar descubrimiento automático de contenido (Hito F)

## �📄 Licencia

MIT License - Ver LICENSE para detalles.

---

**Nota:** Este proyecto está diseñado para uso local y respeta las políticas de copyright. Solo usa contenido con permisos apropiados.
