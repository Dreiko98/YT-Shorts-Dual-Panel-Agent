"""
Stubs de módulos del pipeline - Implementación futura
"""

# discovery.py - Descubrimiento de contenido vía YouTube API
def discover_videos(channel_ids, max_videos=50):
    """Descubrir nuevos videos de los canales especificados."""
    # TODO: Implementar YouTube Data API v3
    # - Autenticación OAuth2
    # - Búsqueda por canal
    # - Filtrado por duración/fecha
    # - Almacenar en BD
    pass


# downloader.py - Descarga con yt-dlp
def download_video(video_id, output_path, quality="best[height<=1080]"):
    """Descargar video usando yt-dlp."""
    # TODO: Implementar descarga con yt-dlp
    # - Configurar formatos y calidad
    # - Manejo de errores y reintentos
    # - Progress tracking
    # - Validación post-descarga
    pass


# normalize.py - Normalización de audio/video
def normalize_media(input_path, output_path, target_fps=30):
    """Normalizar audio y video para consistencia."""
    # TODO: Implementar normalización con ffmpeg
    # - Normalizar audio (-14 LUFS)
    # - Estandarizar FPS
    # - Resolver resolución
    # - Validar integridad
    pass


# transcribe.py - Transcripción con Whisper
def transcribe_audio(audio_path, model="base", language=None):
    """Generar transcripción usando Whisper."""
    # TODO: Implementar Whisper
    # - Cargar modelo local
    # - Procesar audio
    # - Generar .srt y .json
    # - Manejo de GPU/CPU
    pass


# segmenter.py - Segmentación inteligente
def create_segments(video_path, transcript_path, rules_config):
    """Crear clips candidatos basados en transcripción."""
    # TODO: Implementar segmentación
    # - Analizar transcript por palabras clave
    # - Detectar pausas naturales
    # - Scoring de clips
    # - Validar duración
    pass


# broll_picker.py - Selección de B-roll
def select_broll(clip_duration, content_keywords, pool_config):
    """Seleccionar B-roll apropiado para el clip."""
    # TODO: Implementar selección inteligente
    # - Matching por palabras clave
    # - Rotación para evitar repetición
    # - Validar duración y calidad
    # - Preparar para loop si necesario
    pass


# layout.py - Composición de layout dual-panel
def create_dual_panel_layout(podcast_clip, broll_clip, layout_config):
    """Crear layout dual-panel con podcast arriba y B-roll abajo."""
    # TODO: Implementar composición
    # - Panel superior con audio
    # - Panel inferior muteado
    # - Divisor entre paneles  
    # - Safe areas para subtítulos
    pass


# subtitles.py - Subtítulos quemados
def add_burned_subtitles(video_path, srt_path, layout_config):
    """Añadir subtítulos quemados solo en panel superior."""
    # TODO: Implementar subtítulos
    # - Parsing de .srt
    # - Posicionamiento en safe area
    # - Estilo consistente con branding
    # - Solo en panel superior
    pass


# editor.py - Composición final
def compose_final_short(podcast_clip, broll_clip, subtitles, layout_config):
    """Componer Short final con todos los elementos."""
    # TODO: Implementar editor principal
    # - Combinar todos los elementos
    # - Aplicar layout y branding
    # - Renderizar con calidad apropiada
    # - Validar salida
    pass


# qc.py - Control de calidad
def quality_check(video_path, requirements):
    """Validar que el Short cumple todos los requisitos."""
    # TODO: Implementar QC
    # - Verificar duración ≤59.5s
    # - Validar resolución 1080x1920
    # - Comprobar audio solo arriba
    # - Verificar legibilidad subtítulos
    pass


# publisher.py - Publicación en YouTube
def upload_to_youtube(video_path, metadata, credentials):
    """Subir Short a YouTube con metadatos apropiados."""
    # TODO: Implementar YouTube API upload
    # - Autenticación OAuth2
    # - Upload con metadatos
    # - Configurar como Short
    # - Tracking de resultados
    pass
