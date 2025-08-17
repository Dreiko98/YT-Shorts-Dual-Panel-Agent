"""
Tests para transcripción y segmentación.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.pipeline.transcribe import WhisperTranscriber, TranscriptionError, get_available_whisper_models
from src.pipeline.segmenter import TranscriptSegmenter, ClipCandidate, SegmentationError


class TestTranscription:
    """Tests para el módulo de transcripción."""
    
    def test_whisper_not_installed(self):
        """Test cuando Whisper no está instalado."""
        with patch('src.pipeline.transcribe.whisper', None):
            with pytest.raises(TranscriptionError, match="Whisper no está instalado"):
                WhisperTranscriber()
    
    def test_device_selection(self):
        """Test selección automática de dispositivo."""
        with patch('src.pipeline.transcribe.whisper', MagicMock()):
            with patch('src.pipeline.transcribe.torch', MagicMock()) as mock_torch:
                # Test CUDA disponible
                mock_torch.cuda.is_available.return_value = True
                transcriber = WhisperTranscriber(device="auto")
                assert transcriber.device == "cuda"
                
                # Test solo CPU
                mock_torch.cuda.is_available.return_value = False
                transcriber = WhisperTranscriber(device="auto")
                assert transcriber.device == "cpu"
                
                # Test dispositivo específico
                transcriber = WhisperTranscriber(device="cpu")
                assert transcriber.device == "cpu"
    
    def test_get_available_models(self):
        """Test obtener modelos disponibles."""
        with patch('src.pipeline.transcribe.whisper', MagicMock()):
            models = get_available_whisper_models()
            expected = ["tiny", "base", "small", "medium", "large"]
            assert models == expected
        
        with patch('src.pipeline.transcribe.whisper', None):
            models = get_available_whisper_models()
            assert models == []
    
    def create_mock_transcript_data(self):
        """Crear datos de transcripción mock."""
        return {
            "video_path": "/test/video.mp4",
            "model": "base", 
            "language": "es",
            "task": "transcribe",
            "duration": 120,
            "text": "Hola mundo. Esta es una prueba de transcripción.",
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Hola mundo.",
                    "words": [
                        {"word": "Hola", "start": 0.0, "end": 1.0, "probability": 0.95},
                        {"word": "mundo", "start": 1.5, "end": 2.5, "probability": 0.92}
                    ]
                },
                {
                    "id": 1,
                    "start": 5.5,
                    "end": 12.0,
                    "text": "Esta es una prueba de transcripción.",
                    "words": []
                }
            ],
            "quality_metrics": {
                "quality_score": 85.0,
                "words_per_minute": 120
            }
        }


class TestSegmentation:
    """Tests para el módulo de segmentación."""
    
    def test_transcript_segmenter_init(self):
        """Test inicialización del segmentador."""
        config = {
            "min_clip_duration": 10,
            "max_clip_duration": 60,
            "important_keywords": ["test", "demo"]
        }
        
        segmenter = TranscriptSegmenter(config)
        assert segmenter.min_duration == 10
        assert segmenter.max_duration == 60
        assert "test" in segmenter.important_keywords
    
    def test_clip_candidate_creation(self):
        """Test creación de candidatos."""
        candidate = ClipCandidate(
            id="test_1",
            start_time=10.0,
            end_time=25.0,
            duration=15.0,
            text="Esta es una prueba",
            keywords=["prueba"],
            score=75.5,
            metadata={"strategy": "test"}
        )
        
        assert candidate.id == "test_1"
        assert candidate.duration == 15.0
        assert candidate.formatted_duration == "00:15"
        assert "prueba" in candidate.keywords
    
    def test_sentence_boundary_detection(self):
        """Test detección de límites de oración."""
        config = {"min_clip_duration": 5, "max_clip_duration": 60}
        segmenter = TranscriptSegmenter(config)
        
        assert segmenter._is_sentence_boundary("Hola mundo.")
        assert segmenter._is_sentence_boundary("¿Cómo estás?")
        assert segmenter._is_sentence_boundary("¡Excelente!")
        assert not segmenter._is_sentence_boundary("Hola mundo")
        assert not segmenter._is_sentence_boundary("pero además")
    
    def test_complete_thought_detection(self):
        """Test detección de pensamientos completos."""
        config = {"min_clip_duration": 5, "max_clip_duration": 60}
        segmenter = TranscriptSegmenter(config)
        
        # Pensamiento completo válido
        assert segmenter._is_complete_thought("Esta es una oración completa y válida.")
        
        # Muy corto
        assert not segmenter._is_complete_thought("Sí.")
        
        # Sin terminación
        assert not segmenter._is_complete_thought("Esta oración no termina bien")
        
        # Empieza con conjunción colgante
        assert not segmenter._is_complete_thought("And this is not complete.")
    
    def test_overlap_calculation(self):
        """Test cálculo de solapamiento."""
        config = {"min_clip_duration": 5, "max_clip_duration": 60}
        segmenter = TranscriptSegmenter(config)
        
        clip1 = ClipCandidate("1", 10.0, 20.0, 10.0, "test1", [], 50.0, {})
        clip2 = ClipCandidate("2", 15.0, 25.0, 10.0, "test2", [], 60.0, {})
        clip3 = ClipCandidate("3", 30.0, 40.0, 10.0, "test3", [], 70.0, {})
        
        # Solapamiento parcial
        overlap = segmenter._calculate_overlap(clip1, clip2)
        assert 0.3 < overlap < 0.4  # Aproximadamente 1/3
        
        # Sin solapamiento
        overlap = segmenter._calculate_overlap(clip1, clip3)
        assert overlap == 0.0
    
    def test_candidate_filtering(self):
        """Test filtrado de candidatos solapados."""
        config = {
            "min_clip_duration": 5,
            "max_clip_duration": 60,
            "overlap_threshold": 0.3
        }
        segmenter = TranscriptSegmenter(config)
        
        candidates = [
            ClipCandidate("1", 10.0, 20.0, 10.0, "test1", [], 90.0, {}),  # Mejor puntuación
            ClipCandidate("2", 15.0, 25.0, 10.0, "test2", [], 80.0, {}),  # Solapa con 1
            ClipCandidate("3", 30.0, 40.0, 10.0, "test3", [], 70.0, {}),  # Sin solape
        ]
        
        filtered = segmenter._filter_overlapping_candidates(candidates)
        
        # Debe mantener el mejor de los solapados y el independiente
        assert len(filtered) == 2
        assert filtered[0].id == "1"  # Mejor puntuación
        assert filtered[1].id == "3"  # Sin solapamiento
    
    def test_context_expansion(self):
        """Test expansión de contexto."""
        config = {"min_clip_duration": 5, "max_clip_duration": 60}
        segmenter = TranscriptSegmenter(config)
        
        segments = [
            {"start": 0.0, "end": 5.0, "text": "Segmento 1"},
            {"start": 5.0, "end": 10.0, "text": "Segmento 2"},
            {"start": 10.0, "end": 15.0, "text": "Segmento 3"},
            {"start": 15.0, "end": 20.0, "text": "Segmento 4"},
            {"start": 20.0, "end": 25.0, "text": "Segmento 5"},
        ]
        
        # Expandir desde el centro
        context = segmenter._expand_context(segments, 2, 20.0)  # 20 segundos target
        
        # Debería incluir varios segmentos
        assert len(context) > 1
        assert context[0]["text"] in [s["text"] for s in segments]
    
    def create_test_transcript_file(self, tmp_path):
        """Crear archivo de transcripción de prueba."""
        transcript_data = {
            "video_path": "/test/video.mp4",
            "language": "es",
            "duration": 120,
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 8.0,
                    "text": "Hola mundo, esta es una prueba.",
                    "avg_logprob": -0.3,
                    "no_speech_prob": 0.1
                },
                {
                    "id": 1,
                    "start": 10.0,
                    "end": 20.0,
                    "text": "Estamos probando la segmentación automática de clips.",
                    "avg_logprob": -0.2,
                    "no_speech_prob": 0.05
                },
                {
                    "id": 2,
                    "start": 25.0,
                    "end": 35.0,
                    "text": "Este es otro segmento interesante con palabras clave importantes.",
                    "avg_logprob": -0.25,
                    "no_speech_prob": 0.08
                }
            ]
        }
        
        transcript_file = tmp_path / "test_transcript.json"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f)
        
        return transcript_file
    
    def test_segment_transcript_file(self, tmp_path):
        """Test segmentación de archivo real."""
        transcript_file = self.create_test_transcript_file(tmp_path)
        
        config = {
            "min_clip_duration": 5,
            "max_clip_duration": 30,
            "target_clip_duration": 15,
            "overlap_threshold": 0.2,
            "important_keywords": ["prueba", "segmentación"]
        }
        
        segmenter = TranscriptSegmenter(config)
        candidates = segmenter.segment_transcript(transcript_file)
        
        # Debe generar algunos candidatos
        assert len(candidates) > 0
        
        # Verificar que los candidatos tienen estructura correcta
        for candidate in candidates:
            assert isinstance(candidate, ClipCandidate)
            assert candidate.duration >= config["min_clip_duration"]
            assert candidate.duration <= config["max_clip_duration"]
            assert candidate.score > 0
            assert len(candidate.text) > 0
    
    def test_export_candidates(self, tmp_path):
        """Test exportación de candidatos."""
        config = {"min_clip_duration": 5, "max_clip_duration": 60}
        segmenter = TranscriptSegmenter(config)
        
        candidates = [
            ClipCandidate("test_1", 10.0, 25.0, 15.0, "Test clip", ["test"], 75.5, {"strategy": "test"}),
            ClipCandidate("test_2", 30.0, 45.0, 15.0, "Another clip", ["clip"], 65.2, {"strategy": "keyword"})
        ]
        
        output_file = tmp_path / "candidates.json"
        segmenter.export_candidates(candidates, output_file)
        
        # Verificar que se creó el archivo
        assert output_file.exists()
        
        # Verificar contenido
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["total_candidates"] == 2
        assert len(data["candidates"]) == 2
        assert data["candidates"][0]["id"] == "test_1"
        assert data["candidates"][0]["score"] == 75.5
    
    def test_missing_transcript_file(self):
        """Test error cuando no existe el archivo."""
        config = {"min_clip_duration": 5, "max_clip_duration": 60}
        segmenter = TranscriptSegmenter(config)
        
        fake_path = Path("/nonexistent/transcript.json")
        with pytest.raises(SegmentationError, match="no encontrado"):
            segmenter.segment_transcript(fake_path)


if __name__ == "__main__":
    pytest.main([__file__])
