#!/usr/bin/env python3
"""
🤖 YT Shorts CLI Control Interface
Interfaz de línea de comandos para controlar el pipeline sin Telegram
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from pathlib import Path

# Añadir src al path para imports
sys.path.append('src')

try:
    from pipeline.db import PipelineDB
    from pipeline.content_scorer import ContentScorer
    from pipeline.template_manager import TemplateManager
    from datetime import timedelta
    # Import condicional del parser
    try:
        from utils.youtube_parser import YouTubeURLParser, parse_youtube_url
        YOUTUBE_PARSER_AVAILABLE = False  # Forzar modo manual para demo
    except ImportError:
        YOUTUBE_PARSER_AVAILABLE = False
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de ejecutar desde el directorio raíz del proyecto")
    sys.exit(1)

def format_duration(seconds):
    """Formatear duración en formato legible"""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs = seconds % 60
    if secs:
        return f"{minutes}m {secs}s"
    return f"{minutes}m"

class CLIControl:
    def __init__(self):
        self.db = PipelineDB()
        self.scorer = ContentScorer()
        self.template_manager = TemplateManager()
        
        # Inicializar parser de YouTube si está disponible
        if YOUTUBE_PARSER_AVAILABLE:
            self.youtube_parser = YouTubeURLParser()
        else:
            self.youtube_parser = None
            
        self.running = True
    
    def show_banner(self):
        """Mostrar banner de bienvenida"""
        print("="*80)
        print("💻 YT SHORTS PIPELINE - CONTROL CLI")
        print("🔧 Interfaz temporal mientras recuperas acceso a Telegram")
        print("="*80)
    
    def show_menu(self):
        """Mostrar menú principal"""
        print("\n📋 MENÚ PRINCIPAL:")
        print("1️⃣  📊 Ver estado y estadísticas")
        print("2️⃣  🔄 Ver cola de shorts pendientes") 
        print("3️⃣  ✅ Aprobar short específico")
        print("4️⃣  ❌ Rechazar short específico")
        print("5️⃣  📅 Programar publicación")
        print("6️⃣  📦 Operaciones en lote")
        print("7️⃣  ⏸️  Pausar/Reanudar daemon")
        print("8️⃣  📤 Publicar shorts aprobados")
        print("9️⃣  📝 Ver información del sistema")
        print("🎯  🤖 Ejecutar scoring automático")
        print("🎨  🎬 Gestionar templates")
        print("📺  📋 Gestionar canales y videos")
        print("0️⃣  🚪 Salir")
        print("-"*50)
    
    def show_stats(self):
        """Mostrar estadísticas del sistema"""
        print("\n📊 ESTADÍSTICAS DEL SISTEMA")
        print("-"*40)
        
        # Estadísticas de colas
        queue_stats = self.db.get_queue_stats()
        print(f"🔄 Pendientes de revisión: {queue_stats['pending_review']}")
        print(f"✅ Aprobados para publicar: {queue_stats['approved']}")
        print(f"❌ Rechazados: {queue_stats['rejected']}")
        print(f"📤 Publicados: {queue_stats['published']}")
        
        # Estado del daemon
        daemon_paused = self.db.is_daemon_paused()
        status = "⏸️  PAUSADO" if daemon_paused else "▶️  EJECUTÁNDOSE"
        print(f"🤖 Estado del daemon: {status}")
        
        # Estadísticas generales
        try:
            general_stats = self.db.get_stats()
            print(f"📺 Total videos procesados: {general_stats.get('total_videos', 0)}")
            print(f"🎬 Total shorts generados: {general_stats.get('composites', 0)}")
        except:
            print("📊 Estadísticas generales no disponibles")
        
        # Métricas calculadas
        total_reviewed = queue_stats['approved'] + queue_stats['rejected']
        if total_reviewed > 0:
            approval_rate = queue_stats['approved'] / total_reviewed * 100
            print(f"📈 Tasa de aprobación: {approval_rate:.1f}%")
    
    def show_pending_queue(self):
        """Mostrar cola de shorts pendientes"""
        print("\n🔄 COLA DE SHORTS PENDIENTES")
        print("-"*40)
        
        pending = self.db.get_pending_review_composites(limit=20)
        
        if not pending:
            print("📭 No hay shorts pendientes de revisión")
            return
        
        for i, short in enumerate(pending, 1):
            print(f"\n{i}. 📱 ID: {short['clip_id'][:16]}...")
            
            # Obtener detalles completos
            details = self.db.get_composite_details(short['clip_id'])
            if details:
                title = details.get('original_title', 'Sin título')
                print(f"   📝 Título: {title[:60]}{'...' if len(title) > 60 else ''}")
                print(f"   ⏱️  Duración: {details.get('duration_seconds', 0):.1f}s")
                print(f"   📅 Creado: {details.get('created_at', 'N/A')[:16]}")
                
                # Mostrar path del archivo si existe
                if details.get('output_path'):
                    file_path = Path(details['output_path'])
                    if file_path.exists():
                        size_mb = file_path.stat().st_size / (1024*1024)
                        print(f"   📁 Archivo: {file_path.name} ({size_mb:.1f}MB)")
                    else:
                        print(f"   ⚠️  Archivo no encontrado: {file_path.name}")
            else:
                print(f"   📅 Creado: {short.get('created_at', 'N/A')[:16]}")
    
    def approve_short(self):
        """Aprobar un short específico"""
        self.show_pending_queue()
        if not self.db.get_pending_review_composites(limit=1):
            return
        
        clip_id = input("\n✅ Ingresa el ID del short a aprobar (o Enter para cancelar): ").strip()
        if not clip_id:
            return
        
        comment = input("💬 Comentario (opcional): ").strip()
        
        if self.db.approve_composite(clip_id, comment=comment or "Aprobado vía CLI"):
            print(f"✅ Short {clip_id[:16]} aprobado exitosamente")
        else:
            print(f"❌ Error aprobando short {clip_id}")
    
    def reject_short(self):
        """Rechazar un short específico"""
        self.show_pending_queue()
        if not self.db.get_pending_review_composites(limit=1):
            return
        
        clip_id = input("\n❌ Ingresa el ID del short a rechazar (o Enter para cancelar): ").strip()
        if not clip_id:
            return
        
        reason = input("💬 Motivo del rechazo: ").strip()
        if not reason:
            reason = "Rechazado vía CLI"
        
        if self.db.reject_composite(clip_id, reason=reason):
            print(f"❌ Short {clip_id[:16]} rechazado exitosamente")
        else:
            print(f"❌ Error rechazando short {clip_id}")
    
    def schedule_short(self):
        """Programar publicación de un short"""
        self.show_pending_queue()
        if not self.db.get_pending_review_composites(limit=1):
            return
        
        clip_id = input("\n📅 Ingresa el ID del short a programar (o Enter para cancelar): ").strip()
        if not clip_id:
            return
        
        print("\n📅 Formatos de fecha aceptados:")
        print("   • 2024-08-19T18:00 (fecha específica)")
        print("   • +2h (en 2 horas)")  
        print("   • +30m (en 30 minutos)")
        
        time_input = input("⏰ Hora de publicación: ").strip()
        if not time_input:
            return
        
        # Parsear tiempo
        scheduled_at = self.parse_time(time_input)
        if not scheduled_at:
            print("❌ Formato de fecha inválido")
            return
        
        if self.db.approve_composite(clip_id, scheduled_at=scheduled_at, comment="Programado vía CLI"):
            print(f"📅 Short {clip_id[:16]} programado para {scheduled_at}")
        else:
            print(f"❌ Error programando short {clip_id}")
    
    def parse_time(self, time_input):
        """Parsear entrada de tiempo"""
        try:
            # Formato ISO directo
            if 'T' in time_input:
                datetime.fromisoformat(time_input)
                return time_input
            
            # Formato relativo
            if time_input.startswith('+'):
                import re
                match = re.match(r'\+(\d+)([hm])', time_input.lower())
                if match:
                    amount = int(match.group(1))
                    unit = match.group(2)
                    
                    if unit == 'h':
                        target = datetime.now() + timedelta(hours=amount)
                    else:  # 'm'
                        target = datetime.now() + timedelta(minutes=amount)
                    
                    return target.isoformat()
            
            return None
        except:
            return None
    
    def bulk_operations(self):
        """Menú de operaciones en lote"""
        print("\n📦 OPERACIONES EN LOTE")
        print("-"*30)
        print("1. ✅ Aprobar todos los pendientes")
        print("2. ❌ Rechazar todos los pendientes") 
        print("3. ✅ Aprobar primeros N")
        print("4. ❌ Rechazar primeros N")
        print("5. 📊 Estadísticas detalladas")
        print("0. 🔙 Volver")
        
        choice = input("\n👉 Selecciona opción: ").strip()
        
        if choice == '1':
            self.bulk_approve_all()
        elif choice == '2':
            self.bulk_reject_all()
        elif choice == '3':
            self.bulk_approve_n()
        elif choice == '4':
            self.bulk_reject_n()
        elif choice == '5':
            self.detailed_stats()
    
    def bulk_approve_all(self):
        """Aprobar todos los pendientes"""
        pending = self.db.get_pending_review_composites(limit=50)
        if not pending:
            print("📭 No hay shorts pendientes")
            return
        
        confirm = input(f"⚠️  ¿Aprobar TODOS los {len(pending)} shorts pendientes? (s/N): ")
        if confirm.lower() != 's':
            return
        
        count = 0
        for short in pending:
            if self.db.approve_composite(short['clip_id'], comment="Aprobación masiva vía CLI"):
                count += 1
        
        print(f"✅ {count}/{len(pending)} shorts aprobados en lote")
    
    def bulk_reject_all(self):
        """Rechazar todos los pendientes"""
        pending = self.db.get_pending_review_composites(limit=50)
        if not pending:
            print("📭 No hay shorts pendientes")
            return
        
        reason = input("💬 Motivo del rechazo masivo: ").strip()
        if not reason:
            reason = "Rechazo masivo vía CLI"
        
        confirm = input(f"⚠️  ¿Rechazar TODOS los {len(pending)} shorts pendientes? (s/N): ")
        if confirm.lower() != 's':
            return
        
        count = 0
        for short in pending:
            if self.db.reject_composite(short['clip_id'], reason=reason):
                count += 1
        
        print(f"❌ {count}/{len(pending)} shorts rechazados en lote")
    
    def bulk_approve_n(self):
        """Aprobar primeros N shorts"""
        n = input("📝 ¿Cuántos shorts aprobar?: ")
        try:
            n = int(n)
        except ValueError:
            print("❌ Número inválido")
            return
        
        pending = self.db.get_pending_review_composites(limit=n)
        if not pending:
            print("📭 No hay shorts pendientes")
            return
        
        count = 0
        for short in pending:
            if self.db.approve_composite(short['clip_id'], comment=f"Aprobación lote {n} vía CLI"):
                count += 1
        
        print(f"✅ {count}/{len(pending)} shorts aprobados")
    
    def bulk_reject_n(self):
        """Rechazar primeros N shorts"""
        n = input("📝 ¿Cuántos shorts rechazar?: ")
        try:
            n = int(n)
        except ValueError:
            print("❌ Número inválido")
            return
        
        reason = input("💬 Motivo del rechazo: ").strip()
        if not reason:
            reason = f"Rechazo lote {n} vía CLI"
        
        pending = self.db.get_pending_review_composites(limit=n)
        if not pending:
            print("📭 No hay shorts pendientes")
            return
        
        count = 0
        for short in pending:
            if self.db.reject_composite(short['clip_id'], reason=reason):
                count += 1
        
        print(f"❌ {count}/{len(pending)} shorts rechazados")
    
    def detailed_stats(self):
        """Mostrar estadísticas detalladas"""
        print("\n📊 ESTADÍSTICAS DETALLADAS")
        print("-"*50)
        
        queue_stats = self.db.get_queue_stats()
        
        print("🔄 Estado de las colas:")
        print(f"   • Pendientes: {queue_stats['pending_review']}")
        print(f"   • Aprobados: {queue_stats['approved']}")
        print(f"   • Rechazados: {queue_stats['rejected']}")
        print(f"   • Publicados: {queue_stats['published']}")
        
        # Métricas calculadas
        total_shorts = sum(queue_stats.values())
        total_reviewed = queue_stats['approved'] + queue_stats['rejected']
        
        print(f"\n📈 Métricas:")
        print(f"   • Total shorts: {total_shorts}")
        print(f"   • Total revisados: {total_reviewed}")
        
        if total_reviewed > 0:
            approval_rate = queue_stats['approved'] / total_reviewed * 100
            print(f"   • Tasa aprobación: {approval_rate:.1f}%")
        
        if total_shorts > 0:
            publish_rate = queue_stats['published'] / total_shorts * 100
            print(f"   • Tasa publicación: {publish_rate:.1f}%")
    
    def toggle_daemon(self):
        """Pausar/reanudar daemon"""
        current_state = self.db.is_daemon_paused()
        action = "reanudar" if current_state else "pausar"
        
        confirm = input(f"⚠️  ¿{action.capitalize()} el daemon? (s/N): ")
        if confirm.lower() != 's':
            return
        
        new_state = not current_state
        if self.db.set_daemon_paused(new_state):
            status = "pausado" if new_state else "reanudado"
            print(f"🔄 Daemon {status} exitosamente")
        else:
            print("❌ Error cambiando estado del daemon")
    
    def publish_approved(self):
        """Publicar shorts aprobados"""
        approved = self.db.get_approved_composites(limit=10)
        if not approved:
            print("📭 No hay shorts aprobados para publicar")
            return
        
        print(f"📤 Hay {len(approved)} shorts aprobados para publicar")
        print("⚠️  Función de publicación requiere configuración completa de YouTube API")
        print("💡 Usa el daemon automático o configura el publisher para publicar")
    
    def show_system_info(self):
        """Mostrar información del sistema"""
        print("\n📝 INFORMACIÓN DEL SISTEMA")
        print("-"*40)
        
        # Info de la base de datos
        if Path('data/pipeline.db').exists():
            size_mb = Path('data/pipeline.db').stat().st_size / (1024*1024)
            print(f"💾 Base de datos: {size_mb:.2f}MB")
        
        # Archivos de log
        if Path('logs').exists():
            log_files = list(Path('logs').glob('*.log'))
            print(f"📝 Archivos de log: {len(log_files)}")
        
        # Estado de configuración
        config_files = ['configs/channels.yaml', '.env']
        for config in config_files:
            if Path(config).exists():
                print(f"✅ {config}")
            else:
                print(f"❌ {config} (no encontrado)")
        
        # Alternativas para usar el bot
        print(f"\n💡 ALTERNATIVAS MIENTRAS RECUPERAS TELEGRAM:")
        print(f"   • Esta interfaz CLI")
        print(f"   • Interfaz web: python web_interface.py (requiere Flask)")
        print(f"   • Scripts Python personalizados")
        print(f"   • Edición directa de la base de datos")
    
    def run_auto_scoring(self):
        """Ejecutar sistema de scoring automático"""
        print("\n🤖 SISTEMA DE SCORING AUTOMÁTICO")
        print("-" * 40)
        
        print("1. 🎯 Procesar shorts pendientes")
        print("2. 📊 Ver estadísticas de scoring")
        print("3. ⚙️ Configurar thresholds")
        print("4. 🔍 Analizar short específico")
        print("0. 🔙 Volver")
        
        choice = input("\n👉 Selecciona opción: ").strip()
        
        if choice == '1':
            self.process_pending_scoring()
        elif choice == '2':
            self.show_scoring_stats()
        elif choice == '3':
            self.configure_scoring_thresholds()
        elif choice == '4':
            self.analyze_specific_short()
    
    def process_pending_scoring(self):
        """Procesar shorts pendientes con scoring"""
        print("\n🔄 Procesando shorts pendientes...")
        
        try:
            results = self.scorer.process_pending_shorts()
            
            if not results['processed']:
                print("📭 No hay shorts pendientes para procesar")
                return
            
            print(f"✅ Procesados: {results['processed']} shorts")
            print(f"🎯 Auto-aprobados: {results['auto_approved']}")
            print(f"❌ Auto-rechazados: {results['auto_rejected']}")
            print(f"⏳ Requieren revisión manual: {results['needs_manual_review']}")
            
            if results['errors']:
                print(f"⚠️  Errores: {results['errors']}")
            
        except Exception as e:
            print(f"❌ Error procesando scoring: {e}")
    
    def show_scoring_stats(self):
        """Mostrar estadísticas del sistema de scoring"""
        print("\n📊 ESTADÍSTICAS DE SCORING")
        print("-" * 40)
        
        try:
            stats = self.scorer.get_scoring_stats()
            
            basic = stats.get('basic_stats', {})
            distribution = stats.get('score_distribution', {})
            thresholds = stats.get('threshold_stats', {})
            
            print("📈 Estadísticas Básicas:")
            print(f"   • Total evaluados: {basic.get('total_scored', 0)}")
            print(f"   • Score promedio: {basic.get('avg_score', 0):.1f}")
            print(f"   • Auto-rechazos elegibles: {basic.get('auto_rejected_eligible', 0)}")
            
            print("\n📊 Distribución de Scores:")
            for category, count in distribution.items():
                print(f"   • {category.title()}: {count}")
            
            if thresholds:
                print("\n⚙️  Estadísticas de Thresholds:")
                for threshold, count in thresholds.items():
                    print(f"   • {threshold}: {count}")
                    
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
    
    def configure_scoring_thresholds(self):
        """Configurar thresholds del sistema de scoring"""
        print("\n⚙️ CONFIGURAR THRESHOLDS DE SCORING")
        print("-" * 40)
        
        print("Thresholds actuales:")
        print(f"   • Auto-aprobar: ≥ 80 puntos")
        print(f"   • Auto-rechazar: < 40 puntos")
        print(f"   • Revisión manual: 40-79 puntos")
        
        print("\n⚠️  Modificación de thresholds requiere editar el código fuente")
        print("📁 Archivo: src/pipeline/content_scorer.py")
        print("📍 Líneas: auto_approve_threshold y auto_reject_threshold")
    
    def analyze_specific_short(self):
        """Analizar un short específico"""
        print("\n🔍 ANALIZAR SHORT ESPECÍFICO")
        print("-" * 40)
        
        clip_id = input("📄 Ingresa el clip_id del short: ").strip()
        
        if not clip_id:
            print("❌ Clip ID requerido")
            return
        
        try:
            # Buscar el short en la base de datos
            shorts = self.db.get_pending_review_composites()
            short = None
            
            for s in shorts:
                if s['clip_id'] == clip_id:
                    short = s
                    break
            
            if not short:
                print(f"❌ Short con ID '{clip_id}' no encontrado en pendientes")
                return
            
            # Analizar con el scorer
            print(f"🔍 Analizando '{short['title']}'...")
            
            score_details = self.scorer.calculate_score({
                'video_path': short.get('video_path', ''),
                'audio_path': short.get('audio_path', ''),
                'subtitles': short.get('subtitles', ''),
                'duration_seconds': short.get('duration_seconds', 30)
            })
            
            print(f"\n📊 Resultados del análisis:")
            print(f"   🎯 Score total: {score_details['total_score']}/100")
            print(f"   🔊 Calidad de audio: {score_details['audio_score']}/30")
            print(f"   ⏱️ Duración óptima: {score_details['duration_score']}/25")
            print(f"   📝 Subtítulos: {score_details['subtitles_score']}/25")
            print(f"   📹 Estabilidad visual: {score_details['video_score']}/20")
            
            # Mostrar recomendación
            if score_details['total_score'] >= 80:
                print(f"\n✅ Recomendación: AUTO-APROBAR")
            elif score_details['total_score'] < 40:
                print(f"\n❌ Recomendación: AUTO-RECHAZAR")
            else:
                print(f"\n⏳ Recomendación: REVISIÓN MANUAL")
                
        except Exception as e:
            print(f"❌ Error analizando short: {e}")
    
    def manage_templates(self):
        """Gestionar templates dinámicos"""
        print("\n🎨 GESTIÓN DE TEMPLATES DINÁMICOS")
        print("-" * 40)
        
        print("1. 📋 Listar templates disponibles")
        print("2. 👁️ Ver detalles de template")
        print("3. 🎯 Seleccionar template para contenido")
        print("4. ⚙️ Configurar templates")
        print("5. 🧪 Demo de selección automática")
        print("0. 🔙 Volver")
        
        choice = input("\n👉 Selecciona opción: ").strip()
        
        if choice == '1':
            self.list_templates()
        elif choice == '2':
            self.show_template_details()
        elif choice == '3':
            self.select_template_for_content()
        elif choice == '4':
            self.configure_templates()
        elif choice == '5':
            self.demo_template_selection()
    
    def list_templates(self):
        """Listar templates disponibles"""
        print("\n📋 TEMPLATES DISPONIBLES")
        print("-" * 40)
        
        try:
            templates = self.template_manager.list_templates_summary()
            
            if not templates:
                print("❌ No hay templates configurados")
                return
            
            for template in templates:
                status = "✅" if template['enabled'] else "❌"
                priority = template['priority']
                
                print(f"{status} {template['id']}:")
                print(f"   📝 {template['name']}")
                print(f"   💬 {template['description']}")
                print(f"   🎯 Prioridad: {priority}")
                print()
                
        except Exception as e:
            print(f"❌ Error listando templates: {e}")
    
    def show_template_details(self):
        """Mostrar detalles de un template específico"""
        print("\n👁️ DETALLES DE TEMPLATE")
        print("-" * 40)
        
        template_id = input("📄 Ingresa el ID del template: ").strip()
        
        if not template_id:
            print("❌ Template ID requerido")
            return
        
        try:
            details = self.template_manager.get_template_preview(template_id)
            
            if 'error' in details:
                print(f"❌ {details['error']}")
                return
            
            print(f"🎨 {details['name']}")
            print(f"💬 {details['description']}")
            print(f"🎯 Prioridad: {details['priority']}")
            print(f"📊 Estado: {'✅ Habilitado' if details['enabled'] else '❌ Deshabilitado'}")
            
            print(f"\n✨ Características:")
            features = details['features']
            print(f"   📝 Fondo en subtítulos: {'✅' if features['subtitle_background'] else '❌'}")
            print(f"   🏷️ Marca de agua: {'✅' if features['watermark'] else '❌'}")
            print(f"   🔊 Normalización de audio: {'✅' if features['audio_normalization'] else '❌'}")
            print(f"   🎬 Efectos de video: {', '.join(features['video_effects'])}")
            
            print(f"\n🎯 Vista previa del estilo:")
            style = details['style_preview']
            print(f"   🔤 Fuente: {style['font_family']}")
            print(f"   📏 Tamaño: {style['font_size']}px")
            print(f"   🎨 Color: {style['font_color']}")
            print(f"   📍 Posición: {style['position']}")
            
        except Exception as e:
            print(f"❌ Error mostrando detalles: {e}")
    
    def select_template_for_content(self):
        """Seleccionar template para contenido específico"""
        print("\n🎯 SELECCIÓN DE TEMPLATE PARA CONTENIDO")
        print("-" * 40)
        
        print("Ingresa información del contenido:")
        title = input("📝 Título: ").strip()
        duration = input("⏱️ Duración (segundos, default 30): ").strip()
        quality = input("🎯 Score de calidad (0-100, default 50): ").strip()
        
        # Valores por defecto
        duration = int(duration) if duration.isdigit() else 30
        quality = int(quality) if quality.isdigit() and 0 <= int(quality) <= 100 else 50
        
        content_info = {
            'original_title': title,
            'duration_seconds': duration,
            'quality_score': quality
        }
        
        try:
            selected = self.template_manager.select_template_for_content(content_info)
            
            print(f"\n🎨 Template seleccionado: {selected}")
            
            # Mostrar detalles del template seleccionado
            details = self.template_manager.get_template_preview(selected)
            print(f"📝 {details['name']}")
            print(f"💬 {details['description']}")
            
        except Exception as e:
            print(f"❌ Error seleccionando template: {e}")
    
    def configure_templates(self):
        """Configurar templates"""
        print("\n⚙️ CONFIGURACIÓN DE TEMPLATES")
        print("-" * 40)
        
        print("📁 Archivo de configuración: configs/templates.yaml")
        print("✏️ Para editar templates, modifica el archivo de configuración")
        print("🔄 Reinicia la aplicación para aplicar cambios")
        
        print("\n📖 Estructura de template:")
        print("   • name: Nombre descriptivo")
        print("   • description: Descripción del estilo")  
        print("   • subtitle_style: Estilo de subtítulos")
        print("   • branding: Configuración de marca")
        print("   • video_effects: Efectos de video")
        print("   • audio_effects: Efectos de audio")
        print("   • priority: Prioridad (mayor = preferido)")
        print("   • enabled: true/false")
    
    def demo_template_selection(self):
        """Demo de selección automática de templates"""
        print("\n🧪 DEMO: SELECCIÓN AUTOMÁTICA DE TEMPLATES")
        print("-" * 40)
        
        # Ejemplos de contenido
        examples = [
            {
                'original_title': 'Cómo programar en Python - Tutorial completo',
                'duration_seconds': 45,
                'quality_score': 85,
                'description': 'Tutorial paso a paso para aprender Python'
            },
            {
                'original_title': 'EPIC Gaming Moments - Best Highlights',
                'duration_seconds': 30,
                'quality_score': 70,
                'description': 'Gaming highlights and epic moments compilation'
            },
            {
                'original_title': 'Mi rutina diaria - Lifestyle Vlog',
                'duration_seconds': 60,
                'quality_score': 60,
                'description': 'Comparto mi día a día y rutina personal'
            }
        ]
        
        try:
            for i, content in enumerate(examples, 1):
                selected = self.template_manager.select_template_for_content(content)
                details = self.template_manager.get_template_preview(selected)
                
                print(f"\n{i}. 📺 '{content['original_title'][:50]}...'")
                print(f"   ⏱️ Duración: {content['duration_seconds']}s")
                print(f"   🎯 Calidad: {content['quality_score']}/100")
                print(f"   🎨 Template seleccionado: {details['name']}")
                print(f"   💬 Razón: Optimizado para este tipo de contenido")
                
        except Exception as e:
            print(f"❌ Error en demo: {e}")
    
    def manage_channels_videos(self):
        """Gestión manual de canales y videos"""
        print("\n📺 GESTIÓN DE CANALES Y VIDEOS")
        print("-" * 40)
        
        print("1. 📋 Ver todos los canales")
        print("2. ➕ Añadir canal manualmente")
        print("3. 📹 Ver videos de un canal")
        print("4. ➕ Añadir video manualmente")
        print("5. 🔍 Analizar URL de YouTube")
        print("6. 🗑️ Eliminar canal")
        print("7. 🗑️ Eliminar video")
        print("8. 📊 Estadísticas de canales")
        print("0. 🔙 Volver")
        
        choice = input("\n👉 Selecciona opción: ").strip()
        
        if choice == '1':
            self.list_all_channels()
        elif choice == '2':
            self.add_channel_manually()
        elif choice == '3':
            self.view_channel_videos()
        elif choice == '4':
            self.add_video_manually()
        elif choice == '5':
            self.analyze_youtube_url()
        elif choice == '6':
            self.delete_channel()
        elif choice == '7':
            self.delete_video()
        elif choice == '8':
            self.show_channel_stats()
    
    def list_all_channels(self):
        """Listar todos los canales registrados"""
        print("\n📋 CANALES REGISTRADOS")
        print("-" * 40)
        
        try:
            channels = self.db.get_all_channels()
            
            if not channels:
                print("📭 No hay canales registrados")
                return
            
            print(f"📊 Total de canales: {len(channels)}")
            print()
            
            for i, channel in enumerate(channels, 1):
                status = "✅" if channel['is_active'] else "❌"
                print(f"{i}. {status} {channel['name']}")
                print(f"   🆔 ID: {channel['channel_id']}")
                print(f"   👥 Suscriptores: {channel.get('subscriber_count', 0):,}")
                print(f"   📹 Videos: {channel['total_videos']} ({channel['processed_videos']} procesados)")
                print(f"   📅 Descubierto: {channel['discovered_at'][:10]}")
                print(f"   🔗 URL: {channel.get('url', 'N/A')}")
                
                if channel.get('description'):
                    desc = channel['description'][:100] + ('...' if len(channel['description']) > 100 else '')
                    print(f"   💬 {desc}")
                print()
                
        except Exception as e:
            print(f"❌ Error listando canales: {e}")
    
    def add_channel_manually(self):
        """Añadir canal manualmente"""
        print("\n➕ AÑADIR CANAL MANUALMENTE")
        print("-" * 40)
        
        if not YOUTUBE_PARSER_AVAILABLE:
            print("⚠️  Parser de YouTube no disponible. Modo manual básico.")
            
            channel_id = input("🆔 Channel ID (UCxxxx...): ").strip()
            channel_name = input("📝 Nombre del canal: ").strip()
            channel_url = input("🔗 URL (opcional): ").strip()
            description = input("💬 Descripción (opcional): ").strip()
            
            try:
                subscriber_count = int(input("👥 Número de suscriptores (0): ").strip() or "0")
            except ValueError:
                subscriber_count = 0
            
            if not channel_id or not channel_name:
                print("❌ Channel ID y nombre son requeridos")
                return
            
            # Validar formato de Channel ID básico
            if not (channel_id.startswith('UC') and len(channel_id) == 24):
                confirm = input("⚠️  El ID no tiene formato estándar. ¿Continuar? (s/N): ")
                if confirm.lower() != 's':
                    return
            
            confirm = input(f"\n✅ ¿Añadir canal '{channel_name}'? (s/N): ")
            if confirm.lower() != 's':
                print("❌ Operación cancelada")
                return
            
            success = self.db.add_channel_manually(
                channel_id=channel_id,
                channel_name=channel_name,
                channel_url=channel_url or f"https://www.youtube.com/channel/{channel_id}",
                description=description or f"Canal añadido manualmente: {channel_name}",
                subscriber_count=subscriber_count
            )
            
            if success:
                print(f"✅ Canal '{channel_name}' añadido exitosamente")
            else:
                print(f"❌ Error añadiendo canal (posiblemente ya existe)")
            
            return
        
        # Resto del código con parser...
        print("Puedes usar:")
        print("• URL completa: https://www.youtube.com/channel/UCxxxx")
        print("• URL con @: https://www.youtube.com/@nombrecanal")
        print("• Solo el ID: UCxxxxxxxxxxxxxxxxxxxx")
        print("• Solo el @: @nombrecanal")
        
        url_input = input("\n🔗 URL o ID del canal: ").strip()
        
        if not url_input:
            print("❌ URL o ID requerido")
            return
        
        try:
            print("🔍 Analizando canal...")
            
            # Si es una URL completa, parsearla
            if url_input.startswith('http') or '@' in url_input:
                result = parse_youtube_url(url_input)
                if result['type'] != 'channel':
                    print(f"❌ URL no reconocida como canal: {result.get('data', {}).get('error', 'Error desconocido')}")
                    return
                
                channel_info = result['data']
            else:
                # Asumir que es un ID directo
                channel_info = self.youtube_parser.get_channel_info_from_page(url_input)
            
            if 'error' in channel_info:
                print(f"❌ Error obteniendo información: {channel_info['error']}")
                return
            
            # Mostrar información encontrada
            print(f"\n📺 Información encontrada:")
            print(f"   🆔 ID: {channel_info['channel_id']}")
            print(f"   📝 Nombre: {channel_info['name']}")
            print(f"   👥 Suscriptores: {channel_info.get('subscriber_count', 0):,}")
            print(f"   🔗 URL: {channel_info['url']}")
            
            if channel_info.get('description'):
                desc = channel_info['description'][:200] + ('...' if len(channel_info['description']) > 200 else '')
                print(f"   💬 Descripción: {desc}")
            
            # Confirmación
            confirm = input(f"\n✅ ¿Añadir este canal? (s/N): ")
            if confirm.lower() != 's':
                print("❌ Operación cancelada")
                return
            
            # Añadir a la base de datos
            success = self.db.add_channel_manually(
                channel_id=channel_info['channel_id'],
                channel_name=channel_info['name'],
                channel_url=channel_info['url'],
                description=channel_info.get('description'),
                subscriber_count=channel_info.get('subscriber_count', 0)
            )
            
            if success:
                print(f"✅ Canal '{channel_info['name']}' añadido exitosamente")
            else:
                print(f"❌ Error añadiendo canal (posiblemente ya existe)")
                
        except Exception as e:
            print(f"❌ Error añadiendo canal: {e}")
    
    def view_channel_videos(self):
        """Ver videos de un canal específico"""
        print("\n📹 VIDEOS POR CANAL")
        print("-" * 40)
        
        # Primero mostrar canales disponibles
        channels = self.db.get_all_channels()
        if not channels:
            print("📭 No hay canales registrados")
            return
        
        print("Canales disponibles:")
        for i, channel in enumerate(channels, 1):
            print(f"{i}. {channel['name']} ({channel['total_videos']} videos)")
        
        try:
            selection = input("\n👉 Selecciona canal (número o ID): ").strip()
            
            # Si es un número, usar índice
            if selection.isdigit():
                idx = int(selection) - 1
                if 0 <= idx < len(channels):
                    channel_id = channels[idx]['channel_id']
                    channel_name = channels[idx]['name']
                else:
                    print("❌ Número de canal inválido")
                    return
            else:
                # Asumir que es un channel_id
                channel_id = selection
                channel_name = channel_id
            
            # Obtener videos del canal
            videos = self.db.get_videos_by_channel(channel_id, limit=20)
            
            if not videos:
                print(f"📭 No hay videos en el canal {channel_name}")
                return
            
            print(f"\n📹 Videos en {channel_name} (últimos {len(videos)}):")
            print("-" * 60)
            
            for i, video in enumerate(videos, 1):
                processed = "✅" if video['processed'] else "⏳"
                print(f"{i}. {processed} {video['title']}")
                print(f"   🆔 ID: {video['video_id']}")
                print(f"   ⏱️  Duración: {format_duration(video.get('duration_seconds', 0))}")
                print(f"   📅 Publicado: {video.get('published_at', 'N/A')[:10]}")
                print(f"   🎬 Segmentos: {video.get('total_segments', 0)}")
                print(f"   📦 Composites: {video.get('total_composites', 0)}")
                print(f"   🔗 URL: {video.get('url', 'N/A')}")
                print()
                
        except Exception as e:
            print(f"❌ Error mostrando videos: {e}")
    
    def add_video_manually(self):
        """Añadir video manualmente"""
        print("\n➕ AÑADIR VIDEO MANUALMENTE")
        print("-" * 40)
        
        # Primero mostrar canales disponibles
        channels = self.db.get_all_channels()
        if not channels:
            print("❌ No hay canales registrados. Añade un canal primero.")
            return
        
        print("Canales disponibles:")
        for i, channel in enumerate(channels, 1):
            print(f"{i}. {channel['name']} ({channel['channel_id']})")
        
        if not YOUTUBE_PARSER_AVAILABLE:
            print("\n⚠️  Parser de YouTube no disponible. Modo manual básico.")
            
            video_id = input("🆔 Video ID (11 caracteres): ").strip()
            title = input("📝 Título del video: ").strip()
            url = input("🔗 URL (opcional): ").strip()
            
            try:
                duration = int(input("⏱️ Duración en segundos (0): ").strip() or "0")
            except ValueError:
                duration = 0
            
            description = input("💬 Descripción (opcional): ").strip()
            published_at = input("📅 Fecha publicación (YYYY-MM-DD, opcional): ").strip()
            
            if not video_id or not title:
                print("❌ Video ID y título son requeridos")
                return
            
            # Validar formato básico del Video ID
            if len(video_id) != 11:
                confirm = input("⚠️  El ID no tiene 11 caracteres. ¿Continuar? (s/N): ")
                if confirm.lower() != 's':
                    return
            
            # Seleccionar canal
            selection = input("👉 Selecciona canal (número): ").strip()
            
            if not selection.isdigit():
                print("❌ Selección inválida")
                return
                
            idx = int(selection) - 1
            if not (0 <= idx < len(channels)):
                print("❌ Número de canal inválido")
                return
            
            target_channel_id = channels[idx]['channel_id']
            
            confirm = input(f"\n✅ ¿Añadir video '{title}'? (s/N): ")
            if confirm.lower() != 's':
                print("❌ Operación cancelada")
                return
            
            success = self.db.add_video_manually(
                video_id=video_id,
                channel_id=target_channel_id,
                title=title,
                url=url or f"https://www.youtube.com/watch?v={video_id}",
                duration_seconds=duration,
                description=description,
                published_at=published_at
            )
            
            if success:
                print(f"✅ Video '{title}' añadido exitosamente")
            else:
                print(f"❌ Error añadiendo video (posiblemente ya existe)")
            
            return
        
        # Resto del código con parser...
        print("\nPuedes usar:")
        print("• URL completa: https://www.youtube.com/watch?v=xxxxxxx")
        print("• URL corta: https://youtu.be/xxxxxxx")
        print("• Solo el ID: xxxxxxxxxxx")
        
        url_input = input("\n🔗 URL o ID del video: ").strip()
        
        if not url_input:
            print("❌ URL o ID requerido")
            return
        
        try:
            print("🔍 Analizando video...")
            
            # Si es una URL completa, parsearla
            if url_input.startswith('http'):
                result = parse_youtube_url(url_input)
                if result['type'] != 'video':
                    print(f"❌ URL no reconocida como video: {result.get('data', {}).get('error', 'Error desconocido')}")
                    return
                
                video_info = result['data']
            else:
                # Asumir que es un ID directo
                video_info = self.youtube_parser.get_video_info_from_page(url_input)
            
            if 'error' in video_info:
                print(f"❌ Error obteniendo información: {video_info['error']}")
                return
            
            # Mostrar información encontrada
            print(f"\n📺 Información encontrada:")
            print(f"   🆔 ID: {video_info['video_id']}")
            print(f"   📝 Título: {video_info['title']}")
            print(f"   📺 Canal: {video_info['channel_name']}")
            print(f"   🆔 Canal ID: {video_info.get('channel_id', 'N/A')}")
            print(f"   ⏱️  Duración: {format_duration(video_info.get('duration_seconds', 0))}")
            print(f"   📅 Publicado: {video_info.get('published_at', 'N/A')}")
            print(f"   🔗 URL: {video_info['url']}")
            
            if video_info.get('description'):
                desc = video_info['description'][:200] + ('...' if len(video_info['description']) > 200 else '')
                print(f"   💬 Descripción: {desc}")
            
            # Seleccionar canal de destino
            print(f"\n📺 Seleccionar canal de destino:")
            
            # Si el video tiene channel_id, intentar encontrarlo
            target_channel_id = None
            if video_info.get('channel_id'):
                for channel in channels:
                    if channel['channel_id'] == video_info['channel_id']:
                        target_channel_id = channel['channel_id']
                        print(f"   ✅ Canal encontrado automáticamente: {channel['name']}")
                        break
            
            if not target_channel_id:
                selection = input("👉 Selecciona canal (número): ").strip()
                
                if selection.isdigit():
                    idx = int(selection) - 1
                    if 0 <= idx < len(channels):
                        target_channel_id = channels[idx]['channel_id']
                    else:
                        print("❌ Número de canal inválido")
                        return
                else:
                    print("❌ Selección inválida")
                    return
            
            # Confirmación
            confirm = input(f"\n✅ ¿Añadir este video? (s/N): ")
            if confirm.lower() != 's':
                print("❌ Operación cancelada")
                return
            
            # Añadir a la base de datos
            success = self.db.add_video_manually(
                video_id=video_info['video_id'],
                channel_id=target_channel_id,
                title=video_info['title'],
                url=video_info['url'],
                duration_seconds=video_info.get('duration_seconds', 0),
                description=video_info.get('description'),
                published_at=video_info.get('published_at')
            )
            
            if success:
                print(f"✅ Video '{video_info['title']}' añadido exitosamente")
            else:
                print(f"❌ Error añadiendo video (posiblemente ya existe)")
                
        except Exception as e:
            print(f"❌ Error añadiendo video: {e}")
    
    def analyze_youtube_url(self):
        """Analizar cualquier URL de YouTube"""
        print("\n🔍 ANALIZAR URL DE YOUTUBE")
        print("-" * 40)
        
        if not YOUTUBE_PARSER_AVAILABLE:
            print("❌ Parser de YouTube no disponible")
            print("   Instala las dependencias necesarias para usar esta función")
            return
        
        url = input("🔗 Ingresa URL de YouTube: ").strip()
        
        if not url:
            print("❌ URL requerida")
            return
        
        try:
            print("🔍 Analizando...")
            result = parse_youtube_url(url)
            
            print(f"\n📊 Tipo detectado: {result['type'].upper()}")
            
            if result['type'] == 'video':
                data = result['data']
                print(f"   🆔 Video ID: {data['video_id']}")
                print(f"   📝 Título: {data['title']}")
                print(f"   📺 Canal: {data['channel_name']}")
                print(f"   🆔 Canal ID: {data.get('channel_id', 'N/A')}")
                print(f"   ⏱️  Duración: {format_duration(data.get('duration_seconds', 0))}")
                print(f"   📅 Publicado: {data.get('published_at', 'N/A')}")
                
                if data.get('description'):
                    desc = data['description'][:150] + ('...' if len(data['description']) > 150 else '')
                    print(f"   💬 Descripción: {desc}")
                    
            elif result['type'] == 'channel':
                data = result['data']
                print(f"   🆔 Canal ID: {data['channel_id']}")
                print(f"   📝 Nombre: {data['name']}")
                print(f"   👥 Suscriptores: {data.get('subscriber_count', 0):,}")
                
                if data.get('description'):
                    desc = data['description'][:150] + ('...' if len(data['description']) > 150 else '')
                    print(f"   💬 Descripción: {desc}")
                    
            else:
                print(f"   ❌ {result['data'].get('error', 'URL no reconocida')}")
            
        except Exception as e:
            print(f"❌ Error analizando URL: {e}")
    
    def delete_channel(self):
        """Eliminar canal"""
        print("\n🗑️ ELIMINAR CANAL")
        print("-" * 40)
        
        channels = self.db.get_all_channels()
        if not channels:
            print("📭 No hay canales registrados")
            return
        
        print("Canales disponibles:")
        for i, channel in enumerate(channels, 1):
            print(f"{i}. {channel['name']} ({channel['total_videos']} videos)")
        
        try:
            selection = input("\n👉 Selecciona canal a eliminar (número): ").strip()
            
            if not selection.isdigit():
                print("❌ Selección inválida")
                return
            
            idx = int(selection) - 1
            if not (0 <= idx < len(channels)):
                print("❌ Número de canal inválido")
                return
            
            channel = channels[idx]
            
            print(f"\n⚠️  Canal seleccionado: {channel['name']}")
            print(f"   🆔 ID: {channel['channel_id']}")
            print(f"   📹 Videos asociados: {channel['total_videos']}")
            
            if channel['total_videos'] > 0:
                cascade = input("🗑️ ¿Eliminar también todos los videos asociados? (s/N): ")
                cascade_delete = cascade.lower() == 's'
                
                if not cascade_delete:
                    print("❌ No se puede eliminar canal con videos asociados sin cascada")
                    return
            else:
                cascade_delete = False
            
            confirm = input(f"\n⚠️  ¿CONFIRMAR eliminación de '{channel['name']}'? (s/N): ")
            if confirm.lower() != 's':
                print("❌ Operación cancelada")
                return
            
            success = self.db.delete_channel(channel['channel_id'], cascade=cascade_delete)
            
            if success:
                print(f"✅ Canal '{channel['name']}' eliminado exitosamente")
            else:
                print(f"❌ Error eliminando canal")
                
        except Exception as e:
            print(f"❌ Error eliminando canal: {e}")
    
    def delete_video(self):
        """Eliminar video"""
        print("\n🗑️ ELIMINAR VIDEO")
        print("-" * 40)
        
        channels = self.db.get_all_channels()
        if not channels:
            print("📭 No hay canales registrados")
            return
        
        print("Canales disponibles:")
        for i, channel in enumerate(channels, 1):
            print(f"{i}. {channel['name']} ({channel['total_videos']} videos)")
        
        try:
            selection = input("\n👉 Selecciona canal (número): ").strip()
            
            if not selection.isdigit():
                print("❌ Selección inválida")
                return
            
            idx = int(selection) - 1
            if not (0 <= idx < len(channels)):
                print("❌ Número de canal inválido")
                return
            
            channel = channels[idx]
            videos = self.db.get_videos_by_channel(channel['channel_id'], limit=20)
            
            if not videos:
                print(f"📭 No hay videos en el canal {channel['name']}")
                return
            
            print(f"\nVideos en {channel['name']}:")
            for i, video in enumerate(videos, 1):
                print(f"{i}. {video['title'][:50]}... ({video['video_id']})")
            
            video_selection = input("\n👉 Selecciona video a eliminar (número): ").strip()
            
            if not video_selection.isdigit():
                print("❌ Selección inválida")
                return
            
            video_idx = int(video_selection) - 1
            if not (0 <= video_idx < len(videos)):
                print("❌ Número de video inválido")
                return
            
            video = videos[video_idx]
            
            print(f"\n⚠️  Video seleccionado: {video['title']}")
            print(f"   🆔 ID: {video['video_id']}")
            print(f"   🎬 Segmentos asociados: {video.get('total_segments', 0)}")
            print(f"   📦 Composites asociados: {video.get('total_composites', 0)}")
            
            if video.get('total_segments', 0) > 0:
                cascade = input("🗑️ ¿Eliminar también segmentos y composites asociados? (s/N): ")
                cascade_delete = cascade.lower() == 's'
                
                if not cascade_delete:
                    print("❌ No se puede eliminar video con segmentos asociados sin cascada")
                    return
            else:
                cascade_delete = False
            
            confirm = input(f"\n⚠️  ¿CONFIRMAR eliminación de '{video['title']}'? (s/N): ")
            if confirm.lower() != 's':
                print("❌ Operación cancelada")
                return
            
            success = self.db.delete_video(video['video_id'], cascade=cascade_delete)
            
            if success:
                print(f"✅ Video '{video['title']}' eliminado exitosamente")
            else:
                print(f"❌ Error eliminando video")
                
        except Exception as e:
            print(f"❌ Error eliminando video: {e}")
    
    def show_channel_stats(self):
        """Mostrar estadísticas de canales"""
        print("\n📊 ESTADÍSTICAS DE CANALES")
        print("-" * 40)
        
        try:
            channels = self.db.get_all_channels()
            
            if not channels:
                print("📭 No hay canales registrados")
                return
            
            # Estadísticas generales
            total_channels = len(channels)
            active_channels = sum(1 for c in channels if c['is_active'])
            total_videos = sum(c['total_videos'] for c in channels)
            processed_videos = sum(c['processed_videos'] for c in channels)
            total_subscribers = sum(c.get('subscriber_count', 0) for c in channels)
            
            print(f"📊 Resumen General:")
            print(f"   📺 Total de canales: {total_channels}")
            print(f"   ✅ Canales activos: {active_channels}")
            print(f"   📹 Total de videos: {total_videos}")
            print(f"   ✅ Videos procesados: {processed_videos}")
            print(f"   👥 Suscriptores totales: {total_subscribers:,}")
            
            if total_videos > 0:
                processing_rate = (processed_videos / total_videos) * 100
                print(f"   📈 Tasa de procesamiento: {processing_rate:.1f}%")
            
            print(f"\n🏆 Top 5 Canales por Videos:")
            top_channels = sorted(channels, key=lambda x: x['total_videos'], reverse=True)[:5]
            
            for i, channel in enumerate(top_channels, 1):
                status = "✅" if channel['is_active'] else "❌"
                print(f"   {i}. {status} {channel['name']}")
                print(f"      📹 Videos: {channel['total_videos']} ({channel['processed_videos']} procesados)")
                print(f"      👥 Suscriptores: {channel.get('subscriber_count', 0):,}")
            
            print(f"\n👥 Top 3 Canales por Suscriptores:")
            top_subs = sorted(channels, key=lambda x: x.get('subscriber_count', 0), reverse=True)[:3]
            
            for i, channel in enumerate(top_subs, 1):
                if channel.get('subscriber_count', 0) > 0:
                    print(f"   {i}. {channel['name']}")
                    print(f"      👥 {channel['subscriber_count']:,} suscriptores")
                    print(f"      📹 {channel['total_videos']} videos")
                    
        except Exception as e:
            print(f"❌ Error mostrando estadísticas: {e}")
    
    def run(self):
        """Ejecutar interfaz CLI"""
        self.show_banner()
        
        while self.running:
            try:
                self.show_menu()
                choice = input("👉 Selecciona una opción: ").strip()
                
                if choice == '1':
                    self.show_stats()
                elif choice == '2':
                    self.show_pending_queue()
                elif choice == '3':
                    self.approve_short()
                elif choice == '4':
                    self.reject_short()
                elif choice == '5':
                    self.schedule_short()
                elif choice == '6':
                    self.bulk_operations()
                elif choice == '7':
                    self.toggle_daemon()
                elif choice == '8':
                    self.publish_approved()
                elif choice == '9':
                    self.show_system_info()
                elif choice.lower() == 'scoring' or choice == '🎯':
                    self.run_auto_scoring()
                elif choice.lower() == 'templates' or choice == '🎨':
                    self.manage_templates()
                elif choice.lower() == 'canales' or choice == '📺':
                    self.manage_channels_videos()
                elif choice == '0':
                    print("👋 ¡Hasta luego! Que recuperes pronto tu acceso a Telegram")
                    self.running = False
                else:
                    print("❌ Opción no válida")
                
                if self.running and choice != '0':
                    input("\n⏸️  Presiona Enter para continuar...")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Saliendo... ¡Hasta luego!")
                self.running = False
            except Exception as e:
                print(f"\n❌ Error: {e}")
                input("⏸️  Presiona Enter para continuar...")

if __name__ == '__main__':
    cli = CLIControl()
    cli.run()
