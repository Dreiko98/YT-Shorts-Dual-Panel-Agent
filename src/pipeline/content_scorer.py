"""
🧠 Sistema de Scoring Automático para Shorts
Evalúa automáticamente la calidad de los shorts generados
"""

import os
import sys
import subprocess
import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging
from datetime import datetime

# Añadir src al path
sys.path.append('src')
from pipeline.db import PipelineDB

logger = logging.getLogger(__name__)

class ContentScorer:
    """Evaluador automático de calidad de contenido"""
    
    def __init__(self):
        self.db = PipelineDB()
        
        # Configuración de scoring
        self.weights = {
            'audio_quality': 0.30,    # 30% - Calidad de audio
            'duration_optimal': 0.20, # 20% - Duración óptima  
            'subtitle_presence': 0.25, # 25% - Presencia de subtítulos
            'video_stability': 0.25    # 25% - Estabilidad visual
        }
        
        # Thresholds para auto-aprobación
        self.auto_approve_threshold = 80  # Score > 80 = auto-aprobar
        self.auto_reject_threshold = 40   # Score < 40 = auto-rechazar
        
    def calculate_score(self, composite_data: Dict) -> Tuple[int, Dict]:
        """Calcular score total y desglose de un composite"""
        
        scores = {
            'audio_quality': 0,
            'duration_optimal': 0, 
            'subtitle_presence': 0,
            'video_stability': 0
        }
        
        details = {}
        
        try:
            # 1. Evaluar calidad de audio
            audio_score, audio_details = self._evaluate_audio_quality(composite_data)
            scores['audio_quality'] = audio_score
            details['audio'] = audio_details
            
            # 2. Evaluar duración óptima
            duration_score, duration_details = self._evaluate_duration(composite_data)
            scores['duration_optimal'] = duration_score
            details['duration'] = duration_details
            
            # 3. Evaluar presencia de subtítulos
            subtitle_score, subtitle_details = self._evaluate_subtitles(composite_data)
            scores['subtitle_presence'] = subtitle_score  
            details['subtitles'] = subtitle_details
            
            # 4. Evaluar estabilidad del video
            stability_score, stability_details = self._evaluate_video_stability(composite_data)
            scores['video_stability'] = stability_score
            details['video_stability'] = stability_details
            
            # Calcular score total ponderado
            total_score = sum(
                scores[category] * self.weights[category] 
                for category in scores
            )
            
            # Redondear a entero
            total_score = round(min(total_score, 100))
            
            logger.info(f"Score calculado para {composite_data['clip_id'][:12]}: {total_score}/100")
            
            return total_score, {
                'total_score': total_score,
                'category_scores': scores,
                'details': details,
                'evaluated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculando score para {composite_data['clip_id']}: {e}")
            return 50, {'error': str(e), 'total_score': 50}  # Score neutro en caso de error
    
    def _evaluate_audio_quality(self, composite_data: Dict) -> Tuple[int, Dict]:
        """Evaluar calidad de audio (0-100 puntos)"""
        
        file_path = Path(composite_data.get('output_path', ''))
        
        if not file_path.exists():
            return 0, {'error': 'Archivo no encontrado'}
        
        try:
            # Usar ffmpeg para analizar audio
            cmd = [
                'ffmpeg', '-i', str(file_path),
                '-af', 'astats=metadata=1:reset=1',
                '-f', 'null', '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Analizar LUFS si está disponible en los metadatos
            lufs = composite_data.get('lufs')
            
            if lufs is not None:
                # LUFS óptimo para shorts: -14 a -23 LUFS
                if -23 <= lufs <= -14:
                    lufs_score = 100
                elif -25 <= lufs <= -12:
                    lufs_score = 80
                elif -30 <= lufs <= -10:
                    lufs_score = 60
                else:
                    lufs_score = 30
            else:
                lufs_score = 70  # Score neutro si no hay info de LUFS
            
            # Detectar si hay audio (duración > 0)
            has_audio = 'Audio:' in result.stderr
            audio_presence = 100 if has_audio else 0
            
            # Score final combinado
            final_score = (lufs_score * 0.7) + (audio_presence * 0.3)
            
            return round(final_score), {
                'lufs': lufs,
                'lufs_score': lufs_score,
                'has_audio': has_audio,
                'audio_presence_score': audio_presence
            }
            
        except Exception as e:
            logger.warning(f"Error analizando audio: {e}")
            return 60, {'error': str(e), 'fallback_score': 60}
    
    def _evaluate_duration(self, composite_data: Dict) -> Tuple[int, Dict]:
        """Evaluar duración óptima (0-100 puntos)"""
        
        duration = composite_data.get('duration_seconds', 0)
        
        # Duración óptima para shorts: 15-60 segundos
        if 20 <= duration <= 45:
            score = 100  # Duración perfecta
        elif 15 <= duration <= 60:
            score = 90   # Duración muy buena
        elif 10 <= duration <= 70:
            score = 70   # Duración aceptable
        elif 5 <= duration <= 90:
            score = 50   # Duración marginal
        else:
            score = 20   # Duración problemática
        
        return score, {
            'duration_seconds': duration,
            'optimal_range': '20-45s',
            'category': self._categorize_duration(duration)
        }
    
    def _categorize_duration(self, duration: float) -> str:
        """Categorizar duración"""
        if 20 <= duration <= 45:
            return 'perfect'
        elif 15 <= duration <= 60:
            return 'very_good'
        elif 10 <= duration <= 70:
            return 'acceptable'
        elif 5 <= duration <= 90:
            return 'marginal'
        else:
            return 'problematic'
    
    def _evaluate_subtitles(self, composite_data: Dict) -> Tuple[int, Dict]:
        """Evaluar presencia y calidad de subtítulos (0-100 puntos)"""
        
        file_path = Path(composite_data.get('output_path', ''))
        
        if not file_path.exists():
            return 0, {'error': 'Archivo no encontrado'}
        
        try:
            # Detectar subtítulos incrustados usando ffprobe
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_streams', 
                '-select_streams', 's', '-of', 'json', str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                streams_info = json.loads(result.stdout)
                subtitle_streams = streams_info.get('streams', [])
                
                if subtitle_streams:
                    # Hay subtítulos incrustados
                    score = 100
                    subtitle_info = {
                        'has_subtitles': True,
                        'subtitle_streams': len(subtitle_streams),
                        'method': 'embedded'
                    }
                else:
                    # Buscar subtítulos por patrones en el nombre del archivo
                    # (indica que se procesaron con subtítulos durante la generación)
                    if any(keyword in file_path.name.lower() for keyword in ['sub', 'caption', 'text']):
                        score = 90
                        subtitle_info = {
                            'has_subtitles': True,
                            'method': 'inferred_from_filename'
                        }
                    else:
                        score = 30  # Asumir que no hay subtítulos
                        subtitle_info = {
                            'has_subtitles': False,
                            'method': 'not_detected'
                        }
            else:
                # Error ejecutando ffprobe, score neutro
                score = 50
                subtitle_info = {
                    'has_subtitles': None,
                    'error': 'ffprobe_failed'
                }
            
            return score, subtitle_info
            
        except Exception as e:
            logger.warning(f"Error analizando subtítulos: {e}")
            return 40, {'error': str(e)}
    
    def _evaluate_video_stability(self, composite_data: Dict) -> Tuple[int, Dict]:
        """Evaluar estabilidad visual del video (0-100 puntos)"""
        
        file_path = Path(composite_data.get('output_path', ''))
        
        if not file_path.exists():
            return 0, {'error': 'Archivo no encontrado'}
        
        try:
            # Analizar propiedades básicas del video
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries',
                'stream=avg_frame_rate,r_frame_rate,width,height,pix_fmt',
                '-of', 'json', str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                return 50, {'error': 'ffprobe_failed'}
            
            info = json.loads(result.stdout)
            video_streams = [s for s in info.get('streams', []) if s.get('codec_type') == 'video']
            
            if not video_streams:
                return 0, {'error': 'no_video_stream'}
            
            stream = video_streams[0]
            
            # Evaluar resolución
            width = int(stream.get('width', 0))
            height = int(stream.get('height', 0))
            
            # Score por resolución (optimizado para shorts 9:16)
            if width == 1080 and height == 1920:
                resolution_score = 100  # Resolución perfecta para shorts
            elif width >= 720 and height >= 1280:
                resolution_score = 90   # Resolución muy buena
            elif width >= 480:
                resolution_score = 70   # Resolución aceptable
            else:
                resolution_score = 40   # Resolución baja
            
            # Evaluar frame rate
            fps_str = stream.get('avg_frame_rate', '30/1')
            try:
                fps = eval(fps_str) if '/' in fps_str else float(fps_str)
                
                if 29 <= fps <= 31:
                    fps_score = 100     # 30fps perfecto
                elif 24 <= fps <= 35:
                    fps_score = 90      # FPS muy bueno
                elif 15 <= fps <= 60:
                    fps_score = 70      # FPS aceptable
                else:
                    fps_score = 40      # FPS problemático
            except:
                fps_score = 70          # Score neutro si no se puede parsear
            
            # Score final combinado
            final_score = (resolution_score * 0.7) + (fps_score * 0.3)
            
            return round(final_score), {
                'resolution': f"{width}x{height}",
                'resolution_score': resolution_score,
                'fps': fps,
                'fps_score': fps_score,
                'pixel_format': stream.get('pix_fmt')
            }
            
        except Exception as e:
            logger.warning(f"Error analizando estabilidad del video: {e}")
            return 60, {'error': str(e)}
    
    def process_pending_shorts(self) -> Dict:
        """Procesar todos los shorts pendientes y aplicar scoring"""
        
        pending_shorts = self.db.get_pending_review_composites(limit=50)
        results = {
            'processed': 0,
            'auto_approved': 0,
            'auto_rejected': 0,
            'manual_review': 0,
            'errors': 0
        }
        
        for short in pending_shorts:
            try:
                # Obtener detalles completos
                details = self.db.get_composite_details(short['clip_id'])
                if not details:
                    continue
                
                # Calcular score
                score, score_details = self.calculate_score(details)
                
                # Guardar score en base de datos
                self._save_score_to_db(short['clip_id'], score, score_details)
                
                # Decidir acción automática
                action_taken = self._apply_auto_action(short['clip_id'], score, score_details)
                
                results['processed'] += 1
                results[action_taken] += 1
                
            except Exception as e:
                logger.error(f"Error procesando short {short['clip_id']}: {e}")
                results['errors'] += 1
        
        return results
    
    def _save_score_to_db(self, clip_id: str, score: int, score_details: Dict):
        """Guardar score en la base de datos"""
        
        try:
            # Añadir columna de score si no existe
            self.db.conn.execute('''
                ALTER TABLE composites ADD COLUMN quality_score INTEGER DEFAULT NULL
            ''')
        except sqlite3.OperationalError:
            pass  # Columna ya existe
        
        try:
            # Añadir columna de score_details si no existe  
            self.db.conn.execute('''
                ALTER TABLE composites ADD COLUMN score_details TEXT DEFAULT NULL
            ''')
        except sqlite3.OperationalError:
            pass  # Columna ya existe
        
        # Guardar score
        self.db.conn.execute('''
            UPDATE composites 
            SET quality_score = ?, score_details = ?
            WHERE clip_id = ?
        ''', (score, json.dumps(score_details), clip_id))
        
        self.db.conn.commit()
    
    def _apply_auto_action(self, clip_id: str, score: int, score_details: Dict) -> str:
        """Aplicar acción automática basada en el score"""
        
        if score >= self.auto_approve_threshold:
            # Auto-aprobar
            comment = f"Auto-aprobado: Score {score}/100 (excelente calidad)"
            self.db.approve_composite(clip_id, comment=comment)
            logger.info(f"✅ Auto-aprobado: {clip_id[:12]} (Score: {score})")
            return 'auto_approved'
            
        elif score <= self.auto_reject_threshold:
            # Auto-rechazar
            reason = f"Auto-rechazado: Score {score}/100 (calidad insuficiente)"
            self.db.reject_composite(clip_id, reason=reason)
            logger.info(f"❌ Auto-rechazado: {clip_id[:12]} (Score: {score})")
            return 'auto_rejected'
            
        else:
            # Mantener en revisión manual
            logger.info(f"📋 Revisión manual: {clip_id[:12]} (Score: {score})")
            return 'manual_review'
    
    def get_scoring_stats(self) -> Dict:
        """Obtener estadísticas del sistema de scoring"""
        
        try:
            cursor = self.db.conn.cursor()
            
            # Estadísticas básicas
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_scored,
                    AVG(quality_score) as avg_score,
                    MIN(quality_score) as min_score,
                    MAX(quality_score) as max_score,
                    COUNT(CASE WHEN quality_score >= ? THEN 1 END) as auto_approved_eligible,
                    COUNT(CASE WHEN quality_score <= ? THEN 1 END) as auto_rejected_eligible
                FROM composites 
                WHERE quality_score IS NOT NULL
            ''', (self.auto_approve_threshold, self.auto_reject_threshold))
            
            stats = dict(cursor.fetchone())
            
            # Distribución por rangos de score
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN quality_score >= 80 THEN 'excellent'
                        WHEN quality_score >= 60 THEN 'good' 
                        WHEN quality_score >= 40 THEN 'fair'
                        ELSE 'poor'
                    END as quality_range,
                    COUNT(*) as count
                FROM composites 
                WHERE quality_score IS NOT NULL
                GROUP BY 1
            ''')
            
            distribution = dict(cursor.fetchall())
            
            return {
                'basic_stats': stats,
                'score_distribution': distribution,
                'thresholds': {
                    'auto_approve': self.auto_approve_threshold,
                    'auto_reject': self.auto_reject_threshold
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de scoring: {e}")
            return {'error': str(e)}

def main():
    """Función principal para testing"""
    
    print("🧠 Sistema de Scoring Automático - Test")
    print("=" * 50)
    
    scorer = ContentScorer()
    
    # Procesar shorts pendientes
    results = scorer.process_pending_shorts()
    
    print("📊 Resultados del procesamiento:")
    for key, value in results.items():
        print(f"   • {key}: {value}")
    
    # Mostrar estadísticas
    stats = scorer.get_scoring_stats()
    print("\n📈 Estadísticas del sistema:")
    print(json.dumps(stats, indent=2, default=str))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
