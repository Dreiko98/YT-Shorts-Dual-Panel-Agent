# 🎬 Guía para Videos Reales

## 📁 Estructura de Carpetas

```
data/
├── podcasts/          # Videos principales (conversaciones)
├── broll/            # Videos de fondo (visual)
├── transcripts/      # Se genera automáticamente
├── segments/         # Se genera automáticamente  
└── shorts/          # Output final
```

## 🎙️ PODCASTS (data/podcasts/)

### ✅ Requisitos Técnicos
- **Formatos:** MP4, MOV, AVI, MKV
- **Duración:** 10-120 minutos
- **Audio:** Claro, buena calidad
- **Resolución:** Cualquiera (720p+)

### 🎯 Contenido Ideal
- Entrevistas técnicas
- Podcasts de programación
- Charlas de tecnología
- Debates sobre IA/ML
- Tutoriales extensos
- Conferencias

### 💡 Consejos
- Audio claro es MÁS importante que video
- Conversaciones naturales funcionan mejor
- Contenido en español preferible
- Evitar música de fondo fuerte

## 🎨 B-ROLL (data/broll/)

### ✅ Requisitos Técnicos
- **Formatos:** MP4, MOV preferible
- **Duración:** 30 segundos - 5 minutos
- **Resolución:** 1080p mínimo
- **Sin audio** (se elimina automático)

### 🎯 Contenido Ideal
- Paisajes urbanos (drone)
- Código/pantallas de programación
- Naturaleza/timelapses
- Personas trabajando
- Motion graphics
- Elementos abstractos

### 💡 Consejos
- Movimiento suave y constante
- Sin texto/logos prominentes
- Estilo cohesivo
- Loops naturales

## 🚀 Proceso de Uso

1. **Coloca videos:**
   ```bash
   data/podcasts/mi_podcast.mp4
   data/broll/city_drone.mp4
   ```

2. **Ejecuta pipeline:**
   ```bash
   make transcribe VIDEO=data/podcasts/mi_podcast.mp4
   make segment TRANSCRIPT=data/transcripts/mi_podcast_transcript.json
   make compose PODCAST=data/podcasts/mi_podcast.mp4 BROLL=data/broll/city_drone.mp4
   ```

3. **¡Shorts listos en data/shorts/!**

## 📊 Recomendaciones por Temática

### 🖥️ **Tech/Programming**
- **Podcast:** Entrevistas con devs, charlas técnicas
- **B-roll:** Código, oficinas tech, ciudades modernas

### 🎓 **Educational**
- **Podcast:** Explicaciones, tutoriales
- **B-roll:** Estudiantes, libros, naturaleza

### 💼 **Business/Startup**
- **Podcast:** Entrevistas entrepreneurs
- **B-roll:** Oficinas, ciudades, people working

### 🔬 **Science/AI**
- **Podcast:** Debates sobre IA, research
- **B-roll:** Labs, abstract visuals, data viz
