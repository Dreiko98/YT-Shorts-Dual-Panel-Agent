"""
Segmentador inteligente usando OpenAI GPT para análisis de transcripciones.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import openai
from openai import OpenAI

from .segmenter import ClipCandidate, SegmentationError
from ..utils.text import clean_text

logger = logging.getLogger(__name__)


@dataclass
class AISegmentationConfig:
    """Configuración para segmentación con IA."""
    model: str = "gpt-4o"
    max_tokens: int = 4000
    temperature: float = 0.3
    max_clips: int = 5
    min_duration: float = 15.0
    max_duration: float = 59.0
    target_duration: float = 35.0
    content_types: List[str] = None
    
    def __post_init__(self):
        if self.content_types is None:
            self.content_types = [
                "tutorial", "consejo", "explicación", "anécdota", 
                "reflexión", "dato_interesante", "pregunta_respuesta"
            ]


class AITranscriptSegmenter:
    """Segmentador de transcripciones usando IA."""
    
    def __init__(self, config: Optional[AISegmentationConfig] = None):
        """
        Inicializar segmentador IA.
        
        Args:
            config: Configuración personalizada
        """
        self.config = config or AISegmentationConfig()
        
        # Configurar OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise SegmentationError("OPENAI_API_KEY no encontrada en variables de entorno")
        
        self.client = OpenAI(api_key=api_key)
        
        logger.info(f"AITranscriptSegmenter inicializado con modelo {self.config.model}")
    
    def segment_transcript(self, 
                          transcript_path: Path,
                          keywords_filter: Optional[List[str]] = None) -> List[ClipCandidate]:
        """
        Segmentar transcripción usando IA.
        
        Args:
            transcript_path: Ruta al archivo de transcripción JSON
            keywords_filter: Palabras clave opcionales para filtrar
            
        Returns:
            Lista de candidatos a clips
        """
        if not transcript_path.exists():
            raise SegmentationError(f"Archivo de transcripción no encontrado: {transcript_path}")
        
        # Cargar transcripción
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)
        except Exception as e:
            raise SegmentationError(f"Error cargando transcripción: {e}")
        
        segments = transcript_data.get("segments", [])
        if not segments:
            raise SegmentationError("No hay segmentos en la transcripción")
        
        logger.info(f"Procesando transcripción con {len(segments)} segmentos")
        
        # Preparar el texto para la IA
        full_text = self._prepare_transcript_for_ai(segments)
        
        # Obtener segmentación de la IA
        ai_response = self._get_ai_segmentation(full_text, keywords_filter)
        
        # Convertir respuesta de IA a candidatos
        candidates = self._convert_ai_response_to_candidates(ai_response, segments, transcript_data)
        
        logger.info(f"Generados {len(candidates)} clips candidatos con IA")
        
        return candidates
    
    def _prepare_transcript_for_ai(self, segments: List[Dict]) -> str:
        """Preparar transcripción para envío a la IA."""
        # Crear texto con timestamps para la IA
        text_parts = []
        for segment in segments:
            start_time = segment.get("start", 0)
            text = clean_text(segment.get("text", ""))
            text_parts.append(f"[{start_time:.1f}s] {text}")
        
        return "\n".join(text_parts)
    
    def _get_ai_segmentation(self, 
                           transcript_text: str, 
                           keywords_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """Obtener segmentación de la IA."""
        
        # Preparar contexto adicional
        context_info = []
        if keywords_filter:
            context_info.append(f"Palabras clave de interés: {', '.join(keywords_filter)}")
        
        context_info.append(f"Duración mínima: {self.config.min_duration}s")
        context_info.append(f"Duración máxima: {self.config.max_duration}s")
        context_info.append(f"Duración ideal: {self.config.target_duration}s")
        context_info.append(f"Máximo clips: {self.config.max_clips}")
        
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(transcript_text, "\n".join(context_info))
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content
            return json.loads(response_text)
            
        except Exception as e:
            logger.error(f"Error llamando a OpenAI API: {e}")
            raise SegmentationError(f"Error en segmentación IA: {e}")
    
    def _get_system_prompt(self) -> str:
        """Obtener prompt del sistema para la IA."""
        return """Eres un experto editor de video especializado en crear clips cortos y virales para YouTube Shorts. 

Tu tarea es analizar transcripciones de podcasts/videos y segmentarlos en clips de alta calidad que:
- Sean coherentes y tengan sentido por sí solos
- Contengan información valiosa, consejos, anécdotas o datos interesantes
- Generen engagement y sean compartibles
- Tengan un inicio y final natural
- Sean perfectos para el formato vertical de YouTube Shorts

TIPOS DE CONTENIDO IDEAL:
- Consejos prácticos y tips
- Explicaciones técnicas interesantes
- Anécdotas y experiencias personales
- Datos sorprendentes o curiosos
- Preguntas y respuestas relevantes
- Reflexiones profundas
- Momentos de humor o inspiración

