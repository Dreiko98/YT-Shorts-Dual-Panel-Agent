"""
Sistema de subtítulos quemados para YouTube Shorts.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import tempfile

from ..utils.ffmpeg import run_ffmpeg_command, FFmpegError
from ..utils.text import parse_srt_file, format_srt_timestamp

logger = logging.getLogger(__name__)


class SubtitleError(Exception):
    """Error específico de subtítulos."""
    pass


@dataclass
class SubtitleStyle:
    """Configuración de estilo de subtítulos."""
    font_family: str = "Arial"
    font_size: int = 52  # Aumentado para mejor visibilidad
    font_color: str = "#FFFFFF"
    font_weight: str = "bold"
    outline_color: str = "#000000"
    outline_width: int = 3
    shadow_color: str = "#000000"
    shadow_offset: Tuple[int, int] = (2, 2)
    background_color: Optional[str] = None
    background_alpha: float = 0.0
    text_align: str = "center"
    margin_bottom: int = 960  # Centro del canvas (mitad de 1920)
    max_width: int = 950
    line_spacing: float = 1.2
    position: str = "center"  # Centrado en el divisor
    
    def to_ffmpeg_style(self) -> str:
        """Convertir estilo a formato ffmpeg."""
        style_parts = [
            f"FontName={self.font_family}",
            f"FontSize={self.font_size}",
            f"PrimaryColour={self._color_to_ass(self.font_color)}",
            f"OutlineColour={self._color_to_ass(self.outline_color)}",
            f"Outline={self.outline_width}",
            f"Shadow=1",
            f"Alignment=2",  # Bottom center
            f"MarginV={self.margin_bottom}",
            f"Spacing={int(self.line_spacing * 10)}"
        ]
        
        if self.background_color:
            style_parts.append(f"BackColour={self._color_to_ass(self.background_color)}")
        
        return ",".join(style_parts)
    
    def _color_to_ass(self, hex_color: str) -> str:
        """Convertir color hex a formato ASS."""
        # Remover # si está presente
        if hex_color.startswith('#'):
            hex_color = hex_color[1:]
        
        # Convertir de RGB a BGR (formato ASS)
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"&H{b:02X}{g:02X}{r:02X}"
        
        return "&HFFFFFF"  # Blanco por defecto


@dataclass
class SubtitleSegment:
    """Segmento de subtítulo con timing."""
    start_time: float
    end_time: float
    text: str
    style: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """Duración del segmento."""
        return self.end_time - self.start_time
    
    def to_ass_event(self, layer: int = 0) -> str:
        """Convertir a evento ASS."""
        start_ass = self._seconds_to_ass_time(self.start_time)
        end_ass = self._seconds_to_ass_time(self.end_time)
        
        # Limpiar texto para ASS
        clean_text = self._clean_text_for_ass(self.text)
        
        return f"Dialogue: {layer},{start_ass},{end_ass},Default,,0,0,0,,{clean_text}"
    
    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convertir segundos a formato de tiempo ASS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        
        return f"{hours:01d}:{minutes:02d}:{secs:05.2f}"
    
    def _clean_text_for_ass(self, text: str) -> str:
        """Limpiar texto para formato ASS."""
        # Remover caracteres problemáticos
        text = re.sub(r'[{}]', '', text)
        
        # Escapar caracteres especiales
        text = text.replace('\\', '\\\\')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        
        return text.strip()


class BurnedSubtitleRenderer:
    """Renderizador de subtítulos quemados usando ffmpeg."""
    
    def __init__(self, style: Optional[SubtitleStyle] = None):
        """
        Inicializar renderizador.
        
        Args:
            style: Configuración de estilo o None para usar por defecto
        """
        self.style = style or SubtitleStyle()
        logger.info("BurnedSubtitleRenderer inicializado")
    
    def add_subtitles_to_video(self, 
                              video_path: Path,
                              subtitles: List[SubtitleSegment],
                              output_path: Path,
                              safe_zone: Optional[Dict[str, int]] = None) -> bool:
        """
        Añadir subtítulos quemados a un video.
        
        Args:
            video_path: Video origen
            subtitles: Lista de segmentos de subtítulos
            output_path: Video con subtítulos
            safe_zone: Zona segura para subtítulos (x, y, width, height)
            
        Returns:
            True si fue exitoso
        """
        if not video_path.exists():
            raise SubtitleError(f"Video no encontrado: {video_path}")
        
        if not subtitles:
            logger.warning("No hay subtítulos para añadir")
            return self._copy_video_without_subtitles(video_path, output_path)
        
        # Crear archivo ASS temporal
        ass_file = self._create_ass_file(subtitles, safe_zone)
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Comando ffmpeg para quemar subtítulos
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vf", f"ass={ass_file}",
                "-c:v", "libx264",
                "-c:a", "copy",
                "-preset", "medium",
                str(output_path)
            ]
            
            success = run_ffmpeg_command(cmd)
            
            if success:
                logger.info(f"Subtítulos añadidos exitosamente: {output_path}")
            else:
                logger.error("Error añadiendo subtítulos")
            
            return success
            
        except FFmpegError as e:
            logger.error(f"Error en ffmpeg: {e}")
            return False
        
        finally:
            # Limpiar archivo temporal
            if ass_file and Path(ass_file).exists():
                Path(ass_file).unlink()
    
    def add_subtitles_from_srt(self,
                              video_path: Path,
                              srt_path: Path,
                              output_path: Path,
                              safe_zone: Optional[Dict[str, int]] = None) -> bool:
        """
        Añadir subtítulos desde archivo SRT.
        
        Args:
            video_path: Video origen
            srt_path: Archivo SRT con subtítulos
            output_path: Video con subtítulos
            safe_zone: Zona segura para subtítulos
            
        Returns:
            True si fue exitoso
        """
        if not srt_path.exists():
            raise SubtitleError(f"Archivo SRT no encontrado: {srt_path}")
        
        # Parsear archivo SRT
        try:
            srt_data = parse_srt_file(srt_path)
            
            # Convertir a SubtitleSegments
            subtitles = []
            for item in srt_data:
                segment = SubtitleSegment(
                    start_time=item['start'],
                    end_time=item['end'],
                    text=item['text']
                )
                subtitles.append(segment)
            
            return self.add_subtitles_to_video(
                video_path, subtitles, output_path, safe_zone
            )
            
        except Exception as e:
            raise SubtitleError(f"Error procesando SRT: {e}")
    
    def _create_ass_file(self, subtitles: List[SubtitleSegment],
                        safe_zone: Optional[Dict[str, int]] = None) -> str:
        """Crear archivo ASS temporal con los subtítulos."""
        
        # Ajustar estilo si hay zona segura definida
        style = self.style
        if safe_zone:
            # Ajustar posición y tamaño basado en safe_zone
            style.margin_bottom = safe_zone.get('y', style.margin_bottom)
            style.max_width = min(safe_zone.get('width', style.max_width), style.max_width)
        
        # Crear contenido ASS
        ass_content = self._generate_ass_header(style)
        
        # Añadir eventos de subtítulos
        for subtitle in subtitles:
            ass_content += subtitle.to_ass_event() + "\n"
        
        # Escribir archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            return f.name
    
    def _generate_ass_header(self, style: SubtitleStyle) -> str:
        """Generar cabecera del archivo ASS."""
        return f"""[Script Info]
