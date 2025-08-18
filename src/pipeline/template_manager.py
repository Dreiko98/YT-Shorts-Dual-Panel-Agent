"""
🎨 Sistema de Templates Dinámicos para Shorts
Gestiona diferentes estilos visuales y branding automático
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
from dataclasses import dataclass
import tempfile
import subprocess

# Añadir src al path
sys.path.append('src')

logger = logging.getLogger(__name__)

@dataclass
class TemplateConfig:
    """Configuración de un template"""
    name: str
    description: str
    subtitle_style: Dict
    branding: Dict
    video_effects: Dict
    audio_effects: Dict
    priority: int = 50
    enabled: bool = True

class TemplateManager:
    """Gestor de templates dinámicos para shorts"""
    
    def __init__(self, templates_config_path: str = "configs/templates.yaml"):
        self.templates_config_path = templates_config_path
        self.templates: Dict[str, TemplateConfig] = {}
        self.default_template = "clean_centered"
        
        # Crear configuración por defecto si no existe
        self._ensure_templates_config()
        self._load_templates()
    
    def _ensure_templates_config(self):
        """Crear archivo de configuración de templates si no existe"""
        
        config_path = Path(self.templates_config_path)
        config_path.parent.mkdir(exist_ok=True)
        
        if not config_path.exists():
            default_config = {
                'templates': {
                    'clean_centered': {
                        'name': 'Clean Centered',
                        'description': 'Subtítulos centrados limpios, sin decoraciones',
                        'subtitle_style': {
                            'font_family': 'Arial Bold',
                            'font_size': 48,
                            'font_color': 'white',
                            'outline_color': 'black',
                            'outline_width': 2,
                            'position': 'center',
                            'background': False,
                            'shadow': True,
                            'shadow_offset': [2, 2]
                        },
                        'branding': {
                            'watermark': False,
                            'logo_position': 'bottom_right',
                            'logo_size': 100,
                            'logo_opacity': 0.7
                        },
                        'video_effects': {
                            'transition': 'fade',
                            'zoom_effect': False,
                            'blur_background': False,
                            'color_grading': 'neutral'
                        },
                        'audio_effects': {
                            'normalize': True,
                            'compressor': True,
                            'noise_reduction': False,
                            'target_lufs': -18
                        },
                        'priority': 100,
                        'enabled': True
                    },
                    
                    'modern_highlighted': {
                        'name': 'Modern Highlighted',
                        'description': 'Subtítulos con fondo destacado y efectos modernos',
                        'subtitle_style': {
                            'font_family': 'Montserrat Bold',
                            'font_size': 52,
                            'font_color': 'white',
                            'outline_color': 'none',
                            'outline_width': 0,
                            'position': 'center',
                            'background': True,
                            'background_color': 'rgba(0,0,0,0.8)',
                            'background_padding': 20,
                            'shadow': False
                        },
                        'branding': {
                            'watermark': True,
                            'logo_position': 'bottom_right',
                            'logo_size': 120,
                            'logo_opacity': 0.8
                        },
                        'video_effects': {
                            'transition': 'slide',
                            'zoom_effect': True,
                            'blur_background': False,
                            'color_grading': 'vibrant'
                        },
                        'audio_effects': {
                            'normalize': True,
                            'compressor': True,
                            'noise_reduction': True,
                            'target_lufs': -16
                        },
                        'priority': 80,
                        'enabled': True
                    },
                    
                    'minimal_elegant': {
                        'name': 'Minimal Elegant',
                        'description': 'Estilo minimalista y elegante',
                        'subtitle_style': {
                            'font_family': 'Georgia',
                            'font_size': 44,
                            'font_color': '#f5f5f5',
                            'outline_color': 'none',
                            'outline_width': 0,
                            'position': 'lower_center',
                            'background': False,
                            'shadow': True,
                            'shadow_offset': [1, 1],
                            'shadow_color': 'rgba(0,0,0,0.6)'
                        },
                        'branding': {
                            'watermark': False,
                            'logo_position': 'top_left',
                            'logo_size': 80,
                            'logo_opacity': 0.5
                        },
                        'video_effects': {
                            'transition': 'crossfade',
                            'zoom_effect': False,
                            'blur_background': True,
                            'color_grading': 'cinematic'
                        },
                        'audio_effects': {
                            'normalize': True,
                            'compressor': False,
                            'noise_reduction': True,
                            'target_lufs': -20
                        },
                        'priority': 60,
                        'enabled': True
                    },
                    
                    'gaming_style': {
                        'name': 'Gaming Style',
                        'description': 'Estilo gaming con efectos llamativos',
                        'subtitle_style': {
                            'font_family': 'Impact',
                            'font_size': 56,
                            'font_color': '#00ff00',
                            'outline_color': 'black',
                            'outline_width': 3,
                            'position': 'center',
                            'background': True,
                            'background_color': 'rgba(0,0,0,0.9)',
                            'background_padding': 15,
                            'shadow': False,
                            'glow_effect': True,
                            'glow_color': '#00ff00'
                        },
                        'branding': {
                            'watermark': True,
                            'logo_position': 'top_center',
                            'logo_size': 150,
                            'logo_opacity': 1.0
                        },
                        'video_effects': {
                            'transition': 'zoom',
                            'zoom_effect': True,
                            'blur_background': False,
                            'color_grading': 'high_contrast'
                        },
                        'audio_effects': {
                            'normalize': True,
                            'compressor': True,
                            'noise_reduction': False,
                            'target_lufs': -14
                        },
                        'priority': 40,
                        'enabled': False  # Disabled by default
                    }
                },
                
                'channel_preferences': {
                    'default_template': 'clean_centered',
                    'fallback_template': 'minimal_elegant',
                    'auto_select_by_content': True,
                    'content_type_mapping': {
                        'tutorial': 'clean_centered',
                        'gaming': 'gaming_style',
                        'lifestyle': 'minimal_elegant',
                        'tech': 'modern_highlighted'
                    }
                },
                
                'global_settings': {
                    'template_rotation': False,
                    'quality_threshold_for_templates': 70,
                    'enable_a_b_testing': False
                }
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Configuración de templates creada en {config_path}")
    
    def _load_templates(self):
        """Cargar templates desde configuración"""
        
        try:
            with open(self.templates_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            templates_data = config.get('templates', {})
            
            for template_id, template_config in templates_data.items():
                self.templates[template_id] = TemplateConfig(
                    name=template_config['name'],
                    description=template_config['description'],
                    subtitle_style=template_config['subtitle_style'],
                    branding=template_config['branding'],
                    video_effects=template_config['video_effects'],
                    audio_effects=template_config['audio_effects'],
                    priority=template_config.get('priority', 50),
                    enabled=template_config.get('enabled', True)
                )
            
            logger.info(f"Cargados {len(self.templates)} templates")
            
        except Exception as e:
            logger.error(f"Error cargando templates: {e}")
            self.templates = {}
    
    def get_available_templates(self) -> Dict[str, TemplateConfig]:
        """Obtener templates disponibles (habilitados)"""
        return {k: v for k, v in self.templates.items() if v.enabled}
    
    def select_template_for_content(self, content_info: Dict) -> str:
        """Seleccionar template automáticamente basado en el contenido"""
        
        available = self.get_available_templates()
        if not available:
            return self.default_template
        
        # Estrategias de selección automática:
        
        # 1. Por tipo de contenido (si está configurado)
        content_type = self._detect_content_type(content_info)
        if content_type:
            with open(self.templates_config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            mapping = config.get('channel_preferences', {}).get('content_type_mapping', {})
            mapped_template = mapping.get(content_type)
            
            if mapped_template and mapped_template in available:
                logger.info(f"Template seleccionado por contenido '{content_type}': {mapped_template}")
                return mapped_template
        
        # 2. Por calidad del contenido (templates mejores para contenido de alta calidad)
        quality_score = content_info.get('quality_score', 50)
        if quality_score >= 80:
            # Contenido de alta calidad: usar templates premium
            premium_templates = ['modern_highlighted', 'minimal_elegant']
            for template in premium_templates:
                if template in available:
                    logger.info(f"Template premium seleccionado para contenido de alta calidad: {template}")
                    return template
        
        # 3. Por duración (templates diferentes para duraciones diferentes)
        duration = content_info.get('duration_seconds', 30)
        if duration <= 20:
            # Videos cortos: usar templates impactantes
            if 'modern_highlighted' in available:
                return 'modern_highlighted'
        elif duration >= 50:
            # Videos largos: usar templates menos invasivos
            if 'minimal_elegant' in available:
                return 'minimal_elegant'
        
        # 4. Fallback: template por defecto o el de mayor prioridad
        if self.default_template in available:
            return self.default_template
        
        # Seleccionar el de mayor prioridad
        if available:
            best_template = max(available.items(), key=lambda x: x[1].priority)
            return best_template[0]
        
        # Si no hay templates disponibles, usar default
        return self.default_template
    
    def _detect_content_type(self, content_info: Dict) -> Optional[str]:
        """Detectar tipo de contenido basado en título y descripción"""
        
        title = content_info.get('original_title', '').lower()
        description = content_info.get('description', '').lower()
        
        text = f"{title} {description}"
        
        # Palabras clave para categorización
        categories = {
            'tutorial': ['tutorial', 'how to', 'guide', 'learn', 'step by step', 'enseñar', 'aprender'],
            'gaming': ['game', 'gaming', 'play', 'gameplay', 'stream', 'juego', 'gamer'],
            'tech': ['tech', 'technology', 'programming', 'code', 'software', 'tecnología', 'programación'],
            'lifestyle': ['life', 'daily', 'vlog', 'personal', 'lifestyle', 'vida', 'diario']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return None
    
    def apply_template(self, video_path: str, template_id: str, output_path: str, 
                      subtitle_text: Optional[str] = None) -> bool:
        """Aplicar template a un video"""
        
        if template_id not in self.templates:
            logger.error(f"Template no encontrado: {template_id}")
            return False
        
        template = self.templates[template_id]
        
        try:
            # Construir comando ffmpeg basado en template
            ffmpeg_filters = self._build_ffmpeg_filters(template, subtitle_text)
            
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', ffmpeg_filters,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'medium',
                '-crf', '23',
                '-y',  # Sobrescribir
                output_path
            ]
            
            # Ejecutar ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Template '{template_id}' aplicado exitosamente")
                return True
            else:
                logger.error(f"Error aplicando template: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error aplicando template {template_id}: {e}")
            return False
    
    def _build_ffmpeg_filters(self, template: TemplateConfig, subtitle_text: Optional[str] = None) -> str:
        """Construir filtros ffmpeg basados en el template"""
        
        filters = []
        
        # Filtros de video básicos
        if template.video_effects.get('color_grading') == 'vibrant':
            filters.append("eq=contrast=1.2:saturation=1.3:brightness=0.1")
        elif template.video_effects.get('color_grading') == 'cinematic':
            filters.append("curves=darker")
        elif template.video_effects.get('color_grading') == 'high_contrast':
            filters.append("eq=contrast=1.5:saturation=1.1")
        
        # Efectos de zoom
        if template.video_effects.get('zoom_effect'):
            filters.append("scale=1200x2136,crop=1080:1920:60:108")  # Ligero zoom
        
        # Blur background (si se especifica)
        if template.video_effects.get('blur_background'):
            filters.append("boxblur=2:1")
        
        # Subtítulos (si se proporcionan)
        if subtitle_text:
            subtitle_filter = self._build_subtitle_filter(template.subtitle_style, subtitle_text)
            filters.append(subtitle_filter)
        
        # Combinar filtros
        return ','.join(filters) if filters else "null"
    
    def _build_subtitle_filter(self, style: Dict, text: str) -> str:
        """Construir filtro de subtítulos"""
        
        # Escapar texto para ffmpeg
        escaped_text = text.replace(":", "\\:").replace("'", "\\'")
        
        # Posición
        position = style.get('position', 'center')
        if position == 'center':
            x, y = '(w-text_w)/2', '(h-text_h)/2'
        elif position == 'lower_center':
            x, y = '(w-text_w)/2', 'h*0.8'
        elif position == 'upper_center':
            x, y = '(w-text_w)/2', 'h*0.2'
        else:
            x, y = '(w-text_w)/2', '(h-text_h)/2'  # fallback
        
        # Color
        color = style.get('font_color', 'white')
        if color.startswith('#'):
            color = color[1:]  # Remover #
        
        # Tamaño
        size = style.get('font_size', 48)
        
        # Construir filtro drawtext
        subtitle_filter = f"drawtext=text='{escaped_text}':x={x}:y={y}:fontsize={size}:fontcolor={color}"
        
        # Outline
        if style.get('outline_width', 0) > 0:
            outline_color = style.get('outline_color', 'black')
            outline_width = style.get('outline_width', 2)
            subtitle_filter += f":bordercolor={outline_color}:borderw={outline_width}"
        
        # Shadow
        if style.get('shadow'):
            shadow_offset = style.get('shadow_offset', (2, 2))
            subtitle_filter += f":shadowx={shadow_offset[0]}:shadowy={shadow_offset[1]}"
        
        return subtitle_filter
    
    def get_template_preview(self, template_id: str) -> Dict:
        """Obtener preview/información de un template"""
        
        if template_id not in self.templates:
            return {'error': 'Template no encontrado'}
        
        template = self.templates[template_id]
        
        return {
            'name': template.name,
            'description': template.description,
            'priority': template.priority,
            'enabled': template.enabled,
            'features': {
                'subtitle_background': template.subtitle_style.get('background', False),
                'watermark': template.branding.get('watermark', False),
                'video_effects': list(template.video_effects.keys()),
                'audio_normalization': template.audio_effects.get('normalize', False)
            },
            'style_preview': {
                'font_family': template.subtitle_style.get('font_family', 'Arial'),
                'font_size': template.subtitle_style.get('font_size', 48),
                'font_color': template.subtitle_style.get('font_color', 'white'),
                'position': template.subtitle_style.get('position', 'center')
            }
        }
    
    def list_templates_summary(self) -> List[Dict]:
        """Listar resumen de todos los templates"""
        
        return [
            {
                'id': template_id,
                'name': template.name,
                'description': template.description,
                'enabled': template.enabled,
                'priority': template.priority
            }
            for template_id, template in self.templates.items()
        ]

def demo_templates():
    """Demostración del sistema de templates"""
    
    print("🎨 Sistema de Templates Dinámicos - Demo")
    print("=" * 50)
    
    manager = TemplateManager()
    
    # Listar templates disponibles
    templates = manager.list_templates_summary()
    print(f"📋 Templates disponibles: {len(templates)}")
    
    for template in templates:
        status = "✅" if template['enabled'] else "❌"
        print(f"   {status} {template['id']}: {template['name']} (Prioridad: {template['priority']})")
    
    print()
    
    # Ejemplo de selección automática
    content_examples = [
        {
            'original_title': 'How to Code in Python - Complete Tutorial',
            'duration_seconds': 45,
            'quality_score': 85
        },
        {
            'original_title': 'Gaming Stream Highlights - Epic Moments',
            'duration_seconds': 30,
            'quality_score': 70
        },
        {
            'original_title': 'My Daily Life Vlog',
            'duration_seconds': 60,
            'quality_score': 60
        }
    ]
    
    print("🎯 Selección automática de templates:")
    for i, content in enumerate(content_examples, 1):
        selected = manager.select_template_for_content(content)
        print(f"   {i}. '{content['original_title'][:40]}...'")
        print(f"      → Template seleccionado: {selected}")
        
        preview = manager.get_template_preview(selected)
        print(f"      → Estilo: {preview['style_preview']['font_family']}, {preview['style_preview']['font_size']}px, {preview['style_preview']['font_color']}")
        print()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    demo_templates()