Debes devolver SIEMPRE un JSON válido con el formato especificado. No incluyas texto adicional fuera del JSON."""
    
    def _get_user_prompt(self, transcript_text: str, context_info: str) -> str:
        """Obtener prompt del usuario para la IA."""
        return f"""Analiza esta transcripción y identifica los mejores segmentos para YouTube Shorts:

CONTEXTO:
{context_info}

TRANSCRIPCIÓN:
{transcript_text}

INSTRUCCIONES:
1. Identifica los mejores momentos que funcionarían como clips independientes
2. Asegúrate de que cada clip tenga coherencia narrativa
3. Prioriza contenido con valor educativo, entretenimiento o inspiración
4. Evita clips que dependan de contexto previo para entenderse
5. Busca momentos con "gancho" que enganchen desde el inicio

FORMATO DE RESPUESTA (JSON):
{{
    "clips": [
        {{
            "id": "clip_1",
            "title": "Título descriptivo del clip",
            "start_time": 45.2,
            "end_time": 78.5,
            "duration": 33.3,
            "content_type": "tutorial|consejo|anécdota|dato_interesante|reflexión|pregunta_respuesta",
            "hook": "Frase de apertura atractiva",
            "summary": "Resumen breve del contenido",
            "keywords": ["palabra1", "palabra2", "palabra3"],
            "viral_potential": 85,
            "coherence_score": 92,
            "engagement_factors": ["factor1", "factor2"]
        }}
    ],
    "analysis_notes": "Breve análisis del contenido global",
    "total_clips_found": 3
}}

Responde SOLO con el JSON, sin texto adicional."""
    
    def _convert_ai_response_to_candidates(self, 
                                         ai_response: Dict[str, Any],
                                         segments: List[Dict],
                                         transcript_data: Dict) -> List[ClipCandidate]:
        """Convertir respuesta de IA a candidatos."""
        candidates = []
        
        clips = ai_response.get("clips", [])
        
        for clip_data in clips:
            try:
                start_time = float(clip_data["start_time"])
                end_time = float(clip_data["end_time"])
                duration = end_time - start_time
                
                # Validar duración
                if not (self.config.min_duration <= duration <= self.config.max_duration):
                    logger.warning(f"Clip {clip_data['id']} tiene duración inválida: {duration}s")
                    continue
                
                # Extraer texto del segmento
                clip_text = self._extract_text_for_timerange(segments, start_time, end_time)
                
                # Crear metadatos enriquecidos
                metadata = {
                    "ai_generated": True,
                    "title": clip_data.get("title", ""),
                    "content_type": clip_data.get("content_type", "unknown"),
                    "hook": clip_data.get("hook", ""),
                    "summary": clip_data.get("summary", ""),
                    "viral_potential": clip_data.get("viral_potential", 50),
                    "coherence_score": clip_data.get("coherence_score", 50),
                    "engagement_factors": clip_data.get("engagement_factors", []),
                    "ai_keywords": clip_data.get("keywords", [])
                }
                
                # Calcular score combinado
                score = self._calculate_ai_score(clip_data, duration)
                
                candidate = ClipCandidate(
                    id=clip_data["id"],
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    text=clip_text,
                    keywords=clip_data.get("keywords", []),
                    score=score,
                    metadata=metadata
                )
                
                candidates.append(candidate)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Error procesando clip IA: {e}")
                continue
        
        # Ordenar por score
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        return candidates
    
    def _extract_text_for_timerange(self, segments: List[Dict], 
                                  start_time: float, end_time: float) -> str:
        """Extraer texto para un rango de tiempo específico."""
        text_parts = []
        
        for segment in segments:
            seg_start = segment.get("start", 0)
            seg_end = segment.get("end", 0)
            
            # Verificar solapamiento
            if seg_end >= start_time and seg_start <= end_time:
                text_parts.append(clean_text(segment.get("text", "")))
        
        return " ".join(text_parts)
    
    def _calculate_ai_score(self, clip_data: Dict, duration: float) -> float:
        """Calcular score basado en análisis de IA."""
        viral_potential = clip_data.get("viral_potential", 50)
        coherence_score = clip_data.get("coherence_score", 50)
        
        # Factor de duración (preferir duración cercana al objetivo)
        duration_diff = abs(duration - self.config.target_duration)
        duration_score = max(0, 100 - (duration_diff / self.config.target_duration) * 50)
        
        # Score final ponderado
        final_score = (
            viral_potential * 0.4 +      # 40% potencial viral
            coherence_score * 0.3 +      # 30% coherencia
            duration_score * 0.3         # 30% duración óptima
        )
        
        return round(final_score, 2)
