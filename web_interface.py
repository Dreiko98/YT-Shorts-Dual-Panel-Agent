#!/usr/bin/env python3
"""
🌐 INTERFAZ WEB ALTERNATIVA - Control del Pipeline
Para usar mientras no tienes acceso a Telegram

Ejecuta: python web_interface.py
Accede: http://localhost:8080
"""

import sys
sys.path.append('src')

from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from pipeline.db import PipelineDB
# Publisher es opcional; evitamos que un módulo faltante tumbe la interfaz
try:
    from pipeline.publisher import YouTubePublisher  # type: ignore
except Exception:
    YouTubePublisher = None  # Permite que la app siga funcionando sin publisher
from datetime import datetime
import os
import json
from pathlib import Path


# Exponer carpeta de vídeos como ruta estática
from flask import send_from_directory

app = Flask(__name__)
app.secret_key = 'dev-key-temporal'

# Ruta absoluta a la carpeta donde se guardan los vídeos (ajusta si usas otra)
VIDEO_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/shorts_auto'))

# Servir archivos de vídeo desde /media/<filename>
@app.route('/media/<path:filename>')
def media(filename):
    return send_from_directory(VIDEO_FOLDER, filename)

@app.route('/health')
def health_check():
    """Health check endpoint for Docker"""
    try:
        db = PipelineDB()
        stats = db.get_queue_stats()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'queue_stats': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# Template HTML simple pero funcional
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🎬 YT Shorts Control Panel</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .header { text-align: center; color: #333; margin-bottom: 30px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }
        .queue-section { margin-bottom: 30px; }
        .short-item { background: #fff; border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; }
        .short-actions { margin-top: 10px; }
        .btn { padding: 8px 16px; margin: 0 5px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-info { background: #17a2b8; color: white; }
        .btn-warning { background: #ffc107; color: black; }
        .btn-primary { background: #007bff; color: white; }
        .bulk-actions { background: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0; }
        .log-section { background: #f8f9fa; padding: 15px; border-radius: 8px; max-height: 300px; overflow-y: auto; }
        .status-pending { border-left: 4px solid #ffc107; }
        .status-approved { border-left: 4px solid #28a745; }
        .status-rejected { border-left: 4px solid #dc3545; }
        .daemon-status { padding: 10px; border-radius: 5px; margin: 10px 0; text-align: center; font-weight: bold; }
        .daemon-running { background: #d4edda; color: #155724; }
        .daemon-paused { background: #f8d7da; color: #721c24; }
        input, select { padding: 8px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
        .preview-section { margin: 15px 0; padding: 15px; background: #e7f3ff; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">

        <div class="header">
            <h1>🎬 YT Shorts Control Panel</h1>
            <p>Alternativa web mientras recuperas acceso a Telegram</p>
        </div>

        <!-- Procesar video por URL -->
        <div class="bulk-actions" style="background: #fffbe6; border: 1px solid #ffe58f;">
            <h3>🎯 Procesar video de YouTube por URL</h3>
            <form method="POST" action="/process_url" style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                <input type="url" name="video_url" placeholder="https://www.youtube.com/watch?v=..." required style="flex:1; min-width:300px;">
                <button type="submit" class="btn btn-primary">Procesar y Publicar</button>
            </form>
            {% if process_url_result %}
                <div style="margin-top:10px; color: {{ 'green' if process_url_success else 'red' }};">
                    {{ process_url_result }}
                </div>
            {% endif %}
        </div>

        <!-- Estado del Sistema -->
        <div class="daemon-status {{ 'daemon-running' if not daemon_paused else 'daemon-paused' }}">
            🤖 Daemon: {{ "⏸️ PAUSADO" if daemon_paused else "▶️ EJECUTÁNDOSE" }}
            <a href="/toggle_daemon" class="btn btn-warning" style="margin-left: 10px;">
                {{ "Reanudar" if daemon_paused else "Pausar" }}
            </a>
        </div>

        <!-- Controles de Auto-Publicación -->
        <div class="auto-publish-controls" style="margin: 20px 0; padding: 15px; background: #e8f4fd; border-radius: 8px;">
            <h3>📺 Auto-Publicación</h3>
            <div style="display: flex; gap: 15px; align-items: center; flex-wrap: wrap;">
                <div>
                    <label>
                        <input type="checkbox" id="autoPublishToggle" onchange="toggleAutoPublish()">
                        Publicación Automática
                    </label>
                </div>
                <div>
                    <span id="publishStatus">🔄 Cargando...</span>
                </div>
                <div>
                    <button onclick="forcePublish()" class="btn btn-info">🚀 Publicar Ahora</button>
                </div>
                <div>
                    <small id="publishConfig">Horarios: 10:00, 15:00, 20:00</small>
                </div>
            </div>
        </div>

        <!-- Estadísticas -->
        <div class="stats">
            <div class="stat-card">
                <h3>🔄 Pendientes</h3>
                <h2>{{ queue_stats.pending_review }}</h2>
            </div>
            <div class="stat-card">
                <h3>✅ Aprobados</h3>
                <h2>{{ queue_stats.approved }}</h2>
            </div>
            <div class="stat-card">
                <h3>❌ Rechazados</h3>
                <h2>{{ queue_stats.rejected }}</h2>
            </div>
            <div class="stat-card">
                <h3>📤 Publicados</h3>
                <h2>{{ queue_stats.published }}</h2>
            </div>
        </div>

        <!-- Acciones en Lote -->
        <div class="bulk-actions">
            <h3>📦 Operaciones en Lote</h3>
            <a href="/bulk_approve_all" class="btn btn-success" onclick="return confirm('¿Aprobar TODOS los pendientes?')">✅ Aprobar Todos</a>
            <a href="/bulk_reject_all" class="btn btn-danger" onclick="return confirm('¿Rechazar TODOS los pendientes?')">❌ Rechazar Todos</a>
            <a href="/publish_approved" class="btn btn-primary">📤 Publicar Aprobados</a>
        </div>

        <!-- Cola de Shorts Pendientes -->
        <div class="queue-section">
            <h2>🔄 Shorts Pendientes de Revisión</h2>
            {% for short in pending_shorts %}
            <div class="short-item status-{{ short.review_status }}">
                <h4>📱 {{ short.clip_id[:12] }}...</h4>
                <p><strong>Título:</strong> {{ short.title[:80] if short.title else 'Sin título' }}{% if short.title and short.title|length > 80 %}...{% endif %}</p>
                <p><strong>Duración:</strong> {{ short.duration_seconds }}s | <strong>Creado:</strong> {{ short.created_at[:16] }}</p>
                
                {% if short.output_path and short.output_path.endswith('.mp4') %}
                <div class="preview-section">
                    <strong>🎬 Vista Previa:</strong> {{ short.output_path.split('/')[-1] }}
                    <br><small>Archivo: {{ short.output_path }}</small>
                    <br>
                    {% set video_filename = short.output_path.split('/')[-1] %}
                    <video width="320" height="570" controls style="margin-top:10px; background:#000;" preload="metadata">
                        <source src="{{ url_for('media', filename=video_filename) }}" type="video/mp4">
                        Tu navegador no soporta la previsualización de video.
                    </video>
                </div>
                {% endif %}

                <div class="short-actions">
                    <a href="/approve/{{ short.clip_id }}" class="btn btn-success">✅ Aprobar</a>
                    <a href="/reject/{{ short.clip_id }}" class="btn btn-danger">❌ Rechazar</a>
                    <form style="display: inline-block; margin-left: 10px;" method="POST" action="/schedule/{{ short.clip_id }}">
                        <input type="datetime-local" name="schedule_time" title="Programar para...">
                        <button type="submit" class="btn btn-info">📅 Programar</button>
                    </form>
                </div>
            </div>
            {% else %}
            <p>📭 No hay shorts pendientes de revisión</p>
            {% endfor %}
        </div>

        <!-- Shorts Aprobados -->
        {% if approved_shorts %}
        <div class="queue-section">
            <h2>✅ Shorts Aprobados (Listos para Publicar)</h2>
            {% for short in approved_shorts %}
            <div class="short-item status-approved">
                <h4>📱 {{ short.clip_id[:12] }}...</h4>
                <p><strong>Título:</strong> {{ short.title[:80] if short.title else 'Sin título' }}{% if short.title and short.title|length > 80 %}...{% endif %}</p>
                <p><strong>Aprobado:</strong> {{ short.reviewed_at[:16] if short.reviewed_at else 'N/A' }}</p>
                {% if short.scheduled_publish_at %}
                <p><strong>📅 Programado:</strong> {{ short.scheduled_publish_at }}</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <!-- Pipeline Manual -->
        <div class="bulk-actions">
            <h3>🔧 Pipeline Manual</h3>
            <a href="/discover" class="btn btn-info">🔍 Buscar Videos</a>
            <a href="/process_videos" class="btn btn-warning">⚙️ Procesar Videos</a>
            <a href="/channels" class="btn btn-primary">📺 Gestionar Canales</a>
            <a href="/logs" class="btn btn-primary">📝 Ver Logs</a>
        </div>

        <!-- Footer con información -->
        <div style="margin-top: 40px; text-align: center; color: #666; font-size: 12px;">
            <p>🌐 Interfaz Web Temporal | Última actualización: {{ current_time }}</p>
            <p>💡 Cuando recuperes Telegram, usa: <code>/help</code> para ver todos los comandos del bot</p>
        </div>
    </div>

    <script>
        // Auto-refresh cada 30 segundos
        setTimeout(function(){ location.reload(); }, 30000);
        
        // Auto-publish controls
        async function loadAutoPublishStatus() {
            try {
                const response = await fetch('/api/auto-publish/status');
                const data = await response.json();
                
                document.getElementById('autoPublishToggle').checked = data.auto_publish_enabled;
                document.getElementById('publishStatus').textContent = 
                    data.auto_publish_enabled ? '✅ Activa' : '⏸️ Inactiva';
                document.getElementById('publishConfig').textContent = 
                    `Horarios: ${data.publish_times} | Máx: ${data.max_posts_per_day}/día | Intervalo: ${data.min_hours_between}h`;
            } catch (error) {
                console.error('Error loading auto-publish status:', error);
            }
        }
        
        async function toggleAutoPublish() {
            const enabled = document.getElementById('autoPublishToggle').checked;
            
            try {
                const response = await fetch('/api/auto-publish/toggle', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ enabled: enabled })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('publishStatus').textContent = 
                        enabled ? '✅ Activa' : '⏸️ Inactiva';
                    alert(data.message);
                } else {
                    alert('Error: ' + data.error);
                    document.getElementById('autoPublishToggle').checked = !enabled;
                }
            } catch (error) {
                console.error('Error toggling auto-publish:', error);
                alert('Error de conexión');
                document.getElementById('autoPublishToggle').checked = !enabled;
            }
        }
        
        async function forcePublish() {
            if (!confirm('¿Estás seguro de que quieres publicar el próximo clip ahora?')) {
                return;
            }
            
            try {
                const response = await fetch('/api/force-publish', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert('✅ ' + data.message);
                    location.reload();
                } else {
                    alert('❌ Error: ' + data.error);
                }
            } catch (error) {
                console.error('Error forcing publish:', error);
                alert('❌ Error de conexión');
            }
        }
        
        // Cargar estado al iniciar
        document.addEventListener('DOMContentLoaded', function() {
            loadAutoPublishStatus();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard(process_url_result=None, process_url_success=None):
    """Dashboard principal"""
    db = PipelineDB()
    # Obtener estadísticas
    queue_stats = db.get_queue_stats()
    daemon_paused = db.is_daemon_paused()
    # Obtener shorts pendientes
    pending_shorts = db.get_pending_review_composites(limit=20)
    approved_shorts = db.get_approved_composites(limit=10)
    return render_template_string(HTML_TEMPLATE,
        queue_stats=queue_stats,
        daemon_paused=daemon_paused,
        pending_shorts=pending_shorts,
        approved_shorts=approved_shorts,
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        process_url_result=process_url_result,
        process_url_success=process_url_success
    )

@app.route('/process_url', methods=['POST'])
def process_url():
    from src.utils.youtube_parser import YouTubeURLParser
    from src.pipeline.db import PipelineDB
    from src.pipeline.downloader import download_video, DownloadError
    from src.pipeline.transcribe import WhisperTranscriber, TranscriptionError
    from src.pipeline.segmenter import TranscriptSegmenter, SegmentationError
    from src.pipeline.editor import ShortComposer, CompositionError
    from src.pipeline.auto_publisher import AutoPublisher
    import traceback
    import os
    import json
    from pathlib import Path
    import random

    video_url = request.form.get('video_url', '').strip()
    if not video_url:
        return redirect(url_for('dashboard'))

    try:
        parser = YouTubeURLParser()
        db = PipelineDB()
        # 1. Extraer video_id
        video_id = parser.extract_video_id(video_url)
        if not video_id:
            raise Exception('No se pudo extraer el video_id de la URL')

        # 2. Obtener info del video
        video_info = parser.get_video_info_from_page(video_id)
        channel_id = video_info.get('channel_id')
        if not channel_id:
            raise Exception('No se pudo extraer el channel_id del video')

        # 3. Añadir canal si no existe
        channels = db.get_all_channels()
        if not any(c['channel_id'] == channel_id for c in channels):
            db.add_channel_manually(channel_id, video_info.get('channel_name', 'Canal desconocido'))

        # 4. Añadir video si no existe
        if not db.video_exists(video_id):
            db.add_video_manually(
                video_id=video_id,
                channel_id=channel_id,
                title=video_info.get('title', f'Video {video_id}'),
                url=video_url,
                duration_seconds=video_info.get('duration_seconds', 0)
            )

        # 5. Descargar video
        base_dir = Path('data')
        podcast_path = download_video(video_id, channel_id, base_dir)
        db.mark_video_downloaded(video_id, str(podcast_path))

        # 6. Seleccionar B-roll (elige aleatorio de data/raw/broll/*/*.mp4)
        broll_root = Path('data/raw/broll')
        broll_candidates = list(broll_root.glob('*/*.mp4')) if broll_root.exists() else []
        if not broll_candidates:
            raise Exception('No se encontraron videos de B-roll en data/raw/broll')
        broll_path = random.choice(broll_candidates)

        # 7. Transcribir
        whisper_model = os.environ.get('WHISPER_MODEL', 'small')
        whisper_device = os.environ.get('WHISPER_DEVICE', 'cpu')
        transcriber = WhisperTranscriber(model_name=whisper_model, device=whisper_device)
        transcripts_dir = base_dir / 'transcripts'
        transcript_result = transcriber.transcribe_video(podcast_path, transcripts_dir)
        transcript_json = transcript_result['transcript_json']

        # 8. Segmentar
        segmenter_conf = {
            "min_clip_duration": int(os.environ.get('MIN_CLIP_DURATION', 20)),
            "max_clip_duration": int(os.environ.get('MAX_CLIP_DURATION', 60)),
            "target_clip_duration": 30,
            "overlap_threshold": 0.1,
            "scoring_weights": {"keyword_match":0.3,"sentence_completeness":0.25,"duration_fit":0.25,"speech_quality":0.2},
            "important_keywords": []
        }
        segmenter = TranscriptSegmenter(segmenter_conf)
        candidates = segmenter.segment_transcript(Path(transcript_json))
        if not candidates:
            raise Exception('No se encontraron segmentos para shorts')

        # 9. Componer shorts
        shorts_dir = base_dir / 'shorts'
        with open(transcript_json, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        composer = ShortComposer()
        results = composer.compose_multiple_shorts(
            candidates=candidates,
            podcast_video_path=podcast_path,
            broll_video_path=broll_path,
            transcript_data=transcript_data,
            output_dir=shorts_dir,
            max_shorts=int(os.environ.get('MAX_CLIPS_PER_VIDEO', 3)),
            include_subtitles=True
        )
        # Marcar como procesado
        db.mark_video_processed(video_id)

        # 10. Auto-aprobar y publicar
        config = dict(os.environ)
        publisher = AutoPublisher(db, config)
        publisher.auto_approve_clips()
        publisher.run_publishing_cycle()

        process_url_success = True
        process_url_result = f"✅ Video procesado y shorts publicados correctamente. ({video_url})"
    except Exception as e:
        process_url_success = False
        tb = traceback.format_exc()
        process_url_result = f"❌ Error procesando video: {e}\n{tb}"
    return dashboard(process_url_result=process_url_result, process_url_success=process_url_success)

@app.route('/approve/<clip_id>')
def approve_short(clip_id):
    """Aprobar un short"""
    db = PipelineDB()
    if db.approve_composite(clip_id, comment="Aprobado vía Web UI"):
        print(f"✅ Short {clip_id} aprobado vía web")
    return redirect(url_for('dashboard'))

@app.route('/reject/<clip_id>')
def reject_short(clip_id):
    """Rechazar un short"""
    db = PipelineDB()
    if db.reject_composite(clip_id, reason="Rechazado vía Web UI"):
        print(f"❌ Short {clip_id} rechazado vía web")
    return redirect(url_for('dashboard'))

@app.route('/api/auto-publish/toggle', methods=['POST'])
def toggle_auto_publish():
    """Activar/desactivar publicación automática"""
    try:
        enabled = request.json.get('enabled', False)
        
        # Actualizar configuración en la base de datos
        db = PipelineDB()
        db.set_daemon_paused(not enabled)
        
        return jsonify({
            'success': True,
            'auto_publish_enabled': enabled,
            'message': f"Publicación automática {'activada' if enabled else 'desactivada'}"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auto-publish/status')
def auto_publish_status():
    """Obtener estado de la publicación automática"""
    try:
        db = PipelineDB()
        is_paused = db.is_daemon_paused()
        
        return jsonify({
            'auto_publish_enabled': not is_paused,
            'publish_times': os.getenv('PUBLISH_TIMES', '10:00,15:00,20:00'),
            'max_posts_per_day': int(os.getenv('MAX_POSTS_PER_DAY', 3)),
            'min_hours_between': int(os.getenv('MIN_TIME_BETWEEN_POSTS_HOURS', 4)),
            'auto_approve_enabled': os.getenv('AUTO_APPROVE_ENABLED', 'false').lower() == 'true'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/force-publish', methods=['POST'])
def force_publish():
    """Forzar publicación inmediata del próximo clip"""
    try:
        db = PipelineDB()
        
        # Obtener próximo clip
        next_clip = db.get_next_scheduled_clip()
        if not next_clip:
            return jsonify({'error': 'No hay clips listos para publicar'}), 400
        
        # Simular publicación forzada
        clip_id = next_clip['clip_id']
        title = next_clip.get('title', 'Video sin título')
        
        # Marcar como publicado
        success = db.mark_as_published(clip_id, f"https://youtube.com/shorts/forced_{clip_id}")
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Clip "{title}" publicado forzadamente',
                'clip_id': clip_id
            })
        else:
            return jsonify({'error': 'Error al marcar como publicado'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/schedule/<clip_id>', methods=['POST'])
def schedule_short(clip_id):
    """Programar un short"""
    db = PipelineDB()
    schedule_time = request.form.get('schedule_time')
    if schedule_time:
        # Convertir datetime-local a ISO
        scheduled_at = datetime.fromisoformat(schedule_time).isoformat()
        if db.approve_composite(clip_id, scheduled_at=scheduled_at, comment="Programado vía Web UI"):
            print(f"📅 Short {clip_id} programado para {scheduled_at}")
    return redirect(url_for('dashboard'))

@app.route('/bulk_approve_all')
def bulk_approve_all():
    """Aprobar todos los pendientes"""
    db = PipelineDB()
    pending = db.get_pending_review_composites(limit=50)
    count = 0
    for short in pending:
        if db.approve_composite(short['clip_id'], comment="Aprobación masiva vía Web UI"):
            count += 1
    print(f"✅ {count} shorts aprobados en lote vía web")
    return redirect(url_for('dashboard'))

@app.route('/bulk_reject_all')
def bulk_reject_all():
    """Rechazar todos los pendientes"""
    db = PipelineDB()
    pending = db.get_pending_review_composites(limit=50)
    count = 0
    for short in pending:
        if db.reject_composite(short['clip_id'], reason="Rechazo masivo vía Web UI"):
            count += 1
    print(f"❌ {count} shorts rechazados en lote vía web")
    return redirect(url_for('dashboard'))

@app.route('/toggle_daemon')
def toggle_daemon():
    """Pausar/reanudar daemon"""
    db = PipelineDB()
    current_state = db.is_daemon_paused()
    new_state = not current_state
    if db.set_daemon_paused(new_state):
        action = "pausado" if new_state else "reanudado"
        print(f"🔄 Daemon {action} vía web")
    return redirect(url_for('dashboard'))

@app.route('/publish_approved')
def publish_approved():
    """Publicar shorts aprobados"""
    try:
        # Esto requeriría configuración completa de YouTube API
        print("📤 Intentando publicar shorts aprobados...")
        # publisher = YouTubePublisher()
        # publisher.publish_shorts_queue()
        print("⚠️ Función de publicación requiere configuración completa de YouTube API")
    except Exception as e:
        print(f"❌ Error publicando: {e}")
    return redirect(url_for('dashboard'))

@app.route('/discover')
def discover():
    """Buscar nuevos videos"""
    print("🔍 Discovery manual iniciado vía web...")
    return redirect(url_for('dashboard'))

@app.route('/process_videos')
def process_videos():
    """Procesar videos pendientes"""
    print("⚙️ Procesamiento manual iniciado vía web...")
    return redirect(url_for('dashboard'))

@app.route('/logs')
def view_logs():
    """Ver logs del sistema"""
    try:
        log_files = list(Path('logs').glob('*.log'))
        if log_files:
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            with open(latest_log, 'r') as f:
                logs = f.read()[-2000:]  # Últimas 2000 caracteres
        else:
            logs = "No hay archivos de log disponibles"
    except Exception as e:
        logs = f"Error leyendo logs: {e}"
    
    return f"<pre>{logs}</pre><br><a href='/'>🔙 Volver al Dashboard</a>"

@app.route('/channels')
def manage_channels():
    """Página de gestión de canales"""
    db = PipelineDB()
    channels = db.get_all_channels()
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>📺 Gestión de Canales - YT Shorts Pipeline</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .btn { padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
            .btn-primary { background: #3498db; color: white; }
            .btn-success { background: #27ae60; color: white; }
            .btn-danger { background: #e74c3c; color: white; }
            .btn-back { background: #95a5a6; color: white; }
            .btn:hover { opacity: 0.8; }
            .channels-grid { display: grid; gap: 20px; margin-top: 20px; }
            .channel-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .channel-header { display: flex; justify-content: between; align-items: center; margin-bottom: 15px; }
            .channel-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 15px 0; }
            .stat { background: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center; }
            .stat-number { font-size: 1.5em; font-weight: bold; color: #3498db; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
            .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            .form-group textarea { height: 100px; resize: vertical; }
            .add-form { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📺 Gestión de Canales</h1>
                <p>Añadir y gestionar canales manualmente</p>
            </div>
            
            <a href="/" class="btn btn-back">🔙 Volver al Dashboard</a>
            
            <div class="add-form">
                <h2>➕ Añadir Canal Nuevo</h2>
                <form method="POST" action="/channels/add">
                    <div class="form-group">
                        <label for="channel_id">Channel ID:</label>
                        <input type="text" id="channel_id" name="channel_id" placeholder="UCxxxxxxxxxxxxxxxxxxxx" required>
                    </div>
                    <div class="form-group">
                        <label for="channel_name">Nombre del Canal:</label>
                        <input type="text" id="channel_name" name="channel_name" placeholder="Mi Canal de YouTube" required>
                    </div>
                    <div class="form-group">
                        <label for="channel_url">URL (opcional):</label>
                        <input type="url" id="channel_url" name="channel_url" placeholder="https://www.youtube.com/channel/UCxxxx">
                    </div>
                    <div class="form-group">
                        <label for="description">Descripción (opcional):</label>
                        <textarea id="description" name="description" placeholder="Descripción del canal..."></textarea>
                    </div>
                    <div class="form-group">
                        <label for="subscriber_count">Número de Suscriptores:</label>
                        <input type="number" id="subscriber_count" name="subscriber_count" value="0" min="0">
                    </div>
                    <button type="submit" class="btn btn-success">✅ Añadir Canal</button>
                </form>
            </div>
            
            <h2>📋 Canales Registrados ({{ channels|length }})</h2>
            
            <div class="channels-grid">
                {% for channel in channels %}
                <div class="channel-card">
                    <div class="channel-header">
                        <h3>{{ "✅" if channel.is_active else "❌" }} {{ channel.name }}</h3>
                    </div>
                    
                    <p><strong>🆔 ID:</strong> {{ channel.channel_id }}</p>
                    
                    {% if channel.url %}
                    <p><strong>🔗 URL:</strong> <a href="{{ channel.url }}" target="_blank">{{ channel.url }}</a></p>
                    {% endif %}
                    
                    {% if channel.description %}
                    <p><strong>💬 Descripción:</strong> {{ channel.description[:100] }}{{ "..." if channel.description|length > 100 }}</p>
                    {% endif %}
                    
                    <div class="channel-stats">
                        <div class="stat">
                            <div class="stat-number">{{ "{:,}".format(channel.subscriber_count or 0) }}</div>
                            <div>👥 Suscriptores</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ channel.total_videos or 0 }}</div>
                            <div>📹 Videos</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ channel.processed_videos or 0 }}</div>
                            <div>✅ Procesados</div>
                        </div>
                    </div>
                    
                    <p><strong>📅 Descubierto:</strong> {{ channel.discovered_at[:10] if channel.discovered_at else "N/A" }}</p>
                    
                    <div style="margin-top: 15px;">
                        <a href="/channels/{{ channel.channel_id }}/videos" class="btn btn-primary">📹 Ver Videos</a>
                        <a href="/channels/{{ channel.channel_id }}/delete" class="btn btn-danger" 
                           onclick="return confirm('¿Eliminar canal {{ channel.name }}?')">🗑️ Eliminar</a>
                    </div>
                </div>
                {% else %}
                <div class="channel-card">
                    <p style="text-align: center; color: #7f8c8d; font-style: italic;">
                        📭 No hay canales registrados. Añade el primero usando el formulario de arriba.
                    </p>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """, channels=channels)

@app.route('/channels/add', methods=['POST'])
def add_channel():
    """Añadir nuevo canal"""
    try:
        db = PipelineDB()
        channel_id = request.form.get('channel_id', '').strip()
        channel_name = request.form.get('channel_name', '').strip()
        channel_url = request.form.get('channel_url', '').strip()
        description = request.form.get('description', '').strip()
        
        try:
            subscriber_count = int(request.form.get('subscriber_count', 0))
        except ValueError:
            subscriber_count = 0
        
        if not channel_id or not channel_name:
            return jsonify({'error': 'Channel ID y nombre son requeridos'}), 400
        
        success = db.add_channel_manually(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_url=channel_url or f"https://www.youtube.com/channel/{channel_id}",
            description=description or f"Canal añadido manualmente: {channel_name}",
            subscriber_count=subscriber_count
        )
        
        if success:
            return redirect('/channels')
        else:
            return jsonify({'error': 'Error añadiendo canal (posiblemente ya existe)'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/channels/<channel_id>/videos')
def channel_videos(channel_id):
    """Ver videos de un canal"""
    try:
        db = PipelineDB()
        videos = db.get_videos_by_channel(channel_id, limit=50)
        channel_name = videos[0]['channel_name'] if videos else channel_id
        
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>📹 Videos de {{ channel_name }} - YT Shorts Pipeline</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .btn { padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
                .btn-back { background: #95a5a6; color: white; }
                .btn-success { background: #27ae60; color: white; }
                .btn:hover { opacity: 0.8; }
                .video-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; }
                .video-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
                .video-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 10px 0; }
                .stat { background: #f8f9fa; padding: 8px; border-radius: 5px; text-align: center; font-size: 0.9em; }
                .add-form { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .form-group { margin-bottom: 15px; }
                .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
                .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📹 Videos de {{ channel_name }}</h1>
                    <p>Gestión de videos del canal</p>
                </div>
                
                <a href="/channels" class="btn btn-back">🔙 Volver a Canales</a>
                
                <div class="add-form">
                    <h2>➕ Añadir Video Nuevo</h2>
                    <form method="POST" action="/channels/{{ channel_id }}/videos/add">
                        <div class="form-group">
                            <label for="video_id">Video ID (11 caracteres):</label>
                            <input type="text" id="video_id" name="video_id" placeholder="dQw4w9WgXcQ" maxlength="11" required>
                        </div>
                        <div class="form-group">
                            <label for="title">Título del Video:</label>
                            <input type="text" id="title" name="title" placeholder="Mi Video de YouTube" required>
                        </div>
                        <div class="form-group">
                            <label for="url">URL (opcional):</label>
                            <input type="url" id="url" name="url" placeholder="https://www.youtube.com/watch?v=...">
                        </div>
                        <div class="form-group">
                            <label for="duration_seconds">Duración (segundos):</label>
                            <input type="number" id="duration_seconds" name="duration_seconds" value="0" min="0">
                        </div>
                        <button type="submit" class="btn btn-success">✅ Añadir Video</button>
                    </form>
                </div>
                
                <h2>📋 Videos Registrados ({{ videos|length }})</h2>
                
                {% for video in videos %}
                <div class="video-card">
                    <div class="video-header">
                        <h3>{{ "✅" if video.processed else "⏳" }} {{ video.title }}</h3>
                    </div>
                    
                    <p><strong>🆔 Video ID:</strong> {{ video.video_id }}</p>
                    
                    {% if video.url %}
                    <p><strong>🔗 URL:</strong> <a href="{{ video.url }}" target="_blank">{{ video.url }}</a></p>
                    {% endif %}
                    
                    <div class="video-stats">
                        <div class="stat">
                            <strong>⏱️ {{ video.duration_seconds // 60 }}:{{ "{:02d}".format(video.duration_seconds % 60) }}</strong><br>
                            Duración
                        </div>
                        <div class="stat">
                            <strong>📅 {{ video.published_at[:10] if video.published_at else "N/A" }}</strong><br>
                            Publicado
                        </div>
                    </div>
                </div>
                {% else %}
                <div class="video-card">
                    <p style="text-align: center; color: #7f8c8d; font-style: italic;">
                        📭 No hay videos registrados en este canal. Añade el primero usando el formulario de arriba.
                    </p>
                </div>
                {% endfor %}
            </div>
        </body>
        </html>
        """, videos=videos, channel_name=channel_name, channel_id=channel_id)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/channels/<channel_id>/videos/add', methods=['POST'])
def add_video_to_channel(channel_id):
    """Añadir video a un canal"""
    try:
        db = PipelineDB()
        video_id = request.form.get('video_id', '').strip()
        title = request.form.get('title', '').strip()
        url = request.form.get('url', '').strip()
        
        try:
            duration_seconds = int(request.form.get('duration_seconds', 0))
        except ValueError:
            duration_seconds = 0
        
        if not video_id or not title:
            return jsonify({'error': 'Video ID y título son requeridos'}), 400
        
        success = db.add_video_manually(
            video_id=video_id,
            channel_id=channel_id,
            title=title,
            url=url or f"https://www.youtube.com/watch?v={video_id}",
            duration_seconds=duration_seconds
        )
        
        if success:
            return redirect(f'/channels/{channel_id}/videos')
        else:
            return jsonify({'error': 'Error añadiendo video (posiblemente ya existe)'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/channels/<channel_id>/delete')
def delete_channel(channel_id):
    """Eliminar canal"""
    try:
        db = PipelineDB()
        success = db.delete_channel(channel_id)
        if success:
            return redirect('/channels')
        else:
            return jsonify({'error': 'Error eliminando canal'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Permitir configurar el puerto vía variable de entorno (WEB_PORT) con fallback a 8081
    web_port = int(os.getenv("WEB_PORT", "8081"))
    print("🌐 Iniciando interfaz web alternativa...")
    print(f"📱 Accede desde tu navegador: http://localhost:{web_port}")
    print("🔄 La página se actualiza automáticamente cada 30 segundos")
    print("💡 Usa Ctrl+C para detener el servidor")
    
    app.run(host='0.0.0.0', port=web_port, debug=True)
