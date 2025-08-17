"""
Utilidades para procesamiento de video.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import tempfile
import json

from .ffmpeg import run_ffmpeg_command, get_video_info, FFmpegError

logger = logging.getLogger(__name__)


class VideoProcessingError(Exception):
    """Error específico de procesamiento de video."""
    pass


def extract_video_segment(input_path: Path, output_path: Path,
                         start_time: float, duration: float,
                         copy_streams: bool = True) -> bool:
    """
    Extraer segmento de video usando ffmpeg.
    
    Args:
        input_path: Archivo de video origen
        output_path: Archivo de salida
        start_time: Tiempo de inicio en segundos
        duration: Duración del segmento en segundos
        copy_streams: Si True, copia streams sin recodificar (más rápido)
        
    Returns:
        True si fue exitoso
    """
    if not input_path.exists():
        raise VideoProcessingError(f"Video origen no encontrado: {input_path}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Construir comando ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", str(input_path),
        "-t", str(duration)
    ]
    
    if copy_streams:
        # Copia sin recodificar (más rápido pero menos preciso)
        cmd.extend(["-c", "copy"])
    else:
        # Recodificar (más lento pero más preciso)
        cmd.extend([
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "medium"
        ])
    
    cmd.append(str(output_path))
    
    try:
        return run_ffmpeg_command(cmd)
    except FFmpegError as e:
        logger.error(f"Error extrayendo segmento: {e}")
        return False


def resize_video(input_path: Path, output_path: Path,
                width: int, height: int,
                maintain_aspect: bool = True,
                background_color: str = "black") -> bool:
    """
    Redimensionar video manteniendo proporción.
    
    Args:
        input_path: Video origen
        output_path: Video redimensionado
        width: Ancho objetivo
        height: Alto objetivo
        maintain_aspect: Si mantener proporción original
        background_color: Color de fondo si hay letterboxing
        
    Returns:
        True si fue exitoso
    """
    if not input_path.exists():
        raise VideoProcessingError(f"Video origen no encontrado: {input_path}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if maintain_aspect:
        # Scale manteniendo proporción y añadir padding si es necesario
        scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease," \
                      f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={background_color}"
    else:
        # Escalar ignorando proporción
        scale_filter = f"scale={width}:{height}"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", scale_filter,
        "-c:v", "libx264",
        "-c:a", "copy",
        "-preset", "medium",
        str(output_path)
    ]
    
    try:
        return run_ffmpeg_command(cmd)
    except FFmpegError as e:
        logger.error(f"Error redimensionando video: {e}")
        return False


def remove_audio_track(input_path: Path, output_path: Path) -> bool:
    """
    Remover pista de audio de un video.
    
    Args:
        input_path: Video con audio
        output_path: Video sin audio
        
    Returns:
        True si fue exitoso
    """
    if not input_path.exists():
        raise VideoProcessingError(f"Video origen no encontrado: {input_path}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-c:v", "copy",
        "-an",  # Remover audio
        str(output_path)
    ]
    
    try:
        return run_ffmpeg_command(cmd)
    except FFmpegError as e:
        logger.error(f"Error removiendo audio: {e}")
        return False


def create_video_loop(input_path: Path, output_path: Path,
                     target_duration: float) -> bool:
    """
    Crear un loop de video hasta alcanzar duración objetivo.
    
    Args:
        input_path: Video origen
        output_path: Video con loop
        target_duration: Duración objetivo en segundos
        
    Returns:
        True si fue exitoso
    """
    if not input_path.exists():
        raise VideoProcessingError(f"Video origen no encontrado: {input_path}")
    
    try:
        # Obtener duración del video origen
        video_info = get_video_info(input_path)
        source_duration = video_info.get("duration", 0)
        
        if source_duration <= 0:
            raise VideoProcessingError("No se pudo determinar duración del video")
        
        if source_duration >= target_duration:
            # Video ya es suficientemente largo, solo recortar
            return extract_video_segment(input_path, output_path, 0, target_duration)
        
        # Calcular cuántas repeticiones necesitamos
        loops_needed = int(target_duration / source_duration) + 1
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loops_needed - 1),
            "-i", str(input_path),
            "-t", str(target_duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "medium",
            str(output_path)
        ]
        
        return run_ffmpeg_command(cmd)
        
    except (FFmpegError, VideoProcessingError) as e:
        logger.error(f"Error creando loop: {e}")
        return False


def compose_dual_panel_ffmpeg(podcast_path: Path, broll_path: Path,
                             output_path: Path, duration: float,
                             width: int = 1080, height: int = 1920) -> bool:
    """
    Crear composición dual-panel usando ffmpeg directamente.
    
    Args:
        podcast_path: Video de podcast (panel superior con audio)
        broll_path: Video de B-roll (panel inferior sin audio)
        output_path: Video compuesto final
        duration: Duración del clip final
        width: Ancho del video final
        height: Alto del video final
        
    Returns:
        True si fue exitoso
    """
    if not podcast_path.exists():
        raise VideoProcessingError(f"Video de podcast no encontrado: {podcast_path}")
    
    if not broll_path.exists():
        raise VideoProcessingError(f"Video de B-roll no encontrado: {broll_path}")
    
    # Calcular dimensiones de cada panel
    panel_height = height // 2  # Dividir en dos paneles iguales
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Comando ffmpeg complejo para composición dual-panel
    cmd = [
        "ffmpeg", "-y",
        "-i", str(podcast_path),    # Input 0: podcast
        "-i", str(broll_path),      # Input 1: b-roll
        "-filter_complex", f"""
        [0:v]scale={width}:{panel_height}:force_original_aspect_ratio=decrease,pad={width}:{panel_height}:(ow-iw)/2:(oh-ih)/2:color=black[top];
        [1:v]scale={width}:{panel_height}:force_original_aspect_ratio=decrease,pad={width}:{panel_height}:(ow-iw)/2:(oh-ih)/2:color=black[bottom];
        [top][bottom]vstack=inputs=2[video]
        """,
        "-map", "[video]",
        "-map", "0:a?",  # Audio solo del podcast (si existe)
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "medium",
        "-r", "30",  # 30 fps
        str(output_path)
    ]
    
    try:
        return run_ffmpeg_command(cmd)
    except FFmpegError as e:
        logger.error(f"Error en composición dual-panel: {e}")
        return False


def add_letterbox_padding(input_path: Path, output_path: Path,
                         target_width: int, target_height: int,
                         background_color: str = "black") -> bool:
    """
    Añadir letterbox/pillarbox para ajustar video a dimensiones objetivo.
    
    Args:
        input_path: Video origen
        output_path: Video con padding
        target_width: Ancho objetivo
        target_height: Alto objetivo
        background_color: Color del padding
        
    Returns:
        True si fue exitoso
    """
    if not input_path.exists():
        raise VideoProcessingError(f"Video origen no encontrado: {input_path}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
               f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color={background_color}",
        "-c:v", "libx264",
        "-c:a", "copy",
        "-preset", "medium",
        str(output_path)
    ]
    
    try:
        return run_ffmpeg_command(cmd)
    except FFmpegError as e:
        logger.error(f"Error añadiendo padding: {e}")
        return False


def get_video_aspect_ratio(input_path: Path) -> Optional[float]:
    """
    Obtener proporción de aspecto del video.
    
    Args:
        input_path: Ruta al archivo de video
        
    Returns:
        Proporción de aspecto (width/height) o None si hay error
    """
    try:
        info = get_video_info(input_path)
        width = info.get("width", 0)
        height = info.get("height", 0)
        
        if width > 0 and height > 0:
            return width / height
        
        return None
    except FFmpegError:
        return None


def optimize_for_youtube_shorts(input_path: Path, output_path: Path) -> bool:
    """
    Optimizar video para YouTube Shorts (1080x1920, 30fps, etc.).
    
    Args:
        input_path: Video origen
        output_path: Video optimizado
        
    Returns:
        True si fue exitoso
    """
    if not input_path.exists():
        raise VideoProcessingError(f"Video origen no encontrado: {input_path}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
               "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "medium",
        "-profile:v", "high",
        "-level:v", "4.0",
        "-pix_fmt", "yuv420p",
        "-r", "30",  # 30 fps
        "-b:v", "8M",  # Bitrate de video
        "-b:a", "128k",  # Bitrate de audio
        "-maxrate", "12M",
        "-bufsize", "16M",
        str(output_path)
    ]
    
    try:
        return run_ffmpeg_command(cmd)
    except FFmpegError as e:
        logger.error(f"Error optimizando para YouTube Shorts: {e}")
        return False


def create_test_video(output_path: Path, duration: float = 10,
                     width: int = 1080, height: int = 1920,
                     fps: int = 30) -> bool:
    """
    Crear video de prueba con patrón de colores.
    
    Args:
        output_path: Ruta del video de prueba
        duration: Duración en segundos
        width: Ancho del video
        height: Alto del video
        fps: Frames por segundo
        
    Returns:
        True si fue exitoso
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"testsrc2=size={width}x{height}:duration={duration}:rate={fps}",
        "-f", "lavfi", 
        "-i", f"sine=frequency=1000:duration={duration}",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "ultrafast",
        str(output_path)
    ]
    
    try:
        return run_ffmpeg_command(cmd)
    except FFmpegError as e:
        logger.error(f"Error creando video de prueba: {e}")
        return False


