"""
Módulo de transcripción usando Whisper local.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile
import shutil

try:
    import whisper
    import torch
except ImportError:
    whisper = None
    torch = None

from ..utils.ffmpeg import extract_audio, get_video_info, FFmpegError
from ..utils.text import save_srt_file, validate_transcript_quality

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Error específico de transcripción."""
    pass


class WhisperTranscriber:
    """Transcriptor usando OpenAI Whisper."""
    
    def __init__(self, model_name: str = "base", device: str = "auto"):
        """
        Inicializar transcriptor.
        
        Args:
            model_name: Modelo de Whisper (tiny, base, small, medium, large)
            device: Dispositivo (auto, cpu, cuda)
        """
        if whisper is None:
            raise TranscriptionError("OpenAI Whisper no está instalado")
        
        self.model_name = model_name
        self.device = self._select_device(device)
        self.model = None
        
        logger.info(f"WhisperTranscriber inicializado: modelo={model_name}, device={self.device}")
    
    def _select_device(self, device: str) -> str:
        """Seleccionar dispositivo óptimo."""
        if device == "auto":
            if torch and torch.cuda.is_available():
                return "cuda"
            else:
                return "cpu"
        return device
    
    def _load_model(self):
        """Cargar modelo Whisper si no está cargado."""
        if self.model is None:
            try:
                logger.info(f"Cargando modelo Whisper: {self.model_name}")
                self.model = whisper.load_model(self.model_name, device=self.device)
                logger.info("Modelo Whisper cargado correctamente")
            except Exception as e:
                raise TranscriptionError(f"Error cargando modelo Whisper: {e}")
    
    def transcribe_video(self, video_path: Path, output_dir: Path, 
                        language: Optional[str] = None,
                        task: str = "transcribe") -> Dict[str, Any]:
        """
        Transcribir un archivo de video.
        
        Args:
            video_path: Ruta al archivo de video
            output_dir: Directorio donde guardar los archivos de salida
            language: Idioma forzado (es, en, etc.) o None para auto-detectar
            task: "transcribe" o "translate"
        
        Returns:
            Dict con información de la transcripción
        """
        if not video_path.exists():
            raise TranscriptionError(f"Archivo de video no encontrado: {video_path}")
        
        # Crear directorio de salida
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generar nombres de archivos de salida
        base_name = video_path.stem
        audio_temp_path = output_dir / f"{base_name}_temp_audio.wav"
        transcript_json_path = output_dir / f"{base_name}_transcript.json"
        transcript_srt_path = output_dir / f"{base_name}_transcript.srt"
        
        try:
            # 1. Extraer audio del video
            logger.info(f"Extrayendo audio de {video_path}")
            if not extract_audio(video_path, audio_temp_path):
                raise TranscriptionError("Error extrayendo audio del video")
            
            # 2. Obtener información del video original
            try:
                video_info = get_video_info(video_path)
            except FFmpegError as e:
                logger.warning(f"No se pudo obtener info del video: {e}")
                video_info = {"duration": 0}
            
            # 3. Cargar modelo Whisper
            self._load_model()
            
            # 4. Ejecutar transcripción
            logger.info(f"Iniciando transcripción con Whisper")
            
            transcribe_options = {
                "task": task,
                "verbose": False,
                "word_timestamps": True,  # Importante para segmentación
            }
            
            if language:
                transcribe_options["language"] = language
            
            result = self.model.transcribe(
                str(audio_temp_path),
                **transcribe_options
            )
            
            # 5. Procesar resultados
            transcript_data = {
                "video_path": str(video_path),
                "model": self.model_name,
                "language": result.get("language", "unknown"),
                "task": task,
                "duration": video_info.get("duration", 0),
                "text": result["text"].strip(),
                "segments": []
            }
            
            # Procesar segmentos con timestamps de palabras
            for segment in result.get("segments", []):
                segment_data = {
                    "id": segment.get("id", 0),
                    "seek": segment.get("seek", 0),
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "text": segment.get("text", "").strip(),
                    "tokens": segment.get("tokens", []),
                    "temperature": segment.get("temperature", 0),
                    "avg_logprob": segment.get("avg_logprob", 0),
                    "compression_ratio": segment.get("compression_ratio", 0),
                    "no_speech_prob": segment.get("no_speech_prob", 0),
                    "words": []
                }
                
                # Añadir timestamps de palabras si están disponibles
                for word in segment.get("words", []):
                    word_data = {
                        "word": word.get("word", ""),
                        "start": word.get("start", 0),
                        "end": word.get("end", 0),
                        "probability": word.get("probability", 0)
                    }
                    segment_data["words"].append(word_data)
                
                transcript_data["segments"].append(segment_data)
            
            # 6. Validar calidad de transcripción
            quality_metrics = validate_transcript_quality(transcript_data)
            transcript_data["quality_metrics"] = quality_metrics
            
            logger.info(
                f"Transcripción completada: {len(transcript_data['segments'])} segmentos, "
                f"calidad: {quality_metrics['quality_score']:.1f}/100"
            )
            
            # 7. Guardar archivos de salida
            # JSON con datos completos
            with open(transcript_json_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)
            
            # SRT para subtítulos
            srt_subtitles = []
            for segment in transcript_data["segments"]:
                if segment["text"].strip():
                    srt_subtitles.append({
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': segment['text'].strip()
                    })
            
            if srt_subtitles:
                save_srt_file(srt_subtitles, transcript_srt_path)
            
            # 8. Limpiar archivo temporal de audio
            if audio_temp_path.exists():
                audio_temp_path.unlink()
            
            return {
                "success": True,
                "transcript_json": transcript_json_path,
                "transcript_srt": transcript_srt_path,
                "language": transcript_data["language"],
                "duration": transcript_data["duration"],
                "segments_count": len(transcript_data["segments"]),
                "quality_score": quality_metrics["quality_score"],
                "words_per_minute": quality_metrics["words_per_minute"]
            }
            
        except Exception as e:
            # Limpiar archivos temporales en caso de error
            if audio_temp_path.exists():
                audio_temp_path.unlink()
            
            logger.error(f"Error en transcripción: {e}")
            raise TranscriptionError(f"Error transcribiendo {video_path}: {e}")
    
    def batch_transcribe(self, video_paths: List[Path], output_dir: Path,
                        **transcribe_options) -> List[Dict[str, Any]]:
        """Transcribir múltiples videos en lote."""
        results = []
        
        for i, video_path in enumerate(video_paths, 1):
            logger.info(f"Procesando video {i}/{len(video_paths)}: {video_path.name}")
            
            try:
                result = self.transcribe_video(video_path, output_dir, **transcribe_options)
                results.append(result)
            except TranscriptionError as e:
                logger.error(f"Error procesando {video_path}: {e}")
                results.append({
                    "success": False,
                    "video_path": str(video_path),
                    "error": str(e)
                })
        
        return results
    
    def cleanup(self):
        """Liberar recursos del modelo."""
        if self.model is not None:
            del self.model
            self.model = None
            
            # Limpiar memoria GPU si está disponible
            if torch and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("Modelo Whisper liberado")


