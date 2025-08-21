#!/usr/bin/env python3
"""
🤖 Pipeline Daemon - Automatización completa del proceso
Ejecuta el pipeline completo de forma automática con auto-publicación
"""

import time
import schedule
import logging
from datetime import datetime
import sys
import os
from pathlib import Path

# Añadir el directorio src al path
sys.path.append('src')

from pipeline.db import PipelineDB
from pipeline.auto_publisher import AutoPublisher

class PipelineDaemon:
    def __init__(self):
        self.db = PipelineDB()
        
        # Cargar configuración
        self.config = self.load_config()
        
        # Inicializar auto-publisher
        self.auto_publisher = AutoPublisher(self.db, self.config)
        
        # Configurar logging
        log_file = self.config.get('LOG_FILE', 'data/logs/daemon.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_config(self):
        """Cargar configuración desde variables de entorno"""
        config = {}
        
        # Cargar todas las variables de entorno
        for key, value in os.environ.items():
            config[key] = value
        
        # Si no hay variables, cargar desde .env
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key] = value
        
        return config
        
    def run_discovery(self):
        """Ejecutar descubrimiento de nuevos videos"""
        try:
            self.logger.info("🔍 Iniciando descubrimiento de videos...")
            # Por ahora, solo simulamos el descubrimiento
            # En una implementación completa, aquí iría la integración con YouTube API
            discovered = []  # self.discoverer.discover_new_videos()
            self.logger.info(f"✅ Descubiertos {len(discovered)} videos nuevos")
            return discovered
        except Exception as e:
            self.logger.error(f"❌ Error en descubrimiento: {e}")
            return []
    
    def run_download(self):
        """Descargar videos pendientes"""
        try:
            self.logger.info("📥 Iniciando descarga de videos...")
            # Simulación de descarga
            downloaded = 0
            self.logger.info(f"✅ Descargados {downloaded} videos")
            return downloaded
        except Exception as e:
            self.logger.error(f"❌ Error en descarga: {e}")
            return 0
    
    def run_transcription(self):
        """Transcribir videos descargados"""
        try:
            self.logger.info("🎤 Iniciando transcripción...")
            # Simulación de transcripción
            transcribed = 0
            self.logger.info(f"✅ Transcritos {transcribed} videos")
            return transcribed
        except Exception as e:
            self.logger.error(f"❌ Error en transcripción: {e}")
            return 0
    
    def run_segmentation(self):
        """Segmentar transcripciones en clips"""
        try:
            self.logger.info("✂️ Iniciando segmentación...")
            # Simulación de segmentación
            segmented = 0
            self.logger.info(f"✅ Creados {segmented} segmentos")
            return segmented
        except Exception as e:
            self.logger.error(f"❌ Error en segmentación: {e}")
            return 0
    
    def run_composition(self):
        """Componer shorts finales"""
        try:
            self.logger.info("🎬 Iniciando composición...")
            # Simulación de composición
            composed = 0
            self.logger.info(f"✅ Compuestos {composed} shorts")
            return composed
        except Exception as e:
            self.logger.error(f"❌ Error en composición: {e}")
            return 0
    
    def run_auto_approval(self):
        """Aprobar automáticamente shorts con score alto"""
        try:
            self.logger.info("🤖 Revisando shorts para aprobación automática...")
            # Simulación de aprobación automática
            auto_approved = 0
            if auto_approved > 0:
                self.logger.info(f"✅ Auto-aprobados {auto_approved} shorts")
            return auto_approved
        except Exception as e:
            self.logger.error(f"❌ Error en aprobación automática: {e}")
            return 0
    
    def run_publishing(self):
        """Publicar shorts aprobados"""
        try:
            if not os.getenv('AUTO_PUBLISH_ENABLED', 'false').lower() == 'true':
                return 0
                
            self.logger.info("📤 Iniciando publicación...")
            # Simulación de publicación
            published = 0
            self.logger.info(f"✅ Publicados {published} shorts")
            return published
        except Exception as e:
            self.logger.error(f"❌ Error en publicación: {e}")
            return 0
    
    def run_complete_pipeline(self):
        """Ejecutar el pipeline completo incluyendo auto-publicación"""
        try:
            self.logger.info("🚀 Iniciando pipeline completo...")
            start_time = datetime.now()
            
            stats = {
                'discovered': [],
                'downloaded': 0,
                'transcribed': 0,
                'segmented': 0,
                'composed': 0,
                'auto_approved': 0,
                'published': 0
            }
            
            # 1. Descubrimiento
            discovered = self.run_discovery()
            stats['discovered'] = discovered
            
            # 2. Descarga
            downloaded = self.run_download()
            stats['downloaded'] = downloaded
            
            # 3. Transcripción
            transcribed = self.run_transcription()
            stats['transcribed'] = transcribed
            
            # 4. Segmentación
            segmented = self.run_segmentation()
            stats['segmented'] = segmented
            
            # 5. Composición
            composed = self.run_composition()
            stats['composed'] = composed
            
            # 6. AUTO-APROBACIÓN (NUEVA FUNCIONALIDAD)
            if self.config.get('AUTO_APPROVE_ENABLED', False):
                auto_approved = self.auto_publisher.auto_approve_clips()
                stats['auto_approved'] = auto_approved
                self.logger.info(f"🎯 Auto-aprobados: {auto_approved} clips")
            
            # 7. AUTO-PUBLICACIÓN (NUEVA FUNCIONALIDAD)
            if self.config.get('PUBLISH_ENABLED', False):
                try:
                    published = self.auto_publisher.publish_next_clip()
                    stats['published'] = 1 if published else 0
                    if published:
                        self.logger.info("📺 ¡Clip publicado automáticamente!")
                    else:
                        self.logger.info("⏰ No es momento de publicar")
                except Exception as e:
                    self.logger.error(f"❌ Error en auto-publicación: {e}")
            
            # 8. Limpieza automática
            if self.config.get('AUTO_CLEANUP_ENABLED', False):
                self.auto_publisher.cleanup_old_files()
            
            duration = datetime.now() - start_time
            self.logger.info(f"✅ Pipeline completado en {duration}")
            self.logger.info(f"📊 Estadísticas: {stats}")
            
            # Guardar estadísticas
            self.save_pipeline_run_stats(stats, duration)
            
        except Exception as e:
            self.logger.error(f"❌ Error en pipeline completo: {e}")
            raise
    
    def run_publishing_only(self):
        """Ejecutar solo el ciclo de publicación (más frecuente)"""
        try:
            self.logger.info("📺 Ejecutando ciclo de publicación...")
            self.auto_publisher.run_publishing_cycle()
        except Exception as e:
            self.logger.error(f"❌ Error en ciclo de publicación: {e}")
    
    def setup_schedule(self):
        """Configurar horarios automáticos"""
        
        # Pipeline completo cada X horas
        discovery_interval = int(self.config.get('DISCOVERY_INTERVAL_HOURS', 6))
        schedule.every(discovery_interval).hours.do(self.run_complete_pipeline)
        
        # Publicación cada 30 minutos
        publish_interval = int(self.config.get('DAEMON_INTERVAL_MINUTES', 30))
        schedule.every(publish_interval).minutes.do(self.run_publishing_only)
        
        # Horarios específicos de publicación
        publish_times = self.config.get('PUBLISH_TIMES', '10:00,15:00,20:00').split(',')
        for pub_time in publish_times:
            pub_time = pub_time.strip()
            schedule.every().day.at(pub_time).do(self.run_publishing_only)
        
        self.logger.info(f"📅 Horarios configurados:")
        self.logger.info(f"   - Pipeline completo: cada {discovery_interval} horas")
        self.logger.info(f"   - Publicación: cada {publish_interval} minutos")
        self.logger.info(f"   - Horarios específicos: {publish_times}")
    
    def run_daemon(self):
        """Ejecutar daemon principal"""
        self.logger.info("🤖 Iniciando Pipeline Daemon con Auto-Publicación...")
        
        if not self.config.get('DAEMON_ENABLED', True):
            self.logger.warning("⚠️ Daemon deshabilitado en configuración")
            return
        
        # Configurar horarios
        self.setup_schedule()
        
        # Ejecutar una vez al inicio
        self.run_complete_pipeline()
        
        self.logger.info("⏰ Daemon iniciado, esperando próxima ejecución...")
        
        # Loop principal
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verificar cada minuto
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Daemon detenido por usuario")
        except Exception as e:
            self.logger.error(f"❌ Error fatal en daemon: {e}")
            raise
    
    def start(self):
        """Iniciar el daemon con programación"""
        self.logger.info("🤖 Iniciando Pipeline Daemon")
        
        # Programar tareas
        schedule.every(30).minutes.do(self.run_full_pipeline)
        schedule.every().hour.at(":00").do(self.run_discovery)
        schedule.every(2).hours.do(self.run_auto_approval)
        
        # Ejecutar una vez al inicio
        self.run_full_pipeline()
        
        self.logger.info("⏰ Daemon iniciado, esperando próxima ejecución...")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Revisar cada minuto
        except KeyboardInterrupt:
            self.logger.info("🛑 Deteniendo daemon...")
        except Exception as e:
            self.logger.error(f"❌ Error en daemon: {e}")
            raise

if __name__ == "__main__":
    daemon = PipelineDaemon()
    daemon.start()
