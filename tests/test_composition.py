"""
Tests para composición, layout y subtítulos.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.pipeline.layout import (
    DualPanelLayout, LayoutConfig, PanelConfig, create_default_layout,
    validate_layout_config, LayoutError
)
from src.pipeline.subtitles import (
    BurnedSubtitleRenderer, SubtitleStyle, SubtitleSegment,
    create_subtitles_from_transcript, validate_subtitle_timing,
    SubtitleError
)
from src.pipeline.editor import ShortComposer, CompositionError, compose_short_from_files
from src.pipeline.segmenter import ClipCandidate


class TestLayoutSystem:
    """Tests para el sistema de layout."""
    
    def test_panel_config_creation(self):
        """Test creación de configuración de panel."""
        panel = PanelConfig(
            x=100, y=200, width=800, height=600,
            has_audio=True, border_width=2
        )
        
        assert panel.position == (100, 200)
        assert panel.size == (800, 600)
        assert panel.has_audio == True
        assert panel.border_width == 2
    
    def test_layout_config_from_dict(self):
        """Test crear configuración de layout desde dict."""
        data = {
            "name": "test_layout",
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "background_color": "#000000",
            "panels": {
                "podcast": {
                    "x": 0, "y": 0, "width": 1080, "height": 960,
                    "has_audio": True
                }
            },
            "subtitle_zone": {"x": 50, "y": 800, "width": 980, "height": 120}
        }
        
        config = LayoutConfig.from_dict(data)
        
        assert config.name == "test_layout"
        assert config.width == 1080
        assert config.height == 1920
        assert "podcast" in config.panels
        assert config.panels["podcast"].has_audio == True
    
    def test_default_layout_creation(self):
        """Test creación de layout por defecto."""
        layout = create_default_layout()
        
        assert layout.name == "default_dual_panel"
        assert layout.width == 1080
        assert layout.height == 1920
        assert "podcast" in layout.panels
        assert "broll" in layout.panels
        assert layout.panels["podcast"].has_audio == True
        assert layout.panels["broll"].has_audio == False
    
    def test_layout_validation(self):
        """Test validación de configuración de layout."""
        # Layout válido
        valid_layout = create_default_layout()
        errors = validate_layout_config(valid_layout)
        assert len(errors) == 0
        
        # Layout con dimensiones incorrectas
        invalid_layout = create_default_layout()
        invalid_layout.width = 1920
        invalid_layout.height = 1080
        errors = validate_layout_config(invalid_layout)
        assert len(errors) > 0
        assert any("Dimensiones no son YouTube Shorts" in error for error in errors)
    
    def test_dual_panel_layout_init(self):
        """Test inicialización de DualPanelLayout."""
        layout_config = create_default_layout()
        
        with patch('src.pipeline.layout.VideoFileClip', MagicMock()):
            layout = DualPanelLayout(layout_config)
            assert layout.config == layout_config
    
    def test_dual_panel_layout_moviepy_not_installed(self):
        """Test error cuando MoviePy no está instalado."""
        layout_config = create_default_layout()
        
        with patch('src.pipeline.layout.VideoFileClip', None):
            with pytest.raises(LayoutError, match="MoviePy no está instalado"):
                DualPanelLayout(layout_config)


class TestSubtitleSystem:
    """Tests para el sistema de subtítulos."""
    
    def test_subtitle_style_creation(self):
        """Test creación de estilo de subtítulos."""
        style = SubtitleStyle(
            font_family="Arial",
            font_size=48,
            font_color="#FFFFFF",
            outline_width=2
        )
        
        assert style.font_family == "Arial"
        assert style.font_size == 48
        assert style.outline_width == 2
    
    def test_subtitle_style_to_ffmpeg(self):
        """Test conversión de estilo a formato ffmpeg."""
        style = SubtitleStyle()
        ffmpeg_style = style.to_ffmpeg_style()
        
        assert "FontName=Arial" in ffmpeg_style
        assert "FontSize=48" in ffmpeg_style
        assert "Outline=2" in ffmpeg_style
    
    def test_subtitle_segment_creation(self):
        """Test creación de segmento de subtítulo."""
        segment = SubtitleSegment(
            start_time=10.5,
            end_time=15.3,
            text="Hola mundo"
        )
        
        assert abs(segment.duration - 4.8) < 0.01  # Usar tolerancia para float
        assert segment.text == "Hola mundo"
    
    def test_subtitle_segment_to_ass(self):
        """Test conversión de segmento a formato ASS."""
        segment = SubtitleSegment(10.0, 15.0, "Test subtitle")
        ass_event = segment.to_ass_event()
        
        assert "Dialogue:" in ass_event
        assert "Test subtitle" in ass_event
        assert "0:00:10.00" in ass_event
        assert "0:00:15.00" in ass_event
    
    def test_create_subtitles_from_transcript(self):
        """Test creación de subtítulos desde transcripción."""
        transcript_data = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Hola mundo"
                },
                {
                    "start": 5.5,
                    "end": 10.0,
                    "text": "Este es un test"
                }
            ]
        }
        
        subtitles = create_subtitles_from_transcript(transcript_data)
        
        assert len(subtitles) == 2
        assert subtitles[0].text == "Hola mundo"
        assert subtitles[1].text == "Este es un test"
        assert subtitles[0].start_time == 0.0
        assert subtitles[1].start_time == 5.5
    
    def test_subtitle_timing_validation(self):
        """Test validación de timing de subtítulos."""
        # Subtítulos válidos
        valid_subtitles = [
            SubtitleSegment(0.0, 2.0, "Test 1"),
            SubtitleSegment(2.5, 4.5, "Test 2")
        ]
        
        errors = validate_subtitle_timing(valid_subtitles)
        assert len(errors) == 0
        
        # Subtítulos con problemas
        invalid_subtitles = [
            SubtitleSegment(0.0, 0.2, "Muy corto"),  # Muy corto
            SubtitleSegment(2.0, 15.0, "Muy largo"),  # Muy largo
            SubtitleSegment(10.0, 8.0, "Timing inválido")  # Tiempo inválido
        ]
        
        errors = validate_subtitle_timing(invalid_subtitles)
        assert len(errors) >= 3
    
    def test_burned_subtitle_renderer_init(self):
        """Test inicialización del renderizador."""
        renderer = BurnedSubtitleRenderer()
        assert renderer.style is not None
        assert isinstance(renderer.style, SubtitleStyle)
        
        custom_style = SubtitleStyle(font_size=64)
        renderer_custom = BurnedSubtitleRenderer(custom_style)
        assert renderer_custom.style.font_size == 64


class TestCompositionSystem:
    """Tests para el sistema de composición."""
    
    def test_clip_candidate_creation(self):
        """Test creación de candidato para composición."""
        candidate = ClipCandidate(
            id="test_clip",
            start_time=10.0,
            end_time=25.0,
            duration=15.0,
            text="Test clip content",
            keywords=["test", "clip"],
            score=85.5,
            metadata={"strategy": "test"}
        )
        
        assert candidate.id == "test_clip"
        assert candidate.duration == 15.0
        assert candidate.formatted_duration == "00:15"
        assert "test" in candidate.keywords
    
    def test_short_composer_initialization(self):
        """Test inicialización del compositor."""
        composer = ShortComposer()
        
        assert composer.layout_config is not None
        assert composer.subtitle_style is not None
        assert composer.subtitle_renderer is not None
        assert composer.temp_files == []
    
    def test_short_composer_with_custom_config(self):
        """Test compositor con configuración personalizada."""
        custom_layout = create_default_layout()
        custom_layout.name = "custom_test"
        
        custom_style = SubtitleStyle(font_size=64)
        
        composer = ShortComposer(custom_layout, custom_style)
        
        assert composer.layout_config.name == "custom_test"
        assert composer.subtitle_style.font_size == 64
    
    def create_test_files(self, tmp_path):
        """Crear archivos de prueba para tests."""
        # Crear datos de transcripción
        transcript_data = {
            "segments": [
                {
                    "id": 0,
                    "start": 10.0,
                    "end": 20.0,
                    "text": "Test segment content"
                }
            ]
        }
        
        # Crear datos de candidatos
        candidates_data = {
            "candidates": [
                {
                    "id": "test_candidate",
                    "start_time": 10.0,
                    "end_time": 25.0,
                    "duration": 15.0,
                    "text": "Test candidate",
                    "keywords": ["test"],
                    "score": 80.0,
                    "metadata": {}
                }
            ]
        }
        
        # Escribir archivos
        transcript_file = tmp_path / "transcript.json"
        with open(transcript_file, 'w') as f:
            json.dump(transcript_data, f)
        
        candidates_file = tmp_path / "candidates.json"
        with open(candidates_file, 'w') as f:
            json.dump(candidates_data, f)
        
        return transcript_file, candidates_file
    
    def test_compose_short_from_files_missing_files(self, tmp_path):
        """Test error cuando faltan archivos."""
        nonexistent_file = tmp_path / "nonexistent.json"
        
        with pytest.raises(FileNotFoundError):
            compose_short_from_files(
                podcast_video=nonexistent_file,
                broll_video=nonexistent_file,
                transcript_json=nonexistent_file,
                candidates_json=nonexistent_file,
                output_dir=tmp_path / "output",
                max_shorts=1
            )
    
    def test_temp_file_cleanup(self):
        """Test limpieza de archivos temporales."""
        composer = ShortComposer()
        
        # Simular archivos temporales
        temp_files = [
            Path("/tmp/fake_file1.mp4"),
            Path("/tmp/fake_file2.mp4")
        ]
        
        composer.temp_files = temp_files
        
        # Limpiar (no debería dar error aunque los archivos no existan)
        composer._cleanup_temp_files()
        
        assert len(composer.temp_files) == 0
    
    def test_composition_preview_creation(self, tmp_path):
        """Test creación de preview de composición."""
        composer = ShortComposer()
        
        candidates = [
            ClipCandidate(
                "test1", 0.0, 15.0, 15.0, "Test clip 1", ["test"], 90.0, {}
            ),
            ClipCandidate(
                "test2", 20.0, 35.0, 15.0, "Test clip 2", ["example"], 85.0, {}
            )
        ]
        
        preview_path = tmp_path / "preview.txt"
        success = composer.create_composition_preview(candidates, preview_path)
        
        assert success
        assert preview_path.exists()
        
        content = preview_path.read_text(encoding='utf-8')
        assert "Preview de Composición" in content
        assert "test1" in content
        assert "test2" in content


if __name__ == "__main__":
    pytest.main([__file__])
