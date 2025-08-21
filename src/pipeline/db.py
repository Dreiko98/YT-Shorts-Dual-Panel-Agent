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

    def get_approved_composites(self, limit: int = 10) -> list:
        """
        Devuelve una lista de shorts (composites) ya aprobados/subidos (uploaded=1), incluyendo el título del video.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT composites.*, videos.title as title
                FROM composites
                LEFT JOIN videos ON composites.video_id = videos.video_id
                WHERE composites.uploaded = 1
                ORDER BY composites.upload_date DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_pending_review_composites(self, limit: int = 20) -> list:
        """
        Devuelve una lista de shorts (composites) pendientes de revisión (status='ready'), incluyendo el título del video.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT composites.*, videos.title as title
                FROM composites
                LEFT JOIN videos ON composites.video_id = videos.video_id
                WHERE composites.status = 'ready' AND (composites.uploaded = 0 OR composites.uploaded IS NULL)
                ORDER BY composites.created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_queue_stats(self):
        """
        Devuelve estadísticas simples de la cola de procesamiento.
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM videos WHERE status='discovered'")
            pending = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM videos WHERE status='downloaded'")
            downloaded = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM videos WHERE status='processed'")
            processed = cur.fetchone()[0]
        return {
            'pending': pending,
            'downloaded': downloaded,
            'processed': processed
        }
    def is_daemon_paused(self):
        """
        Devuelve False por defecto. Implementa lógica real si quieres pausar el daemon desde la base de datos.
        """
        return False
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

    def get_queue_stats(self) -> Dict[str, int]:
        """Obtener estadísticas de la cola de revisión."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        (SELECT COUNT(*) FROM composites WHERE status = 'pending_review' OR status IS NULL) as pending_review,
                        (SELECT COUNT(*) FROM composites WHERE status = 'approved') as approved,
                        (SELECT COUNT(*) FROM composites WHERE status = 'rejected') as rejected,
                        (SELECT COUNT(*) FROM composites WHERE uploaded = 1) as published
                """)
                row = cursor.fetchone()
                return {
                    'pending_review': row[0] or 0,
                    'approved': row[1] or 0,
                    'rejected': row[2] or 0,
                    'published': row[3] or 0
                }
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo estadísticas de cola: {e}")
            return {'pending_review': 0, 'approved': 0, 'rejected': 0, 'published': 0}

    def is_daemon_paused(self) -> bool:
        """Verificar si el daemon está pausado."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Crear tabla de configuración si no existe
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                cursor = conn.execute("SELECT value FROM config WHERE key = 'daemon_paused'")
                row = cursor.fetchone()
                return row and row[0] == 'true'
        except sqlite3.Error as e:
            logger.error(f"Error verificando estado del daemon: {e}")
            return False

    def set_daemon_paused(self, paused: bool) -> bool:
        """Pausar/reanudar el daemon."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Crear tabla de configuración si no existe
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    INSERT OR REPLACE INTO config (key, value, updated_at)
                    VALUES ('daemon_paused', ?, ?)
                """, ('true' if paused else 'false', datetime.now().isoformat()))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error estableciendo estado del daemon: {e}")
            return False

    def get_pending_review_composites(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtener composites pendientes de revisión."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT c.*, v.title as original_title 
                    FROM composites c
                    LEFT JOIN videos v ON c.video_id = v.video_id
                    WHERE c.status = 'pending_review' OR c.status IS NULL OR c.status = 'ready'
                    ORDER BY c.created_at DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo composites pendientes: {e}")
            return []

    def get_approved_composites(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener composites aprobados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT c.*, v.title as original_title 
                    FROM composites c
                    LEFT JOIN videos v ON c.video_id = v.video_id
                    WHERE c.status = 'approved' AND c.uploaded = 0
                    ORDER BY c.created_at DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo composites aprobados: {e}")
            return []

    def approve_composite(self, clip_id: str, comment: str = "", scheduled_at: str = None, auto_approved: bool = False) -> bool:
        """Aprobar un composite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                update_sql = """
                    UPDATE composites 
                    SET status = 'approved', reviewed_at = ?, auto_approved = ?
                """
                params = [datetime.now().isoformat(), 1 if auto_approved else 0]
                
                if comment:
                    update_sql += ", review_comment = ?"
                    params.append(comment)
                
                if scheduled_at:
                    update_sql += ", scheduled_publish_at = ?"
                    params.append(scheduled_at)
                
                update_sql += " WHERE clip_id = ?"
                params.append(clip_id)
                
                conn.execute(update_sql, params)
                return True
        except sqlite3.Error as e:
            logger.error(f"Error aprobando composite {clip_id}: {e}")
            return False

    def auto_approve_quality_clips(self, min_score: float = 0.7) -> int:
        """Auto-aprobar clips de alta calidad."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Buscar clips pendientes con alta puntuación
                cursor = conn.execute("""
                    SELECT clip_id FROM composites 
                    WHERE (status = 'pending_review' OR status IS NULL)
                    AND (quality_score >= ? OR engagement_score >= ?)
                    AND created_at < datetime('now', '-1 hour')
                    LIMIT 10
                """, (min_score, min_score))
                
                clips_to_approve = [row[0] for row in cursor.fetchall()]
                approved_count = 0
                
                for clip_id in clips_to_approve:
                    if self.approve_composite(clip_id, "Auto-approved: High quality score", auto_approved=True):
                        approved_count += 1
                        logger.info(f"Auto-aprobado clip {clip_id}")
                
                return approved_count
        except sqlite3.Error as e:
            logger.error(f"Error en auto-aprobación: {e}")
            return 0

    def get_next_scheduled_clip(self) -> Dict[str, Any]:
        """Obtener el próximo clip programado para publicar."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT c.*, v.title as original_title 
                    FROM composites c
                    LEFT JOIN videos v ON c.video_id = v.video_id
                    WHERE c.status = 'approved' 
                    AND c.uploaded = 0
                    AND (c.scheduled_publish_at IS NULL OR c.scheduled_publish_at <= datetime('now'))
                    ORDER BY c.priority DESC, c.created_at ASC
                    LIMIT 1
                """)
                row = cursor.fetchone()
                return dict(row) if row else {}
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo próximo clip programado: {e}")
            return {}

    def can_publish_now(self, hours_between_posts: int = 4, max_posts_per_day: int = 3) -> bool:
        """Verificar si se puede publicar ahora según las reglas de espaciado."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Verificar última publicación
                cursor = conn.execute("""
                    SELECT uploaded_at FROM composites 
                    WHERE uploaded = 1 
                    ORDER BY uploaded_at DESC 
                    LIMIT 1
                """)
                last_post = cursor.fetchone()
                
                if last_post:
                    last_time = datetime.fromisoformat(last_post[0])
                    time_diff = datetime.now() - last_time
                    if time_diff.total_seconds() < hours_between_posts * 3600:
                        return False
                
                # Verificar posts del día
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM composites 
                    WHERE uploaded = 1 
                    AND date(uploaded_at) = date('now')
                """)
                posts_today = cursor.fetchone()[0]
                
                return posts_today < max_posts_per_day
        except sqlite3.Error as e:
            logger.error(f"Error verificando si se puede publicar: {e}")
            return False

    def mark_as_published(self, clip_id: str, youtube_url: str = "") -> bool:
        """Marcar un composite como publicado."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE composites 
                    SET uploaded = 1, uploaded_at = ?, youtube_url = ?
                    WHERE clip_id = ?
                """, (datetime.now().isoformat(), youtube_url, clip_id))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error marcando como publicado {clip_id}: {e}")
            return False

    def reject_composite(self, clip_id: str, reason: str = "") -> bool:
        """Rechazar un composite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE composites 
                    SET status = 'rejected', reviewed_at = ?, rejection_reason = ?
                    WHERE clip_id = ?
                """, (datetime.now().isoformat(), reason, clip_id))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error rechazando composite {clip_id}: {e}")
            return False

    def get_all_channels(self) -> List[Dict[str, Any]]:
        """Obtener todos los canales."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT 
                        c.*,
                        COUNT(v.video_id) as total_videos,
                        COUNT(CASE WHEN v.processed = 1 THEN 1 END) as processed_videos,
                        MAX(v.discovered_at) as last_video_discovery
                    FROM channels c
                    LEFT JOIN videos v ON c.channel_id = v.channel_id
                    GROUP BY c.channel_id
                    ORDER BY c.name
                """)
                results = []
                for row in cursor.fetchall():
                    channel_dict = dict(row)
                    # Agregar campos adicionales esperados por la interfaz
                    channel_dict['is_active'] = bool(channel_dict.get('enabled', 1))
                    channel_dict['subscriber_count'] = channel_dict.get('subscriber_count', 0)
                    channel_dict['description'] = channel_dict.get('description', '')
                    channel_dict['url'] = channel_dict.get('url', f"https://www.youtube.com/channel/{channel_dict['channel_id']}")
                    channel_dict['discovered_at'] = channel_dict.get('last_checked', '')
                    results.append(channel_dict)
                return results
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo canales: {e}")
            return []

    def add_channel_manually(self, channel_id: str, channel_name: str, channel_url: str = "", 
                           description: str = "", subscriber_count: int = 0) -> bool:
        """Añadir canal manualmente."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Primero verificar si ya existe
                cursor = conn.execute("SELECT 1 FROM channels WHERE channel_id = ?", (channel_id,))
                if cursor.fetchone():
                    return False  # Ya existe
                
                # Agregar columnas si no existen
                try:
                    conn.execute("ALTER TABLE channels ADD COLUMN description TEXT")
                except sqlite3.OperationalError:
                    pass  # Columna ya existe
                
                try:
                    conn.execute("ALTER TABLE channels ADD COLUMN url TEXT")
                except sqlite3.OperationalError:
                    pass  # Columna ya existe
                
                try:
                    conn.execute("ALTER TABLE channels ADD COLUMN subscriber_count INTEGER DEFAULT 0")
                except sqlite3.OperationalError:
                    pass  # Columna ya existe
                
                conn.execute("""
                    INSERT INTO channels (channel_id, name, description, url, subscriber_count, enabled, last_checked)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """, (channel_id, channel_name, description, channel_url, subscriber_count, datetime.now().isoformat()))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error añadiendo canal {channel_id}: {e}")
            return False

    def get_videos_by_channel(self, channel_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtener videos de un canal."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT v.*, c.name as channel_name
                    FROM videos v
                    LEFT JOIN channels c ON v.channel_id = c.channel_id
                    WHERE v.channel_id = ?
                    ORDER BY v.published_at DESC
                    LIMIT ?
                """, (channel_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo videos del canal {channel_id}: {e}")
            return []

    def add_video_manually(self, video_id: str, channel_id: str, title: str, url: str = "", duration_seconds: int = 0) -> bool:
        """Añadir video manualmente."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Verificar si ya existe
                cursor = conn.execute("SELECT 1 FROM videos WHERE video_id = ?", (video_id,))
                if cursor.fetchone():
                    return False  # Ya existe
                
                conn.execute("""
                    INSERT INTO videos (video_id, channel_id, title, description, published_at, 
                                      duration_seconds, discovered_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'manual')
                """, (video_id, channel_id, title, f"Manual: {url}", 
                     datetime.now().isoformat(), duration_seconds, 
                     datetime.now().isoformat()))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error añadiendo video {video_id}: {e}")
            return False

    def delete_channel(self, channel_id: str) -> bool:
        """Eliminar canal."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error eliminando canal {channel_id}: {e}")
            return False