def transcribe_video_file(video_path: Path, output_dir: Path,
                         model: str = "base", device: str = "auto",
                         language: Optional[str] = None) -> Dict[str, Any]:
    """
    Función helper para transcribir un solo video.
    
    Args:
        video_path: Ruta al video
        output_dir: Directorio de salida
        model: Modelo Whisper a usar
        device: Dispositivo (auto, cpu, cuda)
        language: Idioma forzado o None
    
    Returns:
        Resultado de transcripción
    """
    transcriber = WhisperTranscriber(model_name=model, device=device)
    
    try:
        return transcriber.transcribe_video(
            video_path, output_dir, language=language
        )
    finally:
        transcriber.cleanup()


def get_available_whisper_models() -> List[str]:
    """Obtener lista de modelos Whisper disponibles."""
    if whisper is None:
        return []
    
    return ["tiny", "base", "small", "medium", "large"]


def check_whisper_requirements() -> Dict[str, bool]:
    """Verificar que Whisper y dependencias estén disponibles."""
    checks = {
        "whisper_installed": whisper is not None,
        "torch_available": torch is not None,
        "cuda_available": torch is not None and torch.cuda.is_available(),
    }
    
    if whisper:
        try:
            # Test que podemos cargar un modelo pequeño
            test_model = whisper.load_model("tiny")
            checks["model_loading"] = True
            del test_model
        except Exception:
            checks["model_loading"] = False
    else:
        checks["model_loading"] = False
    
    return checks
