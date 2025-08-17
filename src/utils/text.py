"""
Utilidades para manipulación de texto y transcripciones.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def clean_text_for_segments(text: str) -> str:
    """Limpiar texto para análisis de segmentación."""
    # Normalizar espacios
    text = re.sub(r'\s+', ' ', text)
    
    # Remover caracteres problemáticos pero mantener puntuación básica
    text = re.sub(r'[^\w\s.,;:!?¿¡\-\'"áéíóúüñÁÉÍÓÚÜÑ]', ' ', text)
    
    # Normalizar signos de puntuación
    text = re.sub(r'[,;]', ',', text)
    text = re.sub(r'[.!?¿¡]', '.', text)
    
    return text.strip()


# Alias for backwards compatibility
clean_text = clean_text_for_segments


def format_timestamp_seconds(seconds: float) -> str:
    """Formatear segundos como MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


# Alias for backwards compatibility  
format_timestamp = format_timestamp_seconds


def extract_keywords_from_text(text: str, min_length: int = 3) -> List[str]:
    """Extraer palabras clave básicas del texto."""
    # Limpiar texto
    clean = clean_text_for_segments(text.lower())
    
    # Dividir en palabras
    words = clean.split()
    
    # Filtrar palabras cortas y stopwords básicas
    stopwords = {
        'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo',
        'le', 'da', 'su', 'por', 'son', 'con', 'para', 'del', 'las', 'una', 'al',
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had'
    }
    
    keywords = []
    for word in words:
        # Remover puntuación
        word = re.sub(r'[^\w]', '', word)
        if len(word) >= min_length and word not in stopwords:
            keywords.append(word)
    
    return keywords


def parse_srt_file(srt_path: Path) -> List[Dict[str, Any]]:
    """Parsear archivo SRT y devolver lista de subtítulos."""
    if not srt_path.exists():
        raise FileNotFoundError(f"Archivo SRT no encontrado: {srt_path}")
    
    subtitles = []
    
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Dividir por bloques (separados por doble salto de línea)
        blocks = re.split(r'\n\s*\n', content)
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
                
            # Línea 1: número de secuencia
            try:
                sequence = int(lines[0])
            except ValueError:
                continue
                
            # Línea 2: timestamp
            timestamp_match = re.match(
                r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
                lines[1]
            )
            
            if not timestamp_match:
                continue
                
            start_time = (
                int(timestamp_match.group(1)) * 3600 +  # horas
                int(timestamp_match.group(2)) * 60 +    # minutos
                int(timestamp_match.group(3)) +         # segundos
                int(timestamp_match.group(4)) / 1000    # milisegundos
            )
            
            end_time = (
                int(timestamp_match.group(5)) * 3600 +
                int(timestamp_match.group(6)) * 60 +
                int(timestamp_match.group(7)) +
                int(timestamp_match.group(8)) / 1000
            )
            
            # Líneas 3+: texto del subtítulo
            text = ' '.join(lines[2:])
            text = clean_text_for_segments(text)
            
            subtitles.append({
                'sequence': sequence,
                'start': start_time,
                'end': end_time,
                'duration': end_time - start_time,
                'text': text
            })
    
    except Exception as e:
        logger.error(f"Error parseando SRT {srt_path}: {e}")
        raise
    
    return subtitles


def save_srt_file(subtitles: List[Dict[str, Any]], srt_path: Path):
    """Guardar subtítulos en formato SRT."""
    try:
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles, 1):
                # Número de secuencia
                f.write(f"{i}\n")
                
                # Timestamp
                start_time = format_srt_timestamp(sub['start'])
                end_time = format_srt_timestamp(sub['end'])
                f.write(f"{start_time} --> {end_time}\n")
                
                # Texto
                f.write(f"{sub['text']}\n\n")
                
        logger.info(f"Archivo SRT guardado: {srt_path}")
        
    except Exception as e:
        logger.error(f"Error guardando SRT {srt_path}: {e}")
        raise


