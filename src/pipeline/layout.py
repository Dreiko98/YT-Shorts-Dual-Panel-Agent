"""
Sistema de layouts para composición dual-panel.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass
import tempfile

try:
    from moviepy.editor import VideoFileClip, CompositeVideoClip, ColorClip, TextClip
    from moviepy.video.fx import resize, loop
    from moviepy.video.tools.drawing import color_gradient
except ImportError:
    VideoFileClip = CompositeVideoClip = ColorClip = TextClip = None
    resize = loop = color_gradient = None

from ..utils.ffmpeg import get_video_info, FFmpegError

logger = logging.getLogger(__name__)


class LayoutError(Exception):
    """Error específico de layout."""
    pass


@dataclass
class PanelConfig:
    """Configuración de un panel."""
    x: int
    y: int
    width: int
    height: int
    has_audio: bool = False
    border_width: int = 0
    border_color: str = "#000000"
    
    @property
    def position(self) -> Tuple[int, int]:
        """Posición del panel."""
        return (self.x, self.y)
    
    @property
    def size(self) -> Tuple[int, int]:
        """Tamaño del panel."""
        return (self.width, self.height)


@dataclass
class LayoutConfig:
    """Configuración completa del layout."""
    name: str
    width: int
    height: int
    fps: int
    background_color: str
    panels: Dict[str, PanelConfig]
    subtitle_zone: Dict[str, int]  # x, y, width, height
    branding_zone: Optional[Dict[str, int]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutConfig':
        """Crear configuración desde diccionario."""
        panels = {}
        for name, panel_data in data.get("panels", {}).items():
            panels[name] = PanelConfig(**panel_data)
        
        return cls(
            name=data["name"],
            width=data["width"],
            height=data["height"],
            fps=data.get("fps", 30),
            background_color=data.get("background_color", "#000000"),
            panels=panels,
            subtitle_zone=data["subtitle_zone"],
            branding_zone=data.get("branding_zone")
        )


class DualPanelLayout:
    """Compositor de layouts dual-panel para YouTube Shorts."""
    
    def __init__(self, layout_config: LayoutConfig):
        """
        Inicializar compositor de layout.
        
        Args:
            layout_config: Configuración del layout
        """
        if VideoFileClip is None:
            raise LayoutError("MoviePy no está instalado")
        
        self.config = layout_config
        self.temp_files = []  # Para limpieza
        
        logger.info(f"DualPanelLayout inicializado: {layout_config.name} ({layout_config.width}x{layout_config.height})")
    
    def create_dual_panel_video(self, 
                               podcast_clip_path: Path,
                               broll_clip_path: Path,
                               duration: float,
                               output_path: Path) -> Dict[str, Any]:
        """
        Crear video con layout dual-panel.
        
        Args:
            podcast_clip_path: Ruta al clip de podcast (con audio)
            broll_clip_path: Ruta al clip de B-roll (sin audio)
            duration: Duración del clip final en segundos
            output_path: Ruta de salida del video compuesto
            
        Returns:
            Información del video creado
        """
        if not podcast_clip_path.exists():
            raise LayoutError(f"Clip de podcast no encontrado: {podcast_clip_path}")
        
        if not broll_clip_path.exists():
            raise LayoutError(f"Clip de B-roll no encontrado: {broll_clip_path}")
        
        try:
            # Cargar clips
            logger.info("Cargando clips de video...")
            podcast_clip = VideoFileClip(str(podcast_clip_path))
            broll_clip = VideoFileClip(str(broll_clip_path))
            
            # Configurar paneles
            if "podcast" not in self.config.panels or "broll" not in self.config.panels:
                raise LayoutError("Layout debe tener paneles 'podcast' y 'broll'")
            
            podcast_panel = self.config.panels["podcast"]
            broll_panel = self.config.panels["broll"]
            
            # Preparar clip de podcast (panel superior con audio)
            podcast_resized = self._prepare_podcast_clip(
                podcast_clip, podcast_panel, duration
            )
            
            # Preparar clip de B-roll (panel inferior sin audio)
            broll_resized = self._prepare_broll_clip(
                broll_clip, broll_panel, duration
            )
            
            # Crear fondo
            background = self._create_background()
            
            # Componer video final
            logger.info("Componiendo video final...")
            final_clips = [background]
            
            # Añadir panels con posicionamiento
            final_clips.append(
                podcast_resized.set_position(podcast_panel.position)
            )
            final_clips.append(
                broll_resized.set_position(broll_panel.position)
            )
            
            # Añadir bordes si están configurados
            if podcast_panel.border_width > 0:
                border = self._create_panel_border(podcast_panel)
                if border:
                    final_clips.append(border)
            
            if broll_panel.border_width > 0:
                border = self._create_panel_border(broll_panel)
                if border:
                    final_clips.append(border)
            
            # Crear composición final
            final_video = CompositeVideoClip(
                final_clips,
                size=(self.config.width, self.config.height)
            ).set_duration(duration).set_fps(self.config.fps)
            
            # Renderizar
            logger.info(f"Renderizando video: {output_path}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            final_video.write_videofile(
                str(output_path),
                fps=self.config.fps,
                audio_codec='aac',
                video_codec='libx264',
                temp_audiofile_path=str(output_path.parent / "temp_audio.m4a"),
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            # Liberar recursos
            podcast_clip.close()
            broll_clip.close()
            final_video.close()
            
            # Obtener información del archivo generado
            try:
                output_info = get_video_info(output_path)
            except FFmpegError:
                output_info = {"duration": duration, "width": self.config.width, "height": self.config.height}
            
            return {
                "success": True,
                "output_path": str(output_path),
                "duration": duration,
                "width": self.config.width,
                "height": self.config.height,
                "fps": self.config.fps,
                "layout": self.config.name,
                "file_size": output_path.stat().st_size if output_path.exists() else 0
            }
            
        except Exception as e:
            logger.error(f"Error creando layout dual-panel: {e}")
            raise LayoutError(f"Error en composición: {e}")
        
        finally:
            # Limpiar archivos temporales
            self._cleanup_temp_files()
    
    def _prepare_podcast_clip(self, clip: VideoFileClip, 
                             panel: PanelConfig, duration: float) -> VideoFileClip:
        """Preparar clip de podcast para panel superior."""
        logger.info("Preparando clip de podcast...")
        
        # Recortar duración
        if clip.duration > duration:
            clip = clip.subclip(0, duration)
        elif clip.duration < duration:
            # Loop si es muy corto
            clip = loop(clip, duration=duration)
        
        # Redimensionar manteniendo proporción
        clip_resized = resize(clip, newsize=panel.size)
        
        # El audio se mantiene solo en el podcast
        return clip_resized
    
    def _prepare_broll_clip(self, clip: VideoFileClip,
                           panel: PanelConfig, duration: float) -> VideoFileClip:
        """Preparar clip de B-roll para panel inferior."""
        logger.info("Preparando clip de B-roll...")
        
        # Remover audio del B-roll
        clip = clip.without_audio()
        
        # Recortar o hacer loop según duración
        if clip.duration > duration:
            # Tomar segmento del medio si es muy largo
            start_time = max(0, (clip.duration - duration) / 2)
            clip = clip.subclip(start_time, start_time + duration)
        elif clip.duration < duration:
            # Loop si es muy corto
            clip = loop(clip, duration=duration)
        
        # Redimensionar manteniendo proporción
        clip_resized = resize(clip, newsize=panel.size)
        
        return clip_resized
    
    def _create_background(self) -> ColorClip:
        """Crear fondo del video."""
        background = ColorClip(
            size=(self.config.width, self.config.height),
            color=self.config.background_color
        )
        return background
    
    def _create_panel_border(self, panel: PanelConfig) -> Optional[ColorClip]:
        """Crear borde para un panel."""
        if panel.border_width <= 0:
            return None
        
        # Crear marco usando clips de color
        # Top border
        top_border = ColorClip(
            size=(panel.width + 2 * panel.border_width, panel.border_width),
            color=panel.border_color
        ).set_position((
            panel.x - panel.border_width,
            panel.y - panel.border_width
        ))
        
        return top_border  # Simplificado por ahora
    
    def get_subtitle_zone(self) -> Dict[str, int]:
        """Obtener zona segura para subtítulos."""
        return self.config.subtitle_zone.copy()
    
    def get_branding_zone(self) -> Optional[Dict[str, int]]:
        """Obtener zona para branding si está definida."""
        if self.config.branding_zone:
            return self.config.branding_zone.copy()
        return None
    
    def _cleanup_temp_files(self):
        """Limpiar archivos temporales creados."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo temporal {temp_file}: {e}")
        
        self.temp_files.clear()


