"""
Editor principal para composición de YouTube Shorts.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import tempfile

from .layout import DualPanelLayout, LayoutConfig, create_default_layout, validate_layout_config
from .subtitles import BurnedSubtitleRenderer, SubtitleStyle, create_subtitles_from_transcript
from .segmenter import ClipCandidate
from ..utils.video import (
    extract_video_segment, create_video_loop, remove_audio_track,
    compose_dual_panel_ffmpeg, validate_video_for_shorts
)
from ..utils.ffmpeg import get_video_info, FFmpegError

logger = logging.getLogger(__name__)


class CompositionError(Exception):
    """Error específico de composición."""
    pass


class ShortComposer:
    """Compositor principal de YouTube Shorts."""
    
    def __init__(self, layout_config: Optional[LayoutConfig] = None,
                 subtitle_style: Optional[SubtitleStyle] = None):
        """
        Inicializar compositor.
        
        Args:
            layout_config: Configuración de layout o None para usar por defecto
            subtitle_style: Estilo de subtítulos o None para usar por defecto
        """
        self.layout_config = layout_config or create_default_layout()
        self.subtitle_style = subtitle_style or SubtitleStyle()
        
        # Validar configuración de layout
        layout_errors = validate_layout_config(self.layout_config)
        if layout_errors:
            logger.warning(f"Layout config tiene advertencias: {layout_errors}")
        
        self.subtitle_renderer = BurnedSubtitleRenderer(self.subtitle_style)
        self.temp_files = []  # Para limpieza
        
        logger.info(f"ShortComposer inicializado con layout: {self.layout_config.name}")
    
    def compose_short_from_candidate(self,
                                   candidate: ClipCandidate,
                                   podcast_video_path: Path,
                                   broll_video_path: Path,
                                   transcript_data: Dict[str, Any],
                                   output_path: Path,
                                   include_subtitles: bool = True) -> Dict[str, Any]:
        """
        Componer Short desde un clip candidato.
        
        Args:
            candidate: Clip candidato con timing
            podcast_video_path: Video completo del podcast
            broll_video_path: Video de B-roll
            transcript_data: Datos de transcripción
            output_path: Ruta de salida del Short
            include_subtitles: Si incluir subtítulos quemados
            
        Returns:
            Información del Short creado
        """
        logger.info(f"Componiendo Short: {candidate.id} ({candidate.duration:.1f}s)")
        
        try:
            # 1. Extraer segmento de podcast
            podcast_segment_path = self._extract_podcast_segment(
                podcast_video_path, candidate, output_path.parent
            )
            
            # 2. Preparar B-roll (loop si es necesario)
            broll_segment_path = self._prepare_broll_segment(
                broll_video_path, candidate.duration, output_path.parent
            )
            
            # 3. Crear composición dual-panel
            composed_path = self._create_dual_panel_composition(
                podcast_segment_path, broll_segment_path,
                candidate.duration, output_path.parent
            )
            
            # 4. Añadir subtítulos si se solicita
            if include_subtitles:
                logger.info(f"🔥 DEBUG: Añadiendo subtítulos al candidato {candidate.id}")
                final_path = self._add_subtitles_to_composition(
                    composed_path, candidate, transcript_data, output_path
                )
                logger.info(f"🔥 DEBUG: Subtítulos procesados, archivo final: {final_path}")
            else:
                logger.info(f"🔥 DEBUG: Subtítulos DESHABILITADOS para candidato {candidate.id}")
                # Simplemente mover archivo compuesto al destino final
                composed_path.rename(output_path)
                final_path = output_path
            
            # 5. Validar resultado
            validation = validate_video_for_shorts(final_path)
            
            # 6. Obtener información final
            try:
                video_info = get_video_info(final_path)
            except FFmpegError:
                video_info = {}
            
            result = {
                "success": True,
                "output_path": str(final_path),
                "candidate_id": candidate.id,
                "duration": candidate.duration,
                "has_subtitles": include_subtitles,
                "validation": validation,
                "video_info": video_info,
                "file_size": final_path.stat().st_size if final_path.exists() else 0
            }
            
            logger.info(f"Short compuesto exitosamente: {final_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error componiendo Short: {e}")
            raise CompositionError(f"Error en composición: {e}")
        
        finally:
            self._cleanup_temp_files()
    
    def compose_multiple_shorts(self,
                              candidates: List[ClipCandidate],
                              podcast_video_path: Path,
                              broll_video_path: Path,
                              transcript_data: Dict[str, Any],
                              output_dir: Path,
                              max_shorts: Optional[int] = None,
                              include_subtitles: bool = True) -> List[Dict[str, Any]]:
        """
        Componer múltiples Shorts desde lista de candidatos.
        
        Args:
            candidates: Lista de clips candidatos
            podcast_video_path: Video completo del podcast
            broll_video_path: Video de B-roll
            transcript_data: Datos de transcripción
            output_dir: Directorio de salida
            max_shorts: Máximo número de Shorts a crear
            include_subtitles: Si incluir subtítulos
            
        Returns:
            Lista de resultados de composición
        """
        if max_shorts:
            candidates = candidates[:max_shorts]
        
        results = []
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, candidate in enumerate(candidates, 1):
            logger.info(f"Procesando Short {i}/{len(candidates)}")
            
            # Generar nombre de archivo único
            output_filename = f"short_{candidate.id}_{int(candidate.duration)}s.mp4"
            output_path = output_dir / output_filename
            
            try:
                result = self.compose_short_from_candidate(
                    candidate, podcast_video_path, broll_video_path,
                    transcript_data, output_path, include_subtitles
                )
                results.append(result)
                
            except CompositionError as e:
                logger.error(f"Error procesando candidato {candidate.id}: {e}")
                results.append({
                    "success": False,
                    "candidate_id": candidate.id,
                    "error": str(e)
                })
        
        return results
    
    def _extract_podcast_segment(self, podcast_video_path: Path,
                                candidate: ClipCandidate,
                                temp_dir: Path) -> Path:
        """Extraer segmento de podcast basado en candidato."""
        segment_path = temp_dir / f"podcast_segment_{candidate.id}.mp4"
        self.temp_files.append(segment_path)
        
        success = extract_video_segment(
            podcast_video_path, segment_path,
            candidate.start_time, candidate.duration
        )
        
        if not success or not segment_path.exists():
            raise CompositionError("Error extrayendo segmento de podcast")
        
        return segment_path
    
    def _prepare_broll_segment(self, broll_video_path: Path,
                              target_duration: float,
                              temp_dir: Path) -> Path:
        """Preparar segmento de B-roll con duración objetivo y velocidad x1.75."""
        segment_path = temp_dir / f"broll_segment_{int(target_duration*1000)}.mp4"
        self.temp_files.append(segment_path)
        
        # Obtener información del B-roll
        try:
            broll_info = get_video_info(broll_video_path)
            broll_duration = broll_info.get("duration", 0)
        except FFmpegError:
            raise CompositionError("Error analizando video de B-roll")
        
        # Calcular duración necesaria para acelerar a x1.75
        # Si necesitamos 40s a velocidad normal, necesitamos 40*1.75 = 70s de material original
        speed_factor = 1.75
        required_duration = target_duration * speed_factor
        
        if broll_duration >= required_duration:
            # B-roll es suficientemente largo, extraer segmento
            success = extract_video_segment(
                broll_video_path, segment_path,
                0, required_duration
            )
        else:
            # B-roll es corto, crear loop
            success = create_video_loop(
                broll_video_path, segment_path, required_duration
            )
        
        if not success or not segment_path.exists():
            raise CompositionError("Error preparando segmento de B-roll")
        
        # Acelerar el video a x1.75 y remover audio
        broll_sped_path = temp_dir / f"broll_sped_{int(target_duration*1000)}.mp4"
        self.temp_files.append(broll_sped_path)
        
        success = self._speed_up_video(segment_path, broll_sped_path, speed_factor)
        if not success:
            raise CompositionError("Error acelerando B-roll")
        
        return broll_sped_path
    
    def _speed_up_video(self, input_path: Path, output_path: Path, speed_factor: float) -> bool:
        """Acelerar video usando ffmpeg."""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-vf", f"setpts={1/speed_factor}*PTS",
                "-an",  # Remover audio
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                logger.error(f"Error acelerando video: {result.stderr}")
                return False
                
            return output_path.exists()
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout acelerando video")
            return False
        except Exception as e:
            logger.error(f"Error acelerando video: {e}")
            return False
    
    def _create_dual_panel_composition(self, podcast_path: Path,
                                     broll_path: Path,
                                     duration: float,
                                     temp_dir: Path) -> Path:
        """Crear composición dual-panel."""
        composed_path = temp_dir / f"composed_{int(duration*1000)}.mp4"
        self.temp_files.append(composed_path)
        
        # Usar ffmpeg directo para mejor rendimiento
        success = compose_dual_panel_ffmpeg(
            podcast_path, broll_path, composed_path, duration,
            self.layout_config.width, self.layout_config.height
        )
        
        if not success or not composed_path.exists():
            raise CompositionError("Error creando composición dual-panel")
        
        return composed_path
    
    def _add_subtitles_to_composition(self, video_path: Path,
                                    candidate: ClipCandidate,
                                    transcript_data: Dict[str, Any],
                                    output_path: Path) -> Path:
        """Añadir subtítulos quemados a la composición."""
        logger.info(f"🎬 DEBUG: Iniciando proceso de subtítulos para {candidate.id}")
        
        # Filtrar segmentos de transcripción relevantes
        relevant_segments = self._filter_transcript_segments(
            transcript_data, candidate.start_time, candidate.end_time
        )
        
        logger.info(f"📝 DEBUG: Segmentos relevantes encontrados: {len(relevant_segments)}")
        
        if not relevant_segments:
            logger.warning(f"No hay segmentos de transcripción para candidato {candidate.id}")
            # Copiar sin subtítulos
            video_path.rename(output_path)
            return output_path
        
        # Crear subtítulos desde segmentos filtrados
        subtitle_data = {
            "segments": relevant_segments
        }
        
        subtitles = create_subtitles_from_transcript(subtitle_data)
        logger.info(f"🔤 DEBUG: Subtítulos creados desde transcripción: {len(subtitles)}")
        
        if not subtitles:
            logger.warning("No se pudieron crear subtítulos")
            video_path.rename(output_path)
            return output_path
        
        # Ajustar timing de subtítulos al clip
        adjusted_subtitles = []
        tolerance = 0.1  # Tolerancia de 100ms para problemas de precisión
        
        for subtitle in subtitles:
            # Restar el tiempo de inicio del candidato
            adjusted_start = subtitle.start_time - candidate.start_time
            adjusted_end = subtitle.end_time - candidate.start_time
            
            # Aplicar tolerancia para problemas de precisión
            if adjusted_start < -tolerance:
                continue  # Subtítulo está muy antes del clip
            
            # Ajustar inicio negativo pequeño a 0
            if adjusted_start < 0:
                adjusted_start = 0.0
            
            # Solo incluir subtítulos que estén dentro del rango
            if adjusted_start < candidate.duration:
                adjusted_end = min(adjusted_end, candidate.duration)
                
                if adjusted_end > adjusted_start:
                    subtitle.start_time = adjusted_start
                    subtitle.end_time = adjusted_end
                    adjusted_subtitles.append(subtitle)
        
        logger.info(f"⏱️ DEBUG: Subtítulos ajustados: {len(adjusted_subtitles)}")
        for i, sub in enumerate(adjusted_subtitles[:3]):
            logger.info(f"   {i+1}: {sub.start_time:.1f}s-{sub.end_time:.1f}s: {sub.text[:30]}...")
        
        # Renderizar subtítulos
        safe_zone = self.layout_config.subtitle_zone
        logger.info(f"🎯 DEBUG: Safe zone: {safe_zone}")
        logger.info(f"🎬 DEBUG: Renderizando subtítulos: {video_path} -> {output_path}")
        
        success = self.subtitle_renderer.add_subtitles_to_video(
            video_path, adjusted_subtitles, output_path, safe_zone
        )
        
        logger.info(f"✅ DEBUG: Renderizado de subtítulos: {'EXITOSO' if success else 'FALLÓ'}")
        
        if not success:
            logger.warning("Error añadiendo subtítulos, usando video sin subtítulos")
            video_path.rename(output_path)
        
        return output_path
    
    def _filter_transcript_segments(self, transcript_data: Dict[str, Any],
                                  start_time: float, end_time: float) -> List[Dict[str, Any]]:
        """Filtrar segmentos de transcripción por rango de tiempo."""
        segments = transcript_data.get("segments", [])
        filtered = []
        
        for segment in segments:
            segment_start = segment.get("start", 0)
            segment_end = segment.get("end", 0)
            
            # Verificar si hay solapamiento
            if (segment_start < end_time and segment_end > start_time):
                filtered.append(segment)
        
        return filtered
    
    def _cleanup_temp_files(self):
        """Limpiar archivos temporales."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Archivo temporal eliminado: {temp_file}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar {temp_file}: {e}")
        
        self.temp_files.clear()
    
    def create_composition_preview(self, candidates: List[ClipCandidate],
                                 output_path: Path) -> bool:
        """
        Crear preview de texto con información de composición.
        
        Args:
            candidates: Lista de candidatos
            output_path: Archivo de preview
            
        Returns:
            True si fue exitoso
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("Preview de Composición de Shorts\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"Layout: {self.layout_config.name}\n")
                f.write(f"Dimensiones: {self.layout_config.width}x{self.layout_config.height}\n")
                f.write(f"FPS: {self.layout_config.fps}\n\n")
                
                f.write(f"Total candidatos: {len(candidates)}\n\n")
                
                for i, candidate in enumerate(candidates, 1):
                    f.write(f"[{i:02d}] Short ID: {candidate.id}\n")
                    f.write(f"     Duración: {candidate.formatted_duration}\n")
                    f.write(f"     Score: {candidate.score:.1f}\n")
                    f.write(f"     Tiempo: {candidate.start_time:.1f}s - {candidate.end_time:.1f}s\n")
                    f.write(f"     Texto: {candidate.text[:100]}...\n")
                    f.write(f"     Keywords: {', '.join(candidate.keywords[:5])}\n\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creando preview: {e}")
            return False


def compose_short_from_files(podcast_video: Path, broll_video: Path,
                           transcript_json: Path, candidates_json: Path,
                           output_dir: Path,
                           max_shorts: int = 3,
                           layout_config: Optional[LayoutConfig] = None) -> List[Dict[str, Any]]:
    """
    Función helper para componer Shorts desde archivos.
    
    Args:
        podcast_video: Video del podcast
        broll_video: Video de B-roll
        transcript_json: Archivo JSON con transcripción
        candidates_json: Archivo JSON con candidatos
        output_dir: Directorio de salida
        max_shorts: Máximo Shorts a crear
        layout_config: Configuración de layout opcional
        
    Returns:
        Lista de resultados de composición
    """
    # Cargar datos
    with open(transcript_json, 'r', encoding='utf-8') as f:
        transcript_data = json.load(f)
    
    with open(candidates_json, 'r', encoding='utf-8') as f:
        candidates_data = json.load(f)
    
    # Convertir candidatos desde JSON
    candidates = []
    for candidate_dict in candidates_data.get("candidates", []):
        candidate = ClipCandidate(
            id=candidate_dict["id"],
            start_time=candidate_dict["start_time"],
            end_time=candidate_dict["end_time"],
            duration=candidate_dict["duration"],
            text=candidate_dict["text"],
            keywords=candidate_dict["keywords"],
            score=candidate_dict["score"],
            metadata=candidate_dict.get("metadata", {})
        )
        candidates.append(candidate)
    
    # Crear compositor
    composer = ShortComposer(layout_config)
    
    # Componer Shorts (con subtítulos habilitados)
    return composer.compose_multiple_shorts(
        candidates, podcast_video, broll_video,
        transcript_data, output_dir, max_shorts,
        include_subtitles=True
    )
