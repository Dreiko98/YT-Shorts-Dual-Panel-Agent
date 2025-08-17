# 📁 Estructura de Datos

Esta carpeta contiene todos los archivos de datos del pipeline YT-Shorts. Los archivos están excluidos del repositorio Git por seguridad y tamaño.

## 📂 Carpetas

### 🎙️ **Input (Videos Originales)**
- `podcasts/` - Videos principales (conversaciones, entrevistas)
- `broll/` - Videos de fondo (B-roll, loops visuales)

### 🔄 **Procesamiento**
- `transcripts/` - Transcripciones de Whisper (.json, .srt)
- `segments/` - Clips candidatos segmentados (.json)

### 📹 **Output**
- `shorts/` - Shorts finales listos para YouTube (.mp4)

### 📁 **Legacy (Compatibilidad)**
- `raw/` - Videos sin procesar
- `normalized/` - Videos normalizados
- `transcriptions/` - Transcripciones (legacy)
- `composites/` - Composiciones (legacy)
- `logs/` - Archivos de log
- `videos/` - Videos de prueba

## 🚫 **Archivos Excluidos**

Todos los archivos de video, audio y transcripciones están excluidos del repositorio:
- `*.mp4`, `*.webm`, `*.avi`, `*.mov`, etc.
- `*.mp3`, `*.wav`, `*.aac`, `*.opus`, etc.
- `*.json` (transcripciones)
- `*.srt`, `*.vtt` (subtítulos)

## 🎯 **Uso**

1. **Coloca videos** en `podcasts/` y `broll/`
2. **Ejecuta pipeline** con Makefile o CLI
3. **Obtén Shorts** en `shorts/`

Ver `WORKFLOW.md` para instrucciones detalladas.