def validate_video_for_shorts(video_path: Path) -> Dict[str, Any]:
    """
    Validar que un video cumple requisitos de YouTube Shorts.
    
    Args:
        video_path: Ruta al video a validar
        
    Returns:
        Dict con resultados de validación
    """
    if not video_path.exists():
        return {
            "valid": False,
            "errors": ["Archivo no encontrado"],
            "warnings": []
        }
    
    try:
        info = get_video_info(video_path)
        
        errors = []
        warnings = []
        
        # Verificar dimensiones
        width = info.get("width", 0)
        height = info.get("height", 0)
        
        if width != 1080 or height != 1920:
            errors.append(f"Dimensiones incorrectas: {width}x{height} (esperado: 1080x1920)")
        
        # Verificar duración
        duration = info.get("duration", 0)
        if duration > 60:
            errors.append(f"Duración muy larga: {duration:.1f}s (máximo: 60s)")
        elif duration > 59.5:
            warnings.append(f"Duración cerca del límite: {duration:.1f}s")
        
        # Verificar FPS
        fps = info.get("fps", 0)
        if fps not in [24, 25, 30, 50, 60]:
            warnings.append(f"FPS no estándar: {fps}")
        
        # Verificar audio
        has_audio = info.get("has_audio", False)
        if not has_audio:
            warnings.append("Video no tiene pista de audio")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "info": info
        }
        
    except FFmpegError as e:
        return {
            "valid": False,
            "errors": [f"Error analizando video: {e}"],
            "warnings": []
        }
