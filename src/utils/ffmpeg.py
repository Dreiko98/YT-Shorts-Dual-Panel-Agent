"""
Utilidades para trabajar con ffmpeg de forma segura y robusta.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Error específico de ffmpeg."""
    pass


def check_ffmpeg_available() -> bool:
    """Verificar si ffmpeg está disponible en el sistema."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_ffmpeg_command(cmd: List[str], timeout: int = 300) -> bool:
    """
    Ejecutar comando ffmpeg con manejo de errores.
    
    Args:
        cmd: Lista con el comando y argumentos
        timeout: Timeout en segundos
        
    Returns:
        True si el comando fue exitoso
        
    Raises:
        FFmpegError: Si hay error ejecutando ffmpeg
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            timeout=timeout,
            text=True
        )
        
        logger.debug(f"ffmpeg command successful: {' '.join(cmd)}")
        return True
        
    except subprocess.CalledProcessError as e:
        error_msg = f"ffmpeg failed with code {e.returncode}"
        if e.stderr:
            error_msg += f": {e.stderr}"
        logger.error(error_msg)
        raise FFmpegError(error_msg)
    
    except subprocess.TimeoutExpired:
        error_msg = f"ffmpeg command timed out after {timeout}s"
        logger.error(error_msg)
        raise FFmpegError(error_msg)
    
    except FileNotFoundError:
        error_msg = "ffmpeg not found in system PATH"
        logger.error(error_msg)
        raise FFmpegError(error_msg)


def get_video_info(video_path: Path) -> Dict[str, Any]:
    """Obtener información detallada de un archivo de video usando ffprobe."""
    if not video_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {video_path}")
    
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path)
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=30,
            check=True
        )
        
        info = json.loads(result.stdout)
        
        # Extraer información útil
        format_info = info.get("format", {})
        video_stream = None
        audio_stream = None
        
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video" and not video_stream:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and not audio_stream:
                audio_stream = stream
        
        return {
            "duration": float(format_info.get("duration", 0)),
            "size_bytes": int(format_info.get("size", 0)),
            "bitrate": int(format_info.get("bit_rate", 0)),
            "video": {
                "codec": video_stream.get("codec_name") if video_stream else None,
                "width": int(video_stream.get("width", 0)) if video_stream else 0,
                "height": int(video_stream.get("height", 0)) if video_stream else 0,
                "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream else 0,
                "bitrate": int(video_stream.get("bit_rate", 0)) if video_stream else 0,
            },
            "audio": {
                "codec": audio_stream.get("codec_name") if audio_stream else None,
                "sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else 0,
                "channels": int(audio_stream.get("channels", 0)) if audio_stream else 0,
                "bitrate": int(audio_stream.get("bit_rate", 0)) if audio_stream else 0,
            }
        }
        
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"Error ejecutando ffprobe: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise FFmpegError("Timeout ejecutando ffprobe")
    except json.JSONDecodeError as e:
        raise FFmpegError(f"Error parseando salida de ffprobe: {e}")


def extract_audio(video_path: Path, audio_path: Path, 
                 sample_rate: int = 16000) -> bool:
    """Extraer audio de un video para Whisper."""
    try:
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # Sin video
            "-acodec", "pcm_s16le",  # PCM 16-bit para Whisper
            "-ar", str(sample_rate),  # Sample rate para Whisper
            "-ac", "1",  # Mono
            "-y",  # Sobrescribir si existe
            str(audio_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos max
        )
        
        if result.returncode != 0:
            logger.error(f"Error extrayendo audio: {result.stderr}")
            return False
            
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            logger.error("Archivo de audio no se creó o está vacío")
            return False
            
        logger.info(f"Audio extraído: {audio_path}")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout extrayendo audio")
        return False
    except Exception as e:
        logger.error(f"Error inesperado extrayendo audio: {e}")
        return False


def extract_video_segment(video_path: Path, output_path: Path,
                         start_seconds: float, duration_seconds: float,
                         include_audio: bool = True) -> bool:
    """Extraer un segmento específico del video."""
    try:
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", str(start_seconds),
            "-t", str(duration_seconds),
            "-c", "copy" if include_audio else "copy",  # Copia sin recodificar
            "-avoid_negative_ts", "make_zero",
            "-y",
            str(output_path)
        ]
        
        # Si no queremos audio, añadir -an
        if not include_audio:
            cmd.insert(-2, "-an")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            logger.error(f"Error extrayendo segmento: {result.stderr}")
            return False
            
        if not output_path.exists():
            logger.error("Segmento no se creó")
            return False
            
        logger.info(f"Segmento extraído: {output_path}")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout extrayendo segmento")
        return False
    except Exception as e:
        logger.error(f"Error extrayendo segmento: {e}")
        return False


def normalize_audio_loudness(input_path: Path, output_path: Path, 
                           target_lufs: float = -14.0) -> bool:
    """Normalizar loudness del audio a un nivel específico."""
    try:
        # Primer paso: medir loudness actual
        measure_cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-af", "loudnorm=I=-14:LRA=11:TP=-1.5:print_format=json",
            "-f", "null",
            "-"
        ]
        
        measure_result = subprocess.run(
            measure_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # El JSON está en stderr de ffmpeg
        json_start = measure_result.stderr.rfind('{')
        if json_start == -1:
            logger.warning("No se pudo medir loudness, usando normalización básica")
            # Fallback a normalización simple
            normalize_cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-af", f"loudnorm=I={target_lufs}",
                "-y",
                str(output_path)
            ]
        else:
            loudness_data = json.loads(measure_result.stderr[json_start:])
            
            # Segundo paso: normalizar con datos medidos
            normalize_cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-af", f"loudnorm=I={target_lufs}:LRA=11:TP=-1.5:measured_I={loudness_data['input_i']}:measured_LRA={loudness_data['input_lra']}:measured_TP={loudness_data['input_tp']}:measured_thresh={loudness_data['input_thresh']}",
                "-y",
                str(output_path)
            ]
        
        result = subprocess.run(
            normalize_cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            logger.error(f"Error normalizando audio: {result.stderr}")
            return False
            
        logger.info(f"Audio normalizado: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error normalizando audio: {e}")
        return False


def get_safe_filename(filename: str) -> str:
    """Convertir nombre de archivo a formato seguro."""
    import re
    # Remover caracteres problemáticos
    safe = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe = re.sub(r'\s+', '_', safe)  # Espacios a guiones bajos
    safe = safe.strip('._')  # Remover puntos/guiones al inicio/final
    return safe[:200]  # Limitar longitud