Title: Burned Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_family},{style.font_size},{style._color_to_ass(style.font_color)},&H000000FF,{style._color_to_ass(style.outline_color)},&H80000000,1,0,0,0,100,100,0,0,1,{style.outline_width},1,2,20,20,{style.margin_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def _copy_video_without_subtitles(self, input_path: Path, output_path: Path) -> bool:
        """Copiar video sin modificaciones cuando no hay subtítulos."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-c", "copy",
            str(output_path)
        ]
        
        try:
            return run_ffmpeg_command(cmd)
        except FFmpegError:
            return False


def create_subtitles_from_transcript(transcript_data: Dict[str, Any],
                                   max_chars_per_line: int = 40,
                                   max_lines: int = 2) -> List[SubtitleSegment]:
    """
    Crear subtítulos desde datos de transcripción.
    
    Args:
        transcript_data: Datos de transcripción con segmentos
        max_chars_per_line: Máximo caracteres por línea
        max_lines: Máximo líneas por subtítulo
        
    Returns:
        Lista de segmentos de subtítulos
    """
    subtitles = []
    
    segments = transcript_data.get("segments", [])
    
    for segment in segments:
        text = segment.get("text", "").strip()
        start_time = segment.get("start", 0)
        end_time = segment.get("end", 0)
        
        if not text or end_time <= start_time:
            continue
        
        # Dividir texto largo en múltiples subtítulos
        if len(text) > max_chars_per_line * max_lines:
            sub_segments = _split_long_text(
                text, start_time, end_time, 
                max_chars_per_line, max_lines
            )
            subtitles.extend(sub_segments)
        else:
            # Formatear texto para múltiples líneas si es necesario
            formatted_text = _format_text_for_subtitle(text, max_chars_per_line)
            
            subtitle = SubtitleSegment(
                start_time=start_time,
                end_time=end_time,
                text=formatted_text
            )
            subtitles.append(subtitle)
    
    return subtitles


def _split_long_text(text: str, start_time: float, end_time: float,
                    max_chars_per_line: int, max_lines: int) -> List[SubtitleSegment]:
    """Dividir texto largo en múltiples segmentos de subtítulos."""
    max_chars_total = max_chars_per_line * max_lines
    words = text.split()
    segments = []
    
    current_text = ""
    segment_start = start_time
    duration_per_char = (end_time - start_time) / len(text)
    
    for word in words:
        test_text = current_text + " " + word if current_text else word
        
        if len(test_text) <= max_chars_total:
            current_text = test_text
        else:
            # Crear segmento con texto actual
            if current_text:
                segment_end = segment_start + len(current_text) * duration_per_char
                formatted_text = _format_text_for_subtitle(current_text, max_chars_per_line)
                
                segments.append(SubtitleSegment(
                    start_time=segment_start,
                    end_time=segment_end,
                    text=formatted_text
                ))
                
                segment_start = segment_end
            
            current_text = word
    
    # Añadir último segmento
    if current_text:
        formatted_text = _format_text_for_subtitle(current_text, max_chars_per_line)
        segments.append(SubtitleSegment(
            start_time=segment_start,
            end_time=end_time,
            text=formatted_text
        ))
    
    return segments


def _format_text_for_subtitle(text: str, max_chars_per_line: int) -> str:
    """Formatear texto para subtítulo dividiendo en líneas apropiadas."""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        
        if len(test_line) <= max_chars_per_line:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
                current_line = word
            else:
                # Palabra muy larga, forzar división
                lines.append(word)
                current_line = ""
    
    if current_line:
        lines.append(current_line)
    
    return "\n".join(lines)


def validate_subtitle_timing(subtitles: List[SubtitleSegment]) -> List[str]:
    """
    Validar timing de subtítulos.
    
    Returns:
        Lista de errores encontrados
    """
    errors = []
    
    for i, subtitle in enumerate(subtitles):
        # Validar duración mínima
        if subtitle.duration < 0.5:
            errors.append(f"Subtítulo {i+1}: duración muy corta ({subtitle.duration:.2f}s)")
        
        # Validar duración máxima
        if subtitle.duration > 10.0:
            errors.append(f"Subtítulo {i+1}: duración muy larga ({subtitle.duration:.2f}s)")
        
        # Validar timing válido
        if subtitle.start_time >= subtitle.end_time:
            errors.append(f"Subtítulo {i+1}: timing inválido")
        
        # Validar solapamiento con siguiente
        if i < len(subtitles) - 1:
            next_subtitle = subtitles[i + 1]
            if subtitle.end_time > next_subtitle.start_time:
                errors.append(f"Subtítulo {i+1}: solapa con el siguiente")
    
    return errors


def create_subtitle_preview(subtitles: List[SubtitleSegment],
                           output_path: Path) -> bool:
    """
    Crear archivo de vista previa de subtítulos (solo texto).
    
    Args:
        subtitles: Lista de segmentos
        output_path: Archivo de salida
        
    Returns:
        True si fue exitoso
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Vista Previa de Subtítulos\n")
            f.write("=" * 50 + "\n\n")
            
            for i, subtitle in enumerate(subtitles, 1):
                f.write(f"[{i:03d}] {subtitle.start_time:.2f}s - {subtitle.end_time:.2f}s\n")
                f.write(f"{subtitle.text}\n\n")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creando preview: {e}")
        return False