def format_srt_timestamp(seconds: float) -> str:
    """Convertir segundos a formato de timestamp SRT."""
    td = timedelta(seconds=seconds)
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    secs = int(td.total_seconds() % 60)
    millis = int((td.total_seconds() % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def detect_sentence_boundaries(text: str) -> List[int]:
    """Detectar límites de oraciones en el texto."""
    # Patrones de fin de oración
    sentence_endings = re.finditer(r'[.!?¡¿]\s*', text)
    boundaries = [0]  # Empezar desde el principio
    
    for match in sentence_endings:
        boundaries.append(match.end())
    
    # Añadir final del texto si no está ya
    if boundaries[-1] != len(text):
        boundaries.append(len(text))
    
    return boundaries


def extract_keywords(text: str, keyword_lists: Dict[str, List[str]]) -> Dict[str, int]:
    """Extraer y contar palabras clave en el texto."""
    text_lower = text.lower()
    keyword_counts = {}
    
    for category, keywords in keyword_lists.items():
        count = 0
        for keyword in keywords:
            # Buscar palabra completa (no parte de otra palabra)
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            matches = re.findall(pattern, text_lower)
            count += len(matches)
        keyword_counts[category] = count
    
    return keyword_counts


def calculate_text_density(text: str, duration: float) -> float:
    """Calcular densidad de texto (palabras por minuto)."""
    if duration <= 0:
        return 0.0
    
    word_count = len(text.split())
    words_per_minute = (word_count / duration) * 60
    
    return words_per_minute


def find_optimal_cut_points(text: str, target_length: int, 
                          tolerance: int = 50) -> List[Tuple[int, int]]:
    """Encontrar puntos óptimos para cortar texto manteniendo oraciones completas."""
    if len(text) <= target_length:
        return [(0, len(text))]
    
    sentences = detect_sentence_boundaries(text)
    cuts = []
    start = 0
    
    for i in range(1, len(sentences)):
        current_length = sentences[i] - start
        
        if current_length >= target_length - tolerance:
            # Si estamos cerca del objetivo, cortar aquí
            cuts.append((start, sentences[i]))
            start = sentences[i]
        elif current_length > target_length + tolerance:
            # Si ya pasamos el límite, cortar en la oración anterior
            if i > 1:
                cuts.append((start, sentences[i-1]))
                start = sentences[i-1]
            else:
                # Forzar corte si la primera oración es muy larga
                cuts.append((start, sentences[i]))
                start = sentences[i]
    
    # Añadir último segmento si queda texto
    if start < len(text):
        cuts.append((start, len(text)))
    
    return cuts


def validate_transcript_quality(transcript_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validar calidad de transcripción y devolver métricas."""
    text = transcript_data.get('text', '')
    segments = transcript_data.get('segments', [])
    
    metrics = {
        'total_duration': 0,
        'total_words': len(text.split()),
        'avg_confidence': 0,
        'low_confidence_segments': 0,
        'empty_segments': 0,
        'words_per_minute': 0,
        'quality_score': 0
    }
    
    if not segments:
        return metrics
    
    confidences = []
    total_duration = 0
    
    for segment in segments:
        duration = segment.get('end', 0) - segment.get('start', 0)
        total_duration += duration
        
        # Verificar confianza si está disponible
        if 'words' in segment:
            for word in segment['words']:
                if 'probability' in word:
                    conf = word['probability']
                    confidences.append(conf)
                    if conf < 0.6:  # Confianza baja
                        metrics['low_confidence_segments'] += 1
        
        # Verificar segmentos vacíos
        if not segment.get('text', '').strip():
            metrics['empty_segments'] += 1
    
    metrics['total_duration'] = total_duration
    metrics['words_per_minute'] = (metrics['total_words'] / total_duration * 60) if total_duration > 0 else 0
    metrics['avg_confidence'] = sum(confidences) / len(confidences) if confidences else 0
    
    # Calcular score de calidad (0-100)
    quality_factors = []
    
    # Factor 1: Confianza promedio
    if metrics['avg_confidence'] > 0:
        quality_factors.append(min(100, metrics['avg_confidence'] * 100))
    
    # Factor 2: Palabras por minuto (óptimo ~150-180)
    wpm = metrics['words_per_minute']
    if 120 <= wpm <= 200:
        quality_factors.append(100)
    elif 100 <= wpm <= 250:
        quality_factors.append(80)
    else:
        quality_factors.append(60)
    
    # Factor 3: Porcentaje de segmentos problemáticos
    total_segments = len(segments)
    problem_ratio = (metrics['low_confidence_segments'] + metrics['empty_segments']) / total_segments if total_segments > 0 else 0
    quality_factors.append(max(0, 100 - problem_ratio * 100))
    
    metrics['quality_score'] = sum(quality_factors) / len(quality_factors) if quality_factors else 0
    
    return metrics