def load_layout_config(config_path: Path) -> LayoutConfig:
    """
    Cargar configuración de layout desde archivo YAML/JSON.
    
    Args:
        config_path: Ruta al archivo de configuración
        
    Returns:
        Configuración de layout cargada
    """
    if not config_path.exists():
        raise LayoutError(f"Archivo de configuración no encontrado: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                # Asumir YAML
                import yaml
                data = yaml.safe_load(f)
        
        return LayoutConfig.from_dict(data)
    
    except Exception as e:
        raise LayoutError(f"Error cargando configuración de layout: {e}")


def create_default_layout() -> LayoutConfig:
    """Crear configuración de layout por defecto para YouTube Shorts."""
    return LayoutConfig(
        name="default_dual_panel",
        width=1080,
        height=1920,
        fps=30,
        background_color="#000000",
        panels={
            "podcast": PanelConfig(
                x=0, y=0,
                width=1080, height=960,
                has_audio=True,
                border_width=0
            ),
            "broll": PanelConfig(
                x=0, y=960,
                width=1080, height=960,
                has_audio=False,
                border_width=0
            )
        },
        subtitle_zone={
            "x": 60,           # Margen lateral
            "y": 960,          # Exactamente en el centro (mitad de 1920px)
            "width": 960,      # Ancho generoso para texto
            "height": 160      # Altura suficiente para múltiples líneas
        },
        branding_zone={
            "x": 20,
            "y": 20,
            "width": 200,
            "height": 60
        }
    )


def validate_layout_config(config: LayoutConfig) -> List[str]:
    """
    Validar configuración de layout.
    
    Returns:
        Lista de errores encontrados (vacía si es válida)
    """
    errors = []
    
    # Validar dimensiones para YouTube Shorts
    if config.width != 1080 or config.height != 1920:
        errors.append(f"Dimensiones no son YouTube Shorts: {config.width}x{config.height} (esperado: 1080x1920)")
    
    # Validar FPS
    if config.fps not in [24, 30, 60]:
        errors.append(f"FPS no recomendado: {config.fps} (recomendado: 30)")
    
    # Validar paneles obligatorios
    required_panels = ["podcast", "broll"]
    for panel_name in required_panels:
        if panel_name not in config.panels:
            errors.append(f"Panel obligatorio faltante: {panel_name}")
    
    # Validar que los paneles caben en el canvas
    for name, panel in config.panels.items():
        if panel.x + panel.width > config.width:
            errors.append(f"Panel '{name}' se sale del ancho del canvas")
        if panel.y + panel.height > config.height:
            errors.append(f"Panel '{name}' se sale de la altura del canvas")
    
    # Validar zona de subtítulos
    subtitle_zone = config.subtitle_zone
    if (subtitle_zone["x"] + subtitle_zone["width"] > config.width or
        subtitle_zone["y"] + subtitle_zone["height"] > config.height):
        errors.append("Zona de subtítulos se sale del canvas")
    
    return errors
