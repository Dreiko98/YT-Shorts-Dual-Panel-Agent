"""
Auto Publisher - Módulo de publicación automática para YouTube Shorts
"""

import os
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
from pathlib import Path

# Simulación de la API de YouTube (reemplazar con implementación real)
class YouTubeUploader:
    def __init__(self, client_id: str, client_secret: str, api_key: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self.authenticated = False
        logger.info("YouTube Uploader inicializado")
    
    def authenticate(self) -> bool:
        """Autenticar con YouTube API"""
        try:
            # Aquí iría la lógica real de autenticación OAuth2
            # Por ahora simulamos autenticación exitosa
            logger.info("✅ Autenticación con YouTube API exitosa")
            self.authenticated = True
            return True
        except Exception as e:
            logger.error(f"❌ Error en autenticación YouTube: {e}")
            return False
    
    def upload_video(self, video_path: str, title: str, description: str, tags: list = None) -> Optional[str]:
        """Subir video a YouTube y retornar URL"""
        if not self.authenticated:
            logger.error("❌ No autenticado con YouTube API")
            return None
        
        try:
            # Simulación de subida (reemplazar con API real)
            logger.info(f"📤 Subiendo video: {title}")
            logger.info(f"📁 Archivo: {video_path}")
            logger.info(f"📝 Descripción: {description[:100]}...")
            
            # Simular tiempo de subida
            time.sleep(2)
            
            # URL simulada (reemplazar con URL real de YouTube)
            video_url = f"https://youtube.com/shorts/sim_{int(time.time())}"
            logger.info(f"✅ Video subido exitosamente: {video_url}")
            
            return video_url
            
        except Exception as e:
            logger.error(f"❌ Error subiendo video: {e}")
            return None


class AutoPublisher:
    def __init__(self, db, config: Dict[str, Any]):
        self.db = db
        self.config = config
        self.youtube = None
        self.setup_youtube_api()
        
    def setup_youtube_api(self):
        """Configurar YouTube API"""
        try:
            client_id = self.config.get('YOUTUBE_CLIENT_ID')
            client_secret = self.config.get('YOUTUBE_CLIENT_SECRET')
            api_key = self.config.get('YOUTUBE_API_KEY')
            
            if all([client_id, client_secret, api_key]):
                self.youtube = YouTubeUploader(client_id, client_secret, api_key)
                if self.youtube.authenticate():
                    logger.info("🔗 YouTube API configurado correctamente")
                else:
                    logger.error("❌ Error configurando YouTube API")
            else:
                logger.error("❌ Credenciales de YouTube incompletas")
                
        except Exception as e:
            logger.error(f"❌ Error configurando YouTube API: {e}")
    
    def should_publish_now(self) -> bool:
        """Verificar si es hora de publicar"""
        if not self.config.get('PUBLISH_ENABLED', False):
            return False
        
        # Verificar horarios permitidos
        publish_times = self.config.get('PUBLISH_TIMES', '10:00,15:00,20:00').split(',')
        current_time = datetime.now().strftime('%H:%M')
        
        # Permitir publicación dentro de 30 minutos de los horarios programados
        for pub_time in publish_times:
            pub_time = pub_time.strip()
            try:
                pub_datetime = datetime.strptime(pub_time, '%H:%M')
                current_datetime = datetime.strptime(current_time, '%H:%M')
                
                time_diff = abs((current_datetime - pub_datetime).total_seconds())
                if time_diff <= 1800:  # 30 minutos
                    # Verificar espaciado entre posts
                    hours_between = int(self.config.get('MIN_TIME_BETWEEN_POSTS_HOURS', 4))
                    max_per_day = int(self.config.get('MAX_POSTS_PER_DAY', 3))
                    
                    return self.db.can_publish_now(hours_between, max_per_day)
                    
            except ValueError:
                continue
                
        return False
    
    def auto_approve_clips(self) -> int:
        """Auto-aprobar clips de calidad"""
        if not self.config.get('AUTO_APPROVE_ENABLED', False):
            return 0
        
        min_score = float(self.config.get('MIN_ENGAGEMENT_SCORE', 0.7))
        approved = self.db.auto_approve_quality_clips(min_score)
        
        if approved > 0:
            logger.info(f"🎯 Auto-aprobados {approved} clips de alta calidad")
        
        return approved
    
    def generate_title_and_description(self, clip_data: Dict[str, Any]) -> tuple:
        """Generar título y descripción atractivos"""
        original_title = clip_data.get('original_title', 'Video')
        segment_text = clip_data.get('segment_text', '')[:200]
        
        # Título atractivo (máx 100 caracteres para YouTube)
        title = f"🔥 {original_title[:50]}... #Shorts"
        
        # Descripción con hashtags
        description = f"""
{segment_text}

🎯 ¡No te pierdas más contenido como este!
👆 Dale LIKE si te gustó
🔔 SUSCRÍBETE para más

#Shorts #YouTube #Viral #Content #Trending
#Podcast #Clips #Highlights #Motivation

📱 Síguenos para más contenido increíble
        """.strip()
        
        return title, description
    
    def publish_next_clip(self) -> bool:
        """Publicar el próximo clip programado"""
        if not self.youtube or not self.should_publish_now():
            return False
        
        # Obtener próximo clip
        clip_data = self.db.get_next_scheduled_clip()
        if not clip_data:
            logger.info("📭 No hay clips listos para publicar")
            return False
        
        clip_id = clip_data['clip_id']
        video_path = clip_data.get('output_path')
        
        if not video_path or not os.path.exists(video_path):
            logger.error(f"❌ Archivo de video no encontrado: {video_path}")
            return False
        
        # Generar contenido
        title, description = self.generate_title_and_description(clip_data)
        
        # Subir a YouTube
        logger.info(f"🚀 Publicando clip: {clip_id}")
        youtube_url = self.youtube.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=['shorts', 'viral', 'podcast', 'clips']
        )
        
        if youtube_url:
            # Marcar como publicado en BD
            self.db.mark_as_published(clip_id, youtube_url)
            logger.info(f"✅ Clip {clip_id} publicado: {youtube_url}")
            
            # Enviar notificación si está configurada
            self.send_notification(f"📺 Nuevo video publicado: {title}\n🔗 {youtube_url}")
            
            return True
        else:
            logger.error(f"❌ Error publicando clip {clip_id}")
            return False
    
    def send_notification(self, message: str):
        """Enviar notificación (Telegram, etc.)"""
        if self.config.get('TELEGRAM_NOTIFICATIONS', False):
            # Implementar notificación Telegram
            logger.info(f"📱 Notificación: {message}")
        
    def cleanup_old_files(self):
        """Limpiar archivos antiguos"""
        if not self.config.get('AUTO_CLEANUP_ENABLED', False):
            return
        
        max_storage_gb = float(self.config.get('MAX_STORAGE_GB', 50))
        # Implementar lógica de limpieza
        logger.info(f"🧹 Limpieza automática (máx {max_storage_gb}GB)")
    
    def run_publishing_cycle(self):
        """Ejecutar ciclo completo de publicación"""
        try:
            logger.info("🔄 Iniciando ciclo de publicación automática")
            
            # 1. Auto-aprobar clips de calidad
            approved = self.auto_approve_clips()
            
            # 2. Publicar si es hora
            if self.should_publish_now():
                published = self.publish_next_clip()
                if not published:
                    logger.info("⏳ No se publicó nada en este ciclo")
            else:
                logger.info("⏰ Fuera del horario de publicación")
            
            # 3. Limpieza
            self.cleanup_old_files()
            
            logger.info("✅ Ciclo de publicación completado")
            
        except Exception as e:
            logger.error(f"❌ Error en ciclo de publicación: {e}")


# Configurar logging
logger = logging.getLogger(__name__)
