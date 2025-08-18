#!/usr/bin/env python3
"""
🤖 Pipeline Daemon - Automatización completa del proceso
Ejecuta el pipeline completo de forma automática
"""

import time
import schedule
import logging
from datetime import datetime
import sys
import os

# Añadir el directorio src al path
sys.path.append('src')

from pipeline.db import PipelineDB

class PipelineDaemon:
    def __init__(self):
        self.db = PipelineDB()
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/daemon.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
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
    
    def run_full_pipeline(self):
        """Ejecutar el pipeline completo"""
        self.logger.info("🚀 Iniciando ejecución completa del pipeline")
        start_time = datetime.now()
        
        # Verificar si el daemon está pausado
        if self.db.is_daemon_paused():
            self.logger.info("⏸️ Daemon pausado, saltando ejecución")
            return
        
        stats = {
            'discovered': self.run_discovery(),
            'downloaded': self.run_download(),
            'transcribed': self.run_transcription(),
            'segmented': self.run_segmentation(),
            'composed': self.run_composition(),
            'auto_approved': self.run_auto_approval(),
            'published': self.run_publishing()
        }
        
        duration = datetime.now() - start_time
        self.logger.info(f"✅ Pipeline completado en {duration}")
        self.logger.info(f"📊 Estadísticas: {stats}")
        
        # Guardar estadísticas en la base de datos si el método existe
        try:
            self.db.save_pipeline_run_stats(stats, duration.total_seconds())
        except AttributeError:
            # El método no existe aún, solo logueamos
            self.logger.info("📝 Método save_pipeline_run_stats no implementado aún")
    
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
