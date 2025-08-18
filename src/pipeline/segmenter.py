"""
Módulo de segmentación de transcripciones en clips candidatos.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import timedelta

from ..utils.text import clean_text, extract_keywords_from_text, format_timestamp

logger = logging.getLogger(__name__)


class SegmentationError(Exception):
    """Error específico de segmentación."""
    pass


@dataclass
class ClipCandidate:
    """Candidato a clip corto."""
    id: str
    start_time: float
    end_time: float
    duration: float
    text: str
    keywords: List[str]
    score: float
    metadata: Dict[str, Any]
    
    @property
    def formatted_duration(self) -> str:
        """Duración formateada como MM:SS."""
        return format_timestamp(self.duration)

    def dict(self) -> Dict[str, Any]:
        """Representación serializable (compatibilidad con AI segmenter)."""
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "text": self.text,
            "keywords": self.keywords,
            "score": self.score,
            "metadata": self.metadata,
        }


class TranscriptSegmenter:
    """Segmentador de transcripciones en clips candidatos."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar segmentador.
        
        Args:
            config: Configuración de segmentación
        """
        self.config = config
        self.min_duration = config.get("min_clip_duration", 15)  # segundos
        self.max_duration = config.get("max_clip_duration", 59)  # segundos
        self.target_duration = config.get("target_clip_duration", 45)  # segundos
        self.overlap_threshold = config.get("overlap_threshold", 0.1)  # 10%
        
        # Configuración de puntuación
        self.scoring_weights = config.get("scoring_weights", {
            "keyword_match": 0.3,
            "sentence_completeness": 0.25,
            "duration_fit": 0.25,
            "speech_quality": 0.2
        })
        
        # Palabras clave importantes
        self.important_keywords = set(config.get("important_keywords", []))
        
        logger.info(f"TranscriptSegmenter inicializado: {self.min_duration}-{self.max_duration}s")
    
    def segment_transcript(self, transcript_path: Path, 
                          keywords_filter: Optional[List[str]] = None) -> List[ClipCandidate]:
        """
        Segmentar una transcripción en clips candidatos.
        
        Args:
            transcript_path: Ruta al archivo JSON de transcripción
            keywords_filter: Lista opcional de palabras clave para filtrar
        
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
        
        logger.info(f"Segmentando {len(segments)} segmentos de transcripción")
        
        # Generar candidatos usando diferentes estrategias
        candidates = []
        
        # 1. Segmentación por frases completas
        sentence_candidates = self._segment_by_sentences(segments, transcript_data)
        candidates.extend(sentence_candidates)
        
        # 2. Segmentación por palabras clave
        if keywords_filter or self.important_keywords:
            target_keywords = set(keywords_filter or []) | self.important_keywords
            keyword_candidates = self._segment_by_keywords(segments, target_keywords, transcript_data)
            candidates.extend(keyword_candidates)
        
        # 3. Segmentación por pausas naturales
        pause_candidates = self._segment_by_pauses(segments, transcript_data)
        candidates.extend(pause_candidates)
        
        # 4. Filtrar duplicados y solapamientos
        filtered_candidates = self._filter_overlapping_candidates(candidates)
        
        # 5. Ordenar por puntuación
        filtered_candidates.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Generados {len(filtered_candidates)} clips candidatos")
        
        return filtered_candidates
    
    def _segment_by_sentences(self, segments: List[Dict], 
                             transcript_data: Dict) -> List[ClipCandidate]:
        """Segmentar por oraciones completas."""
        candidates = []
        current_segments = []
        current_start = None
        
        for segment in segments:
            if current_start is None:
                current_start = segment["start"]
            
            current_segments.append(segment)
            current_duration = segment["end"] - current_start
            current_text = " ".join(s["text"].strip() for s in current_segments)
            
            # Verificar si es una oración completa
            is_sentence_end = self._is_sentence_boundary(segment["text"])
            
            # Crear candidato si se cumplen condiciones
            if (is_sentence_end and 
                self.min_duration <= current_duration <= self.max_duration and
                len(current_text.split()) >= 10):  # Mínimo 10 palabras
                
                candidate = self._create_candidate(
                    current_segments, current_start, segment["end"],
                    current_text, "sentence", transcript_data
                )
                candidates.append(candidate)
                
                # Reset para siguiente candidato
                current_segments = []
                current_start = None
            
            # Reset si superamos duración máxima
            elif current_duration > self.max_duration:
                current_segments = [segment]
                current_start = segment["start"]
        
        return candidates
    
    def _segment_by_keywords(self, segments: List[Dict], keywords: set,
                           transcript_data: Dict) -> List[ClipCandidate]:
        """Segmentar por coincidencias de palabras clave."""
        candidates = []
        
        for i, segment in enumerate(segments):
            segment_keywords = extract_keywords_from_text(segment["text"].lower())
            
            # Verificar si hay coincidencias importantes
            matches = keywords & set(segment_keywords)
            if not matches:
                continue
            
            # Expandir contexto alrededor del segmento con palabras clave
            context_segments = self._expand_context(segments, i, self.target_duration)
            
            if len(context_segments) > 0:
                start_time = context_segments[0]["start"]
                end_time = context_segments[-1]["end"]
                duration = end_time - start_time
                
                if self.min_duration <= duration <= self.max_duration:
                    text = " ".join(s["text"].strip() for s in context_segments)
                    
                    candidate = self._create_candidate(
                        context_segments, start_time, end_time,
                        text, "keyword", transcript_data,
                        extra_metadata={"matched_keywords": list(matches)}
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _segment_by_pauses(self, segments: List[Dict],
                          transcript_data: Dict) -> List[ClipCandidate]:
        """Segmentar por pausas naturales."""
        candidates = []
        pause_threshold = 1.0  # 1 segundo de pausa
        
        current_segments = []
        current_start = None
        
        for i, segment in enumerate(segments):
            if current_start is None:
                current_start = segment["start"]
            
            current_segments.append(segment)
            current_duration = segment["end"] - current_start
            
            # Verificar si hay pausa después de este segmento
            has_pause = False
            if i < len(segments) - 1:
                next_segment = segments[i + 1]
                gap = next_segment["start"] - segment["end"]
                has_pause = gap >= pause_threshold
            
            # Crear candidato en pausa natural
            if (has_pause and 
                self.min_duration <= current_duration <= self.max_duration and
                len(current_segments) >= 2):  # Mínimo 2 segmentos
                
                text = " ".join(s["text"].strip() for s in current_segments)
                
                candidate = self._create_candidate(
                    current_segments, current_start, segment["end"],
                    text, "pause", transcript_data
                )
                candidates.append(candidate)
                
                # Reset
                current_segments = []
                current_start = None
        
        return candidates
    
    def _create_candidate(self, segments: List[Dict], start_time: float,
                         end_time: float, text: str, strategy: str,
                         transcript_data: Dict,
                         extra_metadata: Optional[Dict] = None) -> ClipCandidate:
        """Crear un candidato a clip."""
        duration = end_time - start_time
        
        # Limpiar y extraer información del texto
        clean_text_content = clean_text(text)
        keywords = extract_keywords_from_text(clean_text_content.lower())
        
        # Calcular puntuación
        score = self._calculate_clip_score(
            segments, clean_text_content, keywords, duration, transcript_data
        )
        
        # Metadatos
        metadata = {
            "strategy": strategy,
            "segment_count": len(segments),
            "original_text": text,
            "word_count": len(clean_text_content.split()),
            "start_formatted": format_timestamp(start_time),
            "end_formatted": format_timestamp(end_time),
            "language": transcript_data.get("language", "unknown")
        }
        
        if extra_metadata:
            metadata.update(extra_metadata)
        
        # Generar ID único
        clip_id = f"{strategy}_{int(start_time*1000)}_{int(end_time*1000)}"
        
        return ClipCandidate(
            id=clip_id,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            text=clean_text_content,
            keywords=keywords,
            score=score,
            metadata=metadata
        )
    
    def _calculate_clip_score(self, segments: List[Dict], text: str,
                            keywords: List[str], duration: float,
                            transcript_data: Dict) -> float:
        """Calcular puntuación de calidad de un clip."""
        scores = {}
        
        # 1. Coincidencia de palabras clave importantes
        keyword_matches = len(self.important_keywords & set(keywords))
        scores["keyword_match"] = min(keyword_matches / max(len(self.important_keywords), 1), 1.0)
        
        # 2. Completitud de oraciones
        sentence_score = 1.0 if self._is_complete_thought(text) else 0.5
        scores["sentence_completeness"] = sentence_score
        
        # 3. Ajuste de duración al target
        duration_diff = abs(duration - self.target_duration)
        duration_score = max(0, 1.0 - (duration_diff / self.target_duration))
        scores["duration_fit"] = duration_score
        
        # 4. Calidad del habla (basada en probabilidades de Whisper)
        speech_quality = self._calculate_speech_quality(segments)
        scores["speech_quality"] = speech_quality
        
        # 5. NUEVO: Bonus por contenido en español
        spanish_bonus = self._calculate_spanish_bonus(text)
        scores["spanish_content"] = spanish_bonus
        
        # Actualizar pesos para incluir el bonus español
        weights = self.scoring_weights.copy()
        if "spanish_content" not in weights:
            weights["spanish_content"] = 0.2  # 20% de peso para español
            # Reajustar otros pesos proporcionalmente
            adjustment = 0.8  # Reducir otros pesos al 80%
            for key in weights:
                if key != "spanish_content":
                    weights[key] *= adjustment
        
        # Calcular puntuación final ponderada
        final_score = sum(
            scores[key] * weights.get(key, 0)
            for key in scores
        ) * 100  # Escalar a 0-100
        
        return round(final_score, 2)
    
    def _calculate_spanish_bonus(self, text: str) -> float:
        """Calcular bonus por contenido en español."""
        # Palabras comunes en español
        spanish_words = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 
            'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'pero', 'más',
            'hay', 'muy', 'todo', 'ser', 'ya', 'tiene', 'así', 'puede', 'sus', 'está', 'me',
            'si', 'bien', 'dijo', 'hacer', 'ese', 'esta', 'vez', 'años', 'hasta', 'donde',
            'porque', 'mismo', 'entonces', 'nosotros', 'vamos', 'tenemos', 'cosa', 'tiempo',
            'programación', 'código', 'español', 'idioma', 'lenguaje', 'desarrolladores'
        }
        
        # Contar palabras en español vs total de palabras
        words = text.lower().split()
        if not words:
            return 0.0
            
        spanish_count = sum(1 for word in words if any(sp_word in word for sp_word in spanish_words))
        spanish_ratio = spanish_count / len(words)
        
        # Bonus adicional por patrones típicos del español
        spanish_patterns = ['que ', ' es ', ' se ', ' me ', ' te ', ' le ', ' no ', ' sí', ' muy ']
        pattern_matches = sum(1 for pattern in spanish_patterns if pattern in text.lower())
        pattern_bonus = min(pattern_matches * 0.1, 0.3)  # Max 30% bonus por patrones
        
        return min(spanish_ratio + pattern_bonus, 1.0)
    
    def _calculate_speech_quality(self, segments: List[Dict]) -> float:
        """Calcular calidad del habla basada en métricas de Whisper."""
        if not segments:
            return 0.0
        
        total_prob = 0
        total_no_speech = 0
        count = 0
        
        for segment in segments:
            # Probabilidad promedio logarítmica (más alta = mejor)
            avg_logprob = segment.get("avg_logprob", -1.0)
            prob_score = min(max((avg_logprob + 1.0), 0), 1.0)  # Normalizar
            
            # Probabilidad de no-habla (más baja = mejor)
            no_speech_prob = segment.get("no_speech_prob", 0.5)
            no_speech_score = 1.0 - no_speech_prob
            
            total_prob += prob_score
            total_no_speech += no_speech_score
            count += 1
        
        if count == 0:
            return 0.0
        
        return (total_prob + total_no_speech) / (2 * count)
    
    def _is_sentence_boundary(self, text: str) -> bool:
        """Verificar si el texto termina en límite de oración."""
        text = text.strip()
        return bool(re.search(r'[.!?]$', text))
    
    def _is_complete_thought(self, text: str) -> bool:
        """Verificar si el texto representa un pensamiento completo."""
        text = text.strip()
        
        # Verificar terminaciones de oración
        if not re.search(r'[.!?]$', text):
            return False
        
        # Verificar longitud mínima
        words = text.split()
        if len(words) < 5:
            return False
        
        # Verificar que no empiece con conjunciones colgantes
        first_word = words[0].lower()
        hanging_words = {'and', 'but', 'or', 'so', 'then', 'also', 'however'}
        if first_word in hanging_words:
            return False
        
        return True
    
    def _expand_context(self, segments: List[Dict], center_idx: int,
                       target_duration: float) -> List[Dict]:
        """Expandir contexto alrededor de un segmento central."""
        if not segments:
            return []
        
        center_segment = segments[center_idx]
        start_idx = center_idx
        end_idx = center_idx
        
        # Expandir hacia atrás
        while start_idx > 0:
            candidate_start = segments[start_idx - 1]["start"]
            duration = center_segment["end"] - candidate_start
            
            if duration > target_duration * 1.2:  # 20% margen
                break
            
            start_idx -= 1
        
        # Expandir hacia adelante
        while end_idx < len(segments) - 1:
            candidate_end = segments[end_idx + 1]["end"]
            duration = candidate_end - center_segment["start"]
            
            if duration > target_duration * 1.2:  # 20% margen
                break
            
            end_idx += 1
        
        return segments[start_idx:end_idx + 1]
    
    def _filter_overlapping_candidates(self, candidates: List[ClipCandidate]) -> List[ClipCandidate]:
        """Filtrar candidatos solapados, manteniendo los mejores."""
        if not candidates:
            return []
        
        # Ordenar por puntuación descendente
        sorted_candidates = sorted(candidates, key=lambda x: x.score, reverse=True)
        filtered = []
        
        for candidate in sorted_candidates:
            # Verificar solapamiento con candidatos ya aceptados
            has_significant_overlap = any(
                self._calculate_overlap(candidate, accepted) > self.overlap_threshold
                for accepted in filtered
            )
            
            if not has_significant_overlap:
                filtered.append(candidate)
        
        return filtered
    
    def _calculate_overlap(self, clip1: ClipCandidate, clip2: ClipCandidate) -> float:
        """Calcular solapamiento entre dos clips (0.0 = sin solapamiento, 1.0 = solapamiento total)."""
        # Calcular intersección
        overlap_start = max(clip1.start_time, clip2.start_time)
        overlap_end = min(clip1.end_time, clip2.end_time)
        overlap_duration = max(0, overlap_end - overlap_start)
        
        # Calcular unión
        union_start = min(clip1.start_time, clip2.start_time)
        union_end = max(clip1.end_time, clip2.end_time)
        union_duration = union_end - union_start
        
        if union_duration == 0:
            return 0.0
        
        return overlap_duration / union_duration
    
    def export_candidates(self, candidates: List[ClipCandidate], 
                         output_path: Path) -> None:
        """Exportar candidatos a archivo JSON."""
        export_data = {
            "timestamp": format_timestamp(0),  # Timestamp actual
            "total_candidates": len(candidates),
            "config": self.config,
            "candidates": []
        }
        
        for candidate in candidates:
            candidate_data = {
                "id": candidate.id,
                "start_time": candidate.start_time,
                "end_time": candidate.end_time,
                "duration": candidate.duration,
                "formatted_duration": candidate.formatted_duration,
                "text": candidate.text,
                "keywords": candidate.keywords,
                "score": candidate.score,
                "metadata": candidate.metadata
            }
            export_data["candidates"].append(candidate_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Candidatos exportados a {output_path}")


def segment_transcript_file(transcript_path: Path, output_dir: Path,
                           config: Dict[str, Any],
                           keywords_filter: Optional[List[str]] = None) -> List[ClipCandidate]:
    """
    Función helper para segmentar un archivo de transcripción.
    
    Args:
        transcript_path: Ruta al archivo de transcripción JSON
        output_dir: Directorio de salida
        config: Configuración de segmentación
        keywords_filter: Palabras clave para filtrar
    
    Returns:
        Lista de clips candidatos
    """
    segmenter = TranscriptSegmenter(config)
    candidates = segmenter.segment_transcript(transcript_path, keywords_filter)
    
    # Exportar resultados
    output_dir.mkdir(parents=True, exist_ok=True)
    export_path = output_dir / f"{transcript_path.stem}_candidates.json"
    segmenter.export_candidates(candidates, export_path)
    
    return candidates
