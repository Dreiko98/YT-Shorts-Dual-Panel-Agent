# Ejemplo de uso básico

## Descargar archivos de prueba

Para probar el sistema necesitas:

### 1. Podcast de ejemplo (10-30 minutos)
```bash
# Ejemplo: descargar un podcast de dominio público
cd data/raw/podcast
# wget "URL_DEL_PODCAST.mp4"
# O arrastra manualmente un archivo de audio/video
```

### 2. B-roll de ejemplo
```bash  
cd data/raw/broll/subway
# Coloca videos verticales sin audio importante
# Ejemplos: gameplay, animaciones, videos dinámicos
```

## Comando de prueba rápida

Una vez tengas archivos:

```bash
# 1. Transcribir
make transcribe VIDEO=data/raw/podcast/tu_archivo.mp4

# 2. Segmentar 
make segment TRANSCRIPT=data/transcriptions/tu_archivo_transcript.json

# 3. Componer Short final
make compose CANDIDATES=data/segments/candidatos.json
```

## ¿Sin archivos de prueba?

Si no tienes archivos, puedes:
1. Grabar un audio corto (2-5 min) hablando
2. Usar videos de stock gratuitos (Pixabay, Pexels)
3. Buscar podcasts de Creative Commons
