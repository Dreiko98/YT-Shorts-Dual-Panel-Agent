"""
Módulo de base de datos SQLite para el pipeline.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PipelineDB:
    """Gestor de base de datos SQLite para el pipeline."""
    
    def __init__(self, db_path: str = "data/pipeline.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Inicializar esquema de base de datos."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Tabla de videos descubiertos
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    published_at TEXT NOT NULL,
                    duration_seconds INTEGER,
                    view_count INTEGER,
                    discovered_at TEXT NOT NULL,
                    processed INTEGER DEFAULT 0,
                    downloaded INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'discovered',
                    FOREIGN KEY (channel_id) REFERENCES channels (channel_id)
                );
                
                -- Tabla de canales
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    last_checked TEXT,
                    total_videos INTEGER DEFAULT 0
                );
                
                -- Tabla de segmentos/clips candidatos  
                CREATE TABLE IF NOT EXISTS segments (
                    clip_id TEXT PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    start_seconds REAL NOT NULL,
                    end_seconds REAL NOT NULL,
                    duration_seconds REAL NOT NULL,
                    score REAL NOT NULL,
                    transcript_text TEXT,
                    status TEXT DEFAULT 'candidate',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (video_id) REFERENCES videos (video_id)
                );
                
                -- Tabla de assets de B-roll
                CREATE TABLE IF NOT EXISTS broll_assets (
                    asset_id TEXT PRIMARY KEY,
                    pool TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    resolution TEXT,
                    fps INTEGER,
                    file_size_mb REAL,
                    checksum TEXT,
                    usage_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    created_at TEXT NOT NULL
                );
                
                -- Tabla de uso de B-roll (tracking)
                CREATE TABLE IF NOT EXISTS broll_usage (
                    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clip_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    start_seconds REAL NOT NULL,
                    end_seconds REAL NOT NULL,
                    used_at TEXT NOT NULL,
                    FOREIGN KEY (clip_id) REFERENCES composites (clip_id),
                    FOREIGN KEY (asset_id) REFERENCES broll_assets (asset_id)
                );
                
                -- Tabla de Shorts compuestos finales
                CREATE TABLE IF NOT EXISTS composites (
                    clip_id TEXT PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    segment_id TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    fps INTEGER NOT NULL,
                    resolution TEXT NOT NULL,
                    lufs REAL,
                    file_size_mb REAL,
                    template_used TEXT,
                    uploaded INTEGER DEFAULT 0,
                    youtube_short_id TEXT,
                    upload_date TEXT,
                    status TEXT DEFAULT 'ready',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (video_id) REFERENCES videos (video_id),
                    FOREIGN KEY (segment_id) REFERENCES segments (clip_id)
                );
                
                -- Índices para optimizar consultas
                CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id);
                CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
                CREATE INDEX IF NOT EXISTS idx_segments_video ON segments(video_id);
                CREATE INDEX IF NOT EXISTS idx_segments_status ON segments(status);
                CREATE INDEX IF NOT EXISTS idx_composites_uploaded ON composites(uploaded);
                CREATE INDEX IF NOT EXISTS idx_broll_pool ON broll_assets(pool);
                CREATE INDEX IF NOT EXISTS idx_broll_usage_asset ON broll_usage(asset_id);
            """)
        logger.info(f"Base de datos inicializada en {self.db_path}")
        # Aplicar migraciones ligeras (idempotentes)
        self._apply_migrations()

    def _apply_migrations(self):
        """Aplicar migraciones de esquema necesarias (idempotentes)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Añadir columna file_path a videos si no existe
                cursor = conn.execute("PRAGMA table_info(videos)")
                cols = {row[1] for row in cursor.fetchall()}
                if 'file_path' not in cols:
                    conn.execute("ALTER TABLE videos ADD COLUMN file_path TEXT")
                    logger.info("Migración: añadida columna videos.file_path")
        except sqlite3.Error as e:
            logger.error(f"Error aplicando migraciones: {e}")
    
    def add_video(self, video_data: Dict[str, Any]) -> bool:
        """Añadir nuevo video descubierto."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO videos 
                    (video_id, channel_id, title, description, published_at, 
                     duration_seconds, view_count, discovered_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_data['video_id'],
                    video_data['channel_id'], 
                    video_data['title'],
                    video_data.get('description', ''),
                    video_data['published_at'],
                    video_data.get('duration_seconds'),
                    video_data.get('view_count'),
                    datetime.now().isoformat(),
                    'discovered'
                ))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error añadiendo video {video_data.get('video_id')}: {e}")
            return False

    def video_exists(self, video_id: str) -> bool:
        """Verificar si ya existe un video en la base de datos."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT 1 FROM videos WHERE video_id = ? LIMIT 1", (video_id,))
            return cursor.fetchone() is not None
    
    def get_pending_downloads(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener videos pendientes de descarga."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM videos 
                WHERE downloaded = 0 AND status = 'discovered'
                ORDER BY published_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_video_downloaded(self, video_id: str, file_path: str) -> bool:
        """Marcar video como descargado."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE videos 
                    SET downloaded = 1, status = 'downloaded', file_path = ?
                    WHERE video_id = ?
                """, (file_path, video_id))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error marcando video {video_id} como descargado: {e}")
            return False
    
    def add_segment(self, segment_data: Dict[str, Any]) -> bool:
        """Añadir segmento candidato."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO segments
                    (clip_id, video_id, start_seconds, end_seconds, 
                     duration_seconds, score, transcript_text, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    segment_data['clip_id'],
                    segment_data['video_id'],
                    segment_data['start_seconds'],
                    segment_data['end_seconds'],
                    segment_data['duration_seconds'],
                    segment_data['score'],
                    segment_data.get('transcript_text', ''),
                    datetime.now().isoformat()
                ))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error añadiendo segmento {segment_data.get('clip_id')}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """Obtener estadísticas generales del pipeline."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM videos) as total_videos,
                    (SELECT COUNT(*) FROM videos WHERE downloaded = 1) as downloaded,
                    (SELECT COUNT(*) FROM segments) as segments,
                    (SELECT COUNT(*) FROM composites) as composites,
                    (SELECT COUNT(*) FROM composites WHERE uploaded = 1) as uploaded
            """)
            row = cursor.fetchone()
            return {
                'total_videos': row[0] or 0,
                'downloaded': row[1] or 0, 
                'segments': row[2] or 0,
                'composites': row[3] or 0,
                'uploaded': row[4] or 0
            }

    def get_downloaded_unprocessed(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Obtener videos descargados aún no procesados (processed=0)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM videos
                WHERE downloaded = 1 AND (processed = 0 OR processed IS NULL)
                ORDER BY published_at DESC
                LIMIT ?
                """, (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_video_processed(self, video_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE videos SET processed = 1, status = 'processed' WHERE video_id = ?",
                    (video_id,),
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"Error marcando video {video_id} como procesado: {e}")
            return False
