"""Downloader de videos descubiertos usando yt-dlp.

Flujo:
1. Seleccionar N videos con status 'discovered' y downloaded=0
2. Descargar con yt-dlp (formato mejor audio+video <=1080p)
3. Guardar archivo en data/raw/{channel_id}/{video_id}.mp4
4. Actualizar DB: mark_video_downloaded(video_id, file_path)
5. Manejar errores y continuar

Requisitos: paquete yt-dlp instalado.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any
import subprocess
import shlex

from .db import PipelineDB

logger = logging.getLogger(__name__)

YTDLP_CMD_TEMPLATE = (
    "yt-dlp -f 'bv*[height<=1080]+ba/b[height<=1080]' --merge-output-format mp4 "
    "--no-playlist --no-colors --quiet --progress --newline -o {output} https://www.youtube.com/watch?v={video_id}"
)

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

class DownloadError(Exception):
    pass

def download_video(video_id: str, channel_id: str, base_dir: Path) -> Path:
    target_dir = base_dir / 'raw' / channel_id
    ensure_dir(target_dir)
    out_template = target_dir / f"{video_id}.mp4"
    if out_template.exists():
        logger.info(f"Archivo ya existe, omitiendo descarga: {out_template}")
        return out_template
    cmd = YTDLP_CMD_TEMPLATE.format(output=shlex.quote(str(out_template)), video_id=video_id)
    logger.debug(f"Ejecutando: {cmd}")
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise DownloadError(proc.stderr.strip()[:500])
    if not out_template.exists():
        raise DownloadError("Descarga terminada pero archivo no encontrado")
    return out_template

def download_pending(db: PipelineDB, limit: int = 3, base_dir: Path = Path('data')) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    pending = db.get_pending_downloads(limit=limit)
    if not pending:
        return results
    for video in pending:
        vid = video['video_id']
        channel_id = video['channel_id']
        try:
            path = download_video(vid, channel_id, base_dir)
            db.mark_video_downloaded(vid, str(path))
            results.append({'video_id': vid, 'success': True, 'file_path': str(path)})
            logger.info(f"Descargado {vid} -> {path}")
        except Exception as e:
            logger.error(f"Error descargando {vid}: {e}")
            results.append({'video_id': vid, 'success': False, 'error': str(e)})
    return results

__all__ = [
    'download_pending', 'download_video', 'DownloadError'
]
