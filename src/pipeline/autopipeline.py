"""Autopipeline: orquesta discover -> download -> transcribe -> segment (IA + fallback) -> compose.

Limitaciones actuales:
- Procesa un lote pequeño secuencialmente (sin concurrencia)
- Usa configuración fija para segmentación y composición
- Requiere que ffmpeg y whisper estén disponibles

Entradas:
- db_path, workdir
- max_videos: cuántos videos nuevos procesar en este ciclo

Salida:
- Lista de resultados por video con estado y shorts generados
"""
from __future__ import annotations

import os
import json
import random
from pathlib import Path
from typing import List, Dict, Any
import logging

from .db import PipelineDB
from .discovery import discover_new_videos, DiscoveryError
from .downloader import download_pending
from .transcribe import transcribe_video_file, check_whisper_requirements
from .ai_segmenter import AITranscriptSegmenter, AISegmentationConfig
from .editor import compose_short_from_files

logger = logging.getLogger(__name__)

class AutoPipelineResult(Dict[str, Any]):
    pass

def select_random_broll(broll_dir: Path) -> Path | None:
    """Selecciona un video B-roll aleatorio del directorio especificado."""
    if not broll_dir.exists():
        return None
    
    # Extensiones de video válidas
    video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
    
    # Buscar todos los videos en el directorio
    video_files = []
    for ext in video_exts:
        video_files.extend(broll_dir.glob(f'*{ext}'))
        video_files.extend(broll_dir.glob(f'*{ext.upper()}'))
    
    if not video_files:
        return None
    
    # Seleccionar uno aleatorio
    selected = random.choice(video_files)
    return selected

def run_autopipeline(
    db_path: Path = Path('data/pipeline.db'),
    workdir: Path = Path('data'),
    config_path: Path = Path('configs/channels.yaml'),
    max_videos: int = 1,
    max_shorts_per_video: int = 3,
    whisper_model: str = 'base',
    language: str | None = None,
) -> List[AutoPipelineResult]:
    results: List[AutoPipelineResult] = []
    db = PipelineDB(str(db_path))

    # 1. Discovery
    try:
        discover_new_videos(db, config_path)
    except DiscoveryError as e:
        logger.warning(f"Discovery falló: {e}")

    # 2. Descargas (limit = max_videos)
    download_res = download_pending(db, limit=max_videos, base_dir=workdir)
    newly_downloaded = [r['video_id'] for r in download_res if r.get('success')]

    # 3. Obtener videos descargados pero no procesados (incluyendo recién descargados)
    unprocessed = db.get_downloaded_unprocessed(limit=max_videos)
    videos_to_process = [v['video_id'] for v in unprocessed]
    
    # 4. Procesar cada video
    for vid in videos_to_process:
        # Buscar info del video en los no procesados
        video_row = next((v for v in unprocessed if v['video_id'] == vid), None)
        if not video_row:
            continue
        file_path = Path(video_row.get('file_path', '')) if video_row.get('file_path') else None
        if not file_path or not file_path.exists():
            results.append({'video_id': vid, 'success': False, 'error': 'Archivo no encontrado tras descarga'})
            continue
        try:
            # 3a Transcribir (cache)
            transcripts_dir = workdir / 'transcripts'; transcripts_dir.mkdir(exist_ok=True, parents=True)
            transcript_json = transcripts_dir / f"{file_path.stem}_transcript.json"
            if not transcript_json.exists():
                req = check_whisper_requirements()
                if not req['whisper_installed'] or not req['torch_available']:
                    raise RuntimeError('Whisper no disponible')
                tr_result = transcribe_video_file(file_path, transcripts_dir, model=whisper_model, device='auto', language=language)
                if not tr_result.get('success'):
                    raise RuntimeError('Fallo transcripción')
                transcript_json = Path(tr_result['transcript_json'])
            # 3b Segmentar IA + fallback
            ai_conf = AISegmentationConfig(max_clips=max_shorts_per_video, min_duration=15, max_duration=59, target_duration=30)
            ai_seg = AITranscriptSegmenter(ai_conf)
            segments_dir = workdir / 'segments'; segments_dir.mkdir(parents=True, exist_ok=True)
            candidates_path = segments_dir / f"{file_path.stem}_ai_candidates.json"
            try:
                candidates = ai_seg.segment_transcript(transcript_json)
                if not candidates:
                    raise RuntimeError('IA sin candidatos')
                with open(candidates_path, 'w', encoding='utf-8') as f:
                    json.dump({'candidates': [c.dict() for c in candidates]}, f, ensure_ascii=False, indent=2)
            except Exception:
                from .segmenter import segment_transcript_file
                classic_conf = {
                    'min_clip_duration': 15,
                    'max_clip_duration': 59,
                    'target_clip_duration': 30,
                    'overlap_threshold': 0.1,
                    'scoring_weights': {"keyword_match":0.3,"sentence_completeness":0.25,"duration_fit":0.25,"speech_quality":0.2},
                    'important_keywords': []
                }
                cand = segment_transcript_file(transcript_path=transcript_json, output_dir=segments_dir, config=classic_conf)
                if not cand:
                    raise RuntimeError('Fallback sin candidatos')
                with open(candidates_path, 'w', encoding='utf-8') as f:
                    json.dump({'candidates':[c.dict() for c in cand]}, f, ensure_ascii=False, indent=2)
            # 3c Compose
            shorts_dir = workdir / 'shorts_auto'; shorts_dir.mkdir(parents=True, exist_ok=True)
            os.environ['SHORT_SUB_MODE'] = 'fast'
            os.environ['FAST_WORDS_TARGET'] = '2'
            os.environ['FAST_SUB_MIN'] = '0.30'
            os.environ['FAST_SUB_MAX'] = '0.90'
            os.environ['FAST_SUB_COLOR_CYCLE'] = '1'
            os.environ['FAST_SUB_BOUNCE'] = '1'
            
            # Seleccionar B-roll aleatorio
            broll_dir = workdir / 'raw' / 'broll'
            broll_file = select_random_broll(broll_dir)
            
            if not broll_file:
                logger.warning(f"No se encontraron videos B-roll en {broll_dir}, usando video principal como fallback")
                broll_file = file_path
            else:
                logger.info(f"B-roll seleccionado: {broll_file.name}")
            
            results_comp = compose_short_from_files(file_path, broll_file, transcript_json, candidates_path, shorts_dir, max_shorts=max_shorts_per_video)
            ok = sum(1 for r in results_comp if r.get('success'))
            db.mark_video_processed(vid)
            results.append({'video_id': vid, 'success': True, 'shorts_generated': ok})
        except Exception as e:
            results.append({'video_id': vid, 'success': False, 'error': str(e)})
    return results

__all__ = ['run_autopipeline']
