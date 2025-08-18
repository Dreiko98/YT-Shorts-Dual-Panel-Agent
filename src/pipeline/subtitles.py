"""
Sistema de subtítulos quemados para YouTube Shorts.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, replace
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
    font_size: int = 58  # Tamaño grande pero legible
    font_color: str = "#FFFFFF"  # Blanco puro
    font_weight: str = "bold"
    font_italic: bool = True  # Cursiva activada
    outline_color: str = "#000000"  # Contorno negro
    outline_width: int = 5  # Contorno grueso para mejor legibilidad
    shadow_color: str = "#404040"  # Sombra gris oscura
    shadow_offset: Tuple[int, int] = (4, 4)  # Sombra más pronunciada
    background_color: Optional[str] = "#80000000"  # Fondo semi-transparente
    background_alpha: float = 0.3  # Ligero fondo para contraste
    text_align: str = "center"
    margin_bottom: int = 880  # Posición centrada en el divisor
    max_width: int = 900
    line_spacing: float = 1.4  # Mayor espaciado entre líneas
    position: str = "center"
    dropshadow: bool = True  # Efecto de goteo/sombra profunda
    alignment_code: int = 5  # Código ASS (5 = middle-center in ASS (row middle, column center))
    absolute_positioning: bool = True  # Usar \pos(x,y) en lugar de Margins cuando sea posible
    
    def to_ffmpeg_style(self) -> str:
        """Convertir estilo a formato ffmpeg."""
        style_parts = [
            f"FontName={self.font_family}",
            f"FontSize={self.font_size}",
            f"PrimaryColour={self._color_to_ass(self.font_color)}",
            f"OutlineColour={self._color_to_ass(self.outline_color)}",
            f"Outline={self.outline_width}",
            f"Shadow={self.shadow_offset[0] if hasattr(self, 'dropshadow') and self.dropshadow else 1}",
            f"Alignment={self.alignment_code}",
            f"MarginV={self.margin_bottom}",
            f"Spacing={int(self.line_spacing * 10)}",
            f"Bold={-1 if self.font_weight == 'bold' else 0}",
            f"Italic={-1 if hasattr(self, 'font_italic') and self.font_italic else 0}"
        ]
        
        if self.background_color:
            style_parts.append(f"BackColour={self._color_to_ass(self.background_color)}")
            
        # Añadir sombra profunda si está habilitada
        if hasattr(self, 'dropshadow') and self.dropshadow:
            style_parts.append(f"SecondaryColour={self._color_to_ass(self.shadow_color)}")
        
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
    
    def to_ass_event(self, layer: int = 0, override_tag: Optional[str] = None) -> str:
        """Convertir a evento ASS con opción de tags override (\pos, \an, etc.)."""
        start_ass = self._seconds_to_ass_time(self.start_time)
        end_ass = self._seconds_to_ass_time(self.end_time)

        clean_text = self._clean_text_for_ass(self.text)
        # Reemplazar saltos de línea por \N para ASS
        clean_text = clean_text.replace('\n', '\\N')

        if override_tag:
            clean_text = f"{override_tag}{clean_text}"

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
                              safe_zone: Optional[Dict[str, int]] = None,
                              keep_ass: bool = False) -> bool:
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

        # Intentar enfoque drawtext (más directo) a menos que se fuerce solo ASS
        if not os.getenv("USE_ASS_ONLY"):
            try:
                if self._render_with_drawtext(video_path, subtitles, output_path, safe_zone):
                    logger.info("Subtítulos renderizados con drawtext")
                    return True
                else:
                    logger.warning("Fallback a ASS: drawtext no produjo salida visible")
            except Exception as e:
                logger.warning(f"Fallo drawtext ({e}), usando ASS")

        # Método ASS (fallback o forzado)
        ass_file = self._create_ass_file(subtitles, safe_zone)
        logger.debug(f"ASS file generado: {ass_file}")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vf", f"ass={ass_file}",
                "-c:v", "libx264",
                "-c:a", "copy",
                "-preset", "medium",
                str(output_path)
            ]
            logger.info("Ejecutando ffmpeg para quemar subtítulos (ASS)")
            logger.debug("Comando: %s", " ".join(cmd))
            success = run_ffmpeg_command(cmd)
            if success:
                logger.info(f"Subtítulos añadidos exitosamente (ASS): {output_path}")
            return success
        except FFmpegError as e:
            logger.error(f"Error en ffmpeg ASS: {e}")
            return False
        finally:
            if ass_file and Path(ass_file).exists() and not keep_ass and not os.getenv("DEBUG_KEEP_ASS"):
                Path(ass_file).unlink()
            elif ass_file and Path(ass_file).exists():
                logger.info(f"Manteniendo archivo ASS para debug: {ass_file}")
    
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

        # Copiar estilo para modificaciones locales
        style = replace(self.style)

        override_tag = None
        if safe_zone:
            # Calcular centro de la zona segura
            zone_x = safe_zone.get('x', 0)
            zone_y = safe_zone.get('y', style.margin_bottom)
            zone_w = safe_zone.get('width', style.max_width)
            zone_h = safe_zone.get('height', 0)
            style.max_width = min(zone_w, style.max_width)

            if style.absolute_positioning and not os.getenv('FORCE_BOTTOM_SUBS'):
                center_x = zone_x + zone_w // 2
                center_y = zone_y + zone_h // 2 if zone_h else zone_y + 40
                # Usar an5 (center) y posición absoluta
                style.alignment_code = 5
                # Margen pequeño para que no interfiera
                style.margin_bottom = 40
                override_tag = f"{{\\an5\\pos({center_x},{center_y})}}"
            else:
                # Fallback: bottom center calculando MarginV desde bottom
                style.alignment_code = 2
                total_h = 1920
                target_baseline = zone_y + (zone_h // 2 if zone_h else 0)
                style.margin_bottom = max(0, int(total_h - target_baseline))

        ass_content = self._generate_ass_header(style)

        for subtitle in subtitles:
            ass_content += subtitle.to_ass_event(override_tag=override_tag) + "\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            return f.name

    def _generate_ass_header(self, style: SubtitleStyle) -> str:
        """Generar cabecera del archivo ASS con efectos mejorados."""
        primary_color = style._color_to_ass(style.font_color)
        outline_color = style._color_to_ass(style.outline_color)
        shadow_color = style._color_to_ass(style.shadow_color) if hasattr(style, 'shadow_color') else "&H404040"
        back_color = style._color_to_ass(style.background_color) if style.background_color else "&H80000000"

        bold = -1 if style.font_weight == "bold" else 0
        italic = -1 if hasattr(style, 'font_italic') and style.font_italic else 0
        shadow_depth = 3 if hasattr(style, 'dropshadow') and style.dropshadow else 1

        return (
            "[Script Info]\n" \
            "Title: Styled Subtitles with Drop Shadow\n" \
            "ScriptType: v4.00+\n\n" \
            "[V4+ Styles]\n" \
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n" \
            f"Style: Default,{style.font_family},{style.font_size},{primary_color},{shadow_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,2,0,1,{style.outline_width},{shadow_depth},{style.alignment_code},40,40,{style.margin_bottom},1\n\n" \
            "[Events]\n" \
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

    # --- Nuevo método drawtext ---
    def _render_with_drawtext(self, video_path: Path, subtitles: List[SubtitleSegment], output_path: Path,
                              safe_zone: Optional[Dict[str, int]]) -> bool:
        """Renderizar subtítulos usando drawtext (sin ASS) para máxima compatibilidad.
        Construye una cadena de filtros concatenando múltiples drawtext con enable=between(t, start, end).
        """
        font_path_candidates = [
            Path("assets/fonts/YourFont.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
        font_file = None
        for p in font_path_candidates:
            if p.exists():
                font_file = p
                break
        if font_file is None:
            logger.warning("No se encontró fuente específica, usando drawtext sin fontfile")

        # Calcular centro de zona segura o fallback al centro general
        if safe_zone:
            zone_x = safe_zone.get('x', 0)
            zone_y = safe_zone.get('y', 960)
            zone_w = safe_zone.get('width', 960)
            zone_h = safe_zone.get('height', 160)
            center_x_expr = f"{zone_x + zone_w // 2}"
            center_y_expr = f"{zone_y + zone_h // 2}"
        else:
            center_x_expr = "(w/2)"
            center_y_expr = "(h/2)"

        # Definir tamaño de fuente relativo al ancho de la zona segura (valor empírico)
        if safe_zone:
            # Aproximadamente 5.5% del ancho para dos líneas legibles en vertical 1080x1920
            base_fontsize = max(40, int(zone_w * 0.058))
        else:
            base_fontsize = 56

        def _escape_drawtext(text: str) -> str:
            """Escapar caracteres especiales para drawtext.
            Reglas: escapar '\\', ':', "'" y reemplazar salto de línea por \n.
            """
            t = text.replace('\\', r'\\')
            t = t.replace(':', r'\:')
            t = t.replace("'", r"\\'")
            # Normalizar saltos de línea múltiples y convertir a \n
            t = t.replace('\r', '')
            t = t.replace('\n', '\n')
            return t

        # Build filter parts
        filter_parts = []
        color_cycle = os.getenv('FAST_SUB_COLOR_CYCLE', '1') == '1'
        keyword_colors = [
            ('gratis', 'yellow'),
            ('nuevo', 'cyan'),
            ('nueva', 'cyan'),
            ('importante', 'orange'),
            ('clave', 'orange'),
            ('hack', 'violet'),
        ]

        def colorize(text: str, idx: int) -> str:
            base_color = 'white'
            if color_cycle:
                palette = ['white','yellow','#55FFAA','#44CCFF','#FF66CC']
                base_color = palette[idx % len(palette)]
            lower = text.lower()
            for kw, col in keyword_colors:
                if kw in lower:
                    base_color = col
                    break
            return base_color

        enable_bounce = os.getenv('FAST_SUB_BOUNCE','1') == '1'
        bounce_freq = float(os.getenv('FAST_SUB_BOUNCE_FREQ','2.5'))

        for idx, seg in enumerate(subtitles):
            start = max(0, seg.start_time)
            end = max(start + 0.05, seg.end_time)
            # Escape text for drawtext
            txt = _escape_drawtext(seg.text)
            fontcolor = colorize(seg.text, idx)
            scale_expr = '1'
            if enable_bounce:
                # Suave: 1 + 0.06 * sin(2*pi*f*(t-start)) dentro de ventana
                scale_expr = f"(1+0.06*sin(2*PI*{bounce_freq}*(t-{start:.3f})))"
            # Usamos drawtext y luego scale2ref para efecto bounce con expandoverlay (simplificado: solo fontsize modulado)
            draw = "drawtext="
            if font_file:
                draw += f"fontfile='{font_file}':"
            draw += (
                f"text='{txt}':x=(w-text_w)/2:y={center_y_expr}-text_h/2:fontsize={base_fontsize}:fontcolor={fontcolor}"
                f":bordercolor=black:borderw=4:shadowcolor=black:shadowx=2:shadowy=2:box=1:boxcolor=black@0.55:boxborderw=18"
                f":enable='between(t,{start:.3f},{end:.3f})'"
            )
            if enable_bounce:
                # Aplicar efecto de ligero zoom via 'fontsize' no es dinámico; alternativa: usar 'scale' sobre overlay separado es complejo.
                # Simulación: duplicar drawtext con alpha para crear halo colorido animado (pequeño desplazamiento)
                halo = draw.replace("drawtext=", "drawtext=") + f":alpha='if(between(t,{start:.3f},{end:.3f}), (0.35+0.25*sin(2*PI*{bounce_freq}*(t-{start:.3f}))), 0)'"
                filter_parts.append(draw)
                filter_parts.append(halo)
            else:
                filter_parts.append(draw)

        if not filter_parts:
            return False

        vf = ",".join(filter_parts)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", vf,
            "-c:v", "libx264",
            "-c:a", "copy",
            "-preset", "medium",
            str(output_path)
        ]
        logger.debug(f"Comando drawtext: {' '.join(cmd)[:300]}...")
        try:
            return run_ffmpeg_command(cmd)
        except FFmpegError:
            return False
    
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
    # Modo alternativo: subtítulos rápidos (chunk de pocas palabras)
    if os.getenv("SHORT_SUB_MODE", "").lower() in {"fast", "rapid", "words"}:
        return _create_fast_word_subtitles(transcript_data)

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


def _create_fast_word_subtitles(transcript_data: Dict[str, Any],
                                target_words_per_sub: int = 3,
                                min_duration: float = 0.35,
                                max_duration: float = 1.2) -> List[SubtitleSegment]:
    """Generar subtítulos muy cortos y dinámicos (2-4 palabras) para ritmo rápido.

    Estrategia:
    - Usa los segmentos base (con tiempos start/end y palabras en 'words' si existen).
    - Si no hay 'words', divide texto por palabras estimando tiempos proporcionalmente.
    - Agrupa ~target_words_per_sub palabras, ajustando para no exceder max_duration.
    - Fuerza una duración mínima (min_duration) extendiendo end_time si necesario.
    - Une palabras con espacios sin saltos de línea para mantener una sola línea.
    """
    # Overrides por variables de entorno
    def _env_int(name: str, default: int, lo: int, hi: int) -> int:
        try:
            v = int(os.getenv(name, '').strip())
            if lo <= v <= hi:
                return v
        except Exception:
            pass
        return default

    def _env_float(name: str, default: float, lo: float, hi: float) -> float:
        try:
            v = float(os.getenv(name, '').strip())
            if lo <= v <= hi:
                return v
        except Exception:
            pass
        return default

    target_words_per_sub = _env_int('FAST_WORDS_TARGET', target_words_per_sub, 1, 10)
    min_duration = _env_float('FAST_SUB_MIN', min_duration, 0.1, 2.0)
    max_duration = _env_float('FAST_SUB_MAX', max_duration, 0.3, 3.5)
    if min_duration >= max_duration:
        max_duration = min_duration + 0.25
    logger.info(f"Fast subs config -> words:{target_words_per_sub} min:{min_duration:.2f}s max:{max_duration:.2f}s")

    segments = transcript_data.get("segments", [])
    results: List[SubtitleSegment] = []

    for seg in segments:
        text = seg.get("text", "").strip()
        start = seg.get("start", 0.0)
        end = seg.get("end", start)
        if not text or end <= start:
            continue

        words_meta = seg.get("words") or []
        words: List[Tuple[str, float, float]] = []  # (word, w_start, w_end)

        if words_meta and all('start' in w and 'end' in w for w in words_meta):
            for w in words_meta:
                wt = w.get('word') or w.get('text') or ''
                if not wt:
                    continue
                ws, we = float(w['start']), float(w['end'])
                if we > ws:
                    words.append((wt.strip(), ws, we))
        else:
            # Fallback: estimar tiempos proporcionales
            tokens = [t for t in text.split() if t]
            total = len(tokens)
            if total == 0:
                continue
            seg_dur = end - start
            per = seg_dur / total
            for i, tk in enumerate(tokens):
                ws = start + i * per
                we = min(end, ws + per)
                words.append((tk, ws, we))

        # Agrupar palabras
        chunk: List[Tuple[str, float, float]] = []
        for w, ws, we in words:
            if not chunk:
                chunk = [(w, ws, we)]
                continue

            chunk_words = [cw for cw, *_ in chunk]
            tentative_words = chunk_words + [w]
            tentative_start = chunk[0][1]
            tentative_end = we
            tentative_dur = tentative_end - tentative_start

            if (len(tentative_words) <= target_words_per_sub + 1 and
                tentative_dur <= max_duration):
                chunk.append((w, ws, we))
            else:
                # Emitir chunk actual
                cwds = [cw for cw, *_ in chunk]
                cstart = chunk[0][1]
                cend = chunk[-1][2]
                if cend - cstart < min_duration:
                    cend = min(cstart + min_duration, end)
                results.append(SubtitleSegment(start_time=cstart, end_time=cend, text=" ".join(cwds)))
                chunk = [(w, ws, we)]

        if chunk:
            cwds = [cw for cw, *_ in chunk]
            cstart = chunk[0][1]
            cend = chunk[-1][2]
            if cend - cstart < min_duration:
                cend = min(cstart + min_duration, end)
            results.append(SubtitleSegment(start_time=cstart, end_time=cend, text=" ".join(cwds)))

    # Post-procesar: evitar superposiciones y asegurar orden
    results.sort(key=lambda s: s.start_time)
    for i in range(len(results) - 1):
        if results[i].end_time > results[i+1].start_time:
            # Ajustar para que termine justo antes del siguiente
            midpoint = (results[i].end_time + results[i+1].start_time) / 2
            results[i].end_time = min(results[i+1].start_time, midpoint)
            if results[i].end_time - results[i].start_time < 0.25:
                results[i].end_time = results[i].start_time + 0.25
    return results


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
