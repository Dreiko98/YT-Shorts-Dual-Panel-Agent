#!/usr/bin/env python3
"""
CLI principal para el pipeline de YT Shorts Dual-Panel Agent.
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from typing_extensions import Annotated

# Añadir src/ al path para imports
sys.path.insert(0, str(Path(__file__).parent))

app = typer.Typer(
    name="yts",
    help="🎬 YT Shorts Dual-Panel Agent - Pipeline automatizado para generar YouTube Shorts",
    rich_markup_mode="rich",
)
console = Console()


@app.command()
def discover(
    channel_ids: Annotated[
        Optional[str], 
        typer.Option("--channels", "-c", help="IDs de canales separados por coma")
    ] = None,
    max_videos: Annotated[
        int, 
        typer.Option("--max", "-m", help="Máximo número de vídeos a descubrir")
    ] = 50,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
):
    """🔍 Descubrir nuevos episodios de podcast usando YouTube Data API."""
    rprint("[yellow]🔍 Descubriendo nuevos episodios...[/yellow]")
    
    if not channel_ids:
        rprint("[red]❌ No se especificaron canales. Usa --channels o configura channels.yaml[/red]")
        raise typer.Exit(1)
    
    # TODO: Implementar discovery.py
    rprint("[blue]📋 Canales a procesar:[/blue]", channel_ids)
    rprint(f"[blue]📊 Límite de vídeos:[/blue] {max_videos}")
    rprint("[yellow]⚠️  Funcionalidad pendiente de implementar[/yellow]")


@app.command()
def download(
    limit: Annotated[
        int, 
        typer.Option("--limit", "-l", help="Límite de descargas simultáneas")
    ] = 3,
    quality: Annotated[
        str, 
        typer.Option("--quality", "-q", help="Calidad de descarga")
    ] = "best[height<=1080]",
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
):
    """⬇️  Descargar podcasts pendientes usando yt-dlp."""
    rprint("[yellow]⬇️  Descargando podcasts pendientes...[/yellow]")
    
    # TODO: Implementar downloader.py
    rprint(f"[blue]📊 Límite simultáneo:[/blue] {limit}")
    rprint(f"[blue]🎥 Calidad:[/blue] {quality}")
    rprint("[yellow]⚠️  Funcionalidad pendiente de implementar[/yellow]")


@app.command()
def normalize(
    force: Annotated[bool, typer.Option("--force", "-f", help="Forzar renormalización")] = False,
    target_fps: Annotated[int, typer.Option("--fps", help="FPS objetivo")] = 30,
):
    """🎵 Normalizar audio y video (fps, resolución, loudness)."""
    rprint("[yellow]🎵 Normalizando audio/video...[/yellow]")
    
    # TODO: Implementar normalize.py
    rprint(f"[blue]🎯 FPS objetivo:[/blue] {target_fps}")
    rprint(f"[blue]🔄 Forzar renormalización:[/blue] {force}")
    rprint("[yellow]⚠️  Funcionalidad pendiente de implementar[/yellow]")


@app.command()
def transcribe(
    video_path: str = typer.Argument(..., help="Ruta al archivo de video"),
    output_dir: str = typer.Option("data/transcripts", help="Directorio de salida"),
    model: str = typer.Option("base", help="Modelo Whisper (tiny, base, small, medium, large)"),
    language: str = typer.Option(None, help="Idioma forzado (es, en, etc.)"),
    device: str = typer.Option("auto", help="Dispositivo (auto, cpu, cuda)")
):
    """Transcribir video usando Whisper."""
    from pathlib import Path
    from .pipeline.transcribe import transcribe_video_file, TranscriptionError, check_whisper_requirements
    
    console.print(f"🎤 [bold]Transcribiendo video:[/bold] {video_path}")
    
    # Verificar requirements
    requirements = check_whisper_requirements()
    if not requirements["whisper_installed"]:
        console.print("❌ [red]Whisper no está instalado. Ejecuta: pip install openai-whisper[/red]")
        raise typer.Exit(1)
    
    if not requirements["torch_available"]:
        console.print("❌ [red]PyTorch no está disponible[/red]")
        raise typer.Exit(1)
    
    video_file = Path(video_path)
    if not video_file.exists():
        console.print(f"❌ [red]Archivo de video no encontrado: {video_path}[/red]")
        raise typer.Exit(1)
    
    output_path = Path(output_dir)
    
    try:
        with console.status("Transcribiendo con Whisper..."):
            result = transcribe_video_file(
                video_path=video_file,
                output_dir=output_path,
                model=model,
                device=device,
                language=language
            )
        
        if result["success"]:
            console.print("✅ [green]Transcripción completada[/green]")
            console.print(f"   📄 JSON: {result['transcript_json']}")
            console.print(f"   📝 SRT: {result['transcript_srt']}")
            console.print(f"   🌍 Idioma: {result['language']}")
            console.print(f"   ⏱️ Duración: {result['duration']:.1f}s")
            console.print(f"   📊 Segmentos: {result['segments_count']}")
            console.print(f"   🎯 Calidad: {result['quality_score']:.1f}/100")
        else:
            console.print("❌ [red]Error en transcripción[/red]")
            raise typer.Exit(1)
    
    except TranscriptionError as e:
        console.print(f"❌ [red]Error: {e}[/red]")
        raise typer.Exit(1)



@app.command()
def segment(
    transcript_path: str = typer.Argument(..., help="Ruta al archivo de transcripción"),
    output_dir: str = typer.Option("data/segments", help="Directorio de salida"),
    keywords: str = typer.Option("", help="Palabras clave separadas por comas"),
    min_duration: int = typer.Option(15, help="Duración mínima del clip (s)"),
    max_duration: int = typer.Option(59, help="Duración máxima del clip (s)")
):
    """Segmentar transcripción en clips candidatos."""
    from pathlib import Path
    from .pipeline.segmenter import segment_transcript_file, SegmentationError
    
    console.print(f"✂️ [bold]Segmentando transcripción:[/bold] {transcript_path}")
    
    transcript_file = Path(transcript_path)
    if not transcript_file.exists():
        console.print(f"❌ [red]Archivo de transcripción no encontrado: {transcript_path}[/red]")
        raise typer.Exit(1)
    
    output_path = Path(output_dir)
    
    # Preparar configuración
    config = {
        "min_clip_duration": min_duration,
        "max_clip_duration": max_duration,
        "target_clip_duration": (min_duration + max_duration) // 2,
        "overlap_threshold": 0.1,
        "scoring_weights": {
            "keyword_match": 0.3,
            "sentence_completeness": 0.25,
            "duration_fit": 0.25,
            "speech_quality": 0.2
        },
        "important_keywords": []
    }
    
    # Procesar palabras clave
    keywords_list = None
    if keywords.strip():
        keywords_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        console.print(f"🔍 Filtrando por palabras clave: {', '.join(keywords_list)}")
    
    try:
        with console.status("Segmentando transcripción..."):
            candidates = segment_transcript_file(
                transcript_path=transcript_file,
                output_dir=output_path,
                config=config,
                keywords_filter=keywords_list
            )
        
        console.print("✅ [green]Segmentación completada[/green]")
        console.print(f"   📊 Clips candidatos: {len(candidates)}")
        
        if candidates:
            console.print("\n🏆 [bold]Top 5 candidatos:[/bold]")
            for i, candidate in enumerate(candidates[:5], 1):
                console.print(
                    f"   {i}. {candidate.formatted_duration} | "
                    f"Score: {candidate.score:.1f} | "
                    f"{candidate.text[:60]}..."
                )
        
        export_path = output_path / f"{transcript_file.stem}_candidates.json"
        console.print(f"   📄 Candidatos exportados: {export_path}")
    
    except SegmentationError as e:
        console.print(f"❌ [red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def segment_ai(
    transcript_path: str = typer.Argument(..., help="Ruta al archivo de transcripción JSON"),
    output_dir: str = typer.Option("data/segments", help="Directorio de salida"),
    keywords: str = typer.Option("", help="Palabras clave separadas por comas"),
    max_clips: int = typer.Option(5, help="Máximo número de clips a generar"),
    min_duration: int = typer.Option(15, help="Duración mínima del clip (s)"),
    max_duration: int = typer.Option(59, help="Duración máxima del clip (s)")
):
    """🤖 Segmentar transcripción usando IA (ChatGPT)."""
    from pathlib import Path
    from .pipeline.ai_segmenter import AITranscriptSegmenter, AISegmentationConfig, SegmentationError
    import json
    
    console.print(f"🤖 [bold]Segmentando con IA:[/bold] {transcript_path}")
    
    transcript_file = Path(transcript_path)
    if not transcript_file.exists():
        console.print(f"❌ [red]Archivo de transcripción no encontrado: {transcript_path}[/red]")
        raise typer.Exit(1)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Configurar segmentador IA
    config = AISegmentationConfig(
        max_clips=max_clips,
        min_duration=min_duration,
        max_duration=max_duration,
        target_duration=(min_duration + max_duration) / 2
    )
    
    # Procesar palabras clave
    keywords_list = None
    if keywords.strip():
        keywords_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        console.print(f"🔍 Palabras clave: {', '.join(keywords_list)}")
    
    try:
        segmenter = AITranscriptSegmenter(config)
        
        with console.status("Analizando con ChatGPT..."):
            candidates = segmenter.segment_transcript(
                transcript_file, 
                keywords_filter=keywords_list
            )
        
        console.print("✅ [green]Segmentación IA completada[/green]")
        console.print(f"   📊 Clips candidatos: {len(candidates)}")
        
        if candidates:
            console.print("\n🏆 [bold]Top clips por IA:[/bold]")
            for i, candidate in enumerate(candidates[:5], 1):
                metadata = candidate.metadata
                title = metadata.get("title", "Sin título")
                viral_score = metadata.get("viral_potential", 0)
                content_type = metadata.get("content_type", "unknown")
                
                console.print(
                    f"   {i}. {candidate.formatted_duration} | "
                    f"Viral: {viral_score}/100 | "
                    f"Tipo: {content_type}"
                )
                console.print(f"      📝 {title}")
                console.print(f"      🎯 {candidate.text[:80]}...")
                console.print()
        
        # Exportar candidatos
        export_data = {
            "candidates": [],
            "metadata": {
                "generated_by": "AI",
                "model": config.model,
                "total_candidates": len(candidates),
                "generation_timestamp": str(Path().cwd())
            }
        }
        
        for candidate in candidates:
            export_data["candidates"].append({
                "id": candidate.id,
                "start_time": candidate.start_time,
                "end_time": candidate.end_time,
                "duration": candidate.duration,
                "text": candidate.text,
                "keywords": candidate.keywords,
                "score": candidate.score,
                "metadata": candidate.metadata
            })
        
        export_path = output_path / f"{transcript_file.stem}_ai_candidates.json"
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        console.print(f"   📄 Candidatos IA exportados: {export_path}")
    
    except SegmentationError as e:
        console.print(f"❌ [red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ [red]Error inesperado: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def pipeline_ai(
    podcast_video: str = typer.Argument(..., help="Ruta al video de podcast"),
    broll_video: str = typer.Argument(..., help="Ruta al video de B-roll"),
    keywords: str = typer.Option("", help="Palabras clave separadas por comas"),
    max_shorts: int = typer.Option(3, help="Máximo número de Shorts a crear"),
    whisper_model: str = typer.Option("small", help="Modelo Whisper"),
    language: str = typer.Option("es", help="Idioma del podcast"),
    output_base: str = typer.Option("data", help="Directorio base de salida")
):
    """🚀 Pipeline completo: transcribir → segmentar con IA → componer Shorts."""
    from pathlib import Path
    from .pipeline.transcribe import transcribe_video_file, TranscriptionError
    from .pipeline.ai_segmenter import AITranscriptSegmenter, AISegmentationConfig, SegmentationError
    from .pipeline.editor import compose_short_from_files, CompositionError
    import json
    
    console.print("🚀 [bold]Iniciando pipeline completo con IA[/bold]")
    
    # Verificar archivos de entrada
    podcast_path = Path(podcast_video)
    broll_path = Path(broll_video)
    
    if not podcast_path.exists():
        console.print(f"❌ [red]Video de podcast no encontrado: {podcast_path}[/red]")
        raise typer.Exit(1)
    
    if not broll_path.exists():
        console.print(f"❌ [red]Video de B-roll no encontrado: {broll_path}[/red]")
        raise typer.Exit(1)
    
    base_name = podcast_path.stem
    base_dir = Path(output_base)
    
    # Configurar directorios
    transcripts_dir = base_dir / "transcripts"
    segments_dir = base_dir / "segments"  
    shorts_dir = base_dir / "shorts_ai"
    
    for dir_path in [transcripts_dir, segments_dir, shorts_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Paso 1: Transcribir
        console.print("\n📝 [bold cyan]Paso 1: Transcribiendo video...[/bold cyan]")
        transcript_path = transcripts_dir / f"{base_name}_transcript.json"
        
        if not transcript_path.exists():
            with console.status("Transcribiendo con Whisper..."):
                result = transcribe_video_file(
                    video_path=podcast_path,
                    output_dir=transcripts_dir,
                    model=whisper_model,
                    language=language,
                    device="cpu"
                )
            console.print(f"✅ Transcripción completada: {result['json_path']}")
        else:
            console.print(f"✅ Transcripción encontrada: {transcript_path}")
        
        # Paso 2: Segmentar con IA
        console.print("\n🤖 [bold magenta]Paso 2: Segmentando con IA...[/bold magenta]")
        
        config = AISegmentationConfig(max_clips=max_shorts + 2)  # Pedir un poco más
        segmenter = AITranscriptSegmenter(config)
        
        keywords_list = None
        if keywords.strip():
            keywords_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
            console.print(f"🔍 Palabras clave: {', '.join(keywords_list)}")
        
        with console.status("Analizando contenido con ChatGPT..."):
            candidates = segmenter.segment_transcript(
                transcript_path,
                keywords_filter=keywords_list
            )
        
        console.print(f"✅ IA encontró {len(candidates)} clips candidatos")
        
        # Exportar candidatos IA
        ai_candidates_path = segments_dir / f"{base_name}_ai_candidates.json"
        export_data = {
            "candidates": [
                {
                    "id": c.id,
                    "start_time": c.start_time,
                    "end_time": c.end_time,
                    "duration": c.duration,
                    "text": c.text,
                    "keywords": c.keywords,
                    "score": c.score,
                    "metadata": c.metadata
                } for c in candidates
            ],
            "metadata": {
                "generated_by": "AI",
                "model": config.model,
                "total_candidates": len(candidates)
            }
        }
        
        with open(ai_candidates_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        # Mostrar top clips
        if candidates:
            console.print("\n🏆 [bold]Top clips seleccionados:[/bold]")
            for i, candidate in enumerate(candidates[:max_shorts], 1):
                metadata = candidate.metadata
                title = metadata.get("title", "Sin título")
                viral_score = metadata.get("viral_potential", 0)
                content_type = metadata.get("content_type", "unknown")
                
                console.print(
                    f"   {i}. {candidate.formatted_duration} | "
                    f"Viral: {viral_score}/100 | "
                    f"Tipo: {content_type}"
                )
                console.print(f"      📝 {title}")
        
        # Paso 3: Componer Shorts
        console.print(f"\n🎬 [bold green]Paso 3: Componiendo {max_shorts} Shorts...[/bold green]")
        
        with console.status("Generando Shorts finales..."):
            results = compose_short_from_files(
                candidates_json=ai_candidates_path,
                podcast_video=podcast_path,
                broll_video=broll_path,
                transcript_json=transcript_path,
                output_dir=shorts_dir,
                max_shorts=max_shorts
            )
        
        # Resumen final
        successful_shorts = [r for r in results if r.get("success", False)]
        
        console.print(f"\n🎉 [bold green]Pipeline completo finalizado![/bold green]")
        console.print(f"   📹 Shorts creados: {len(successful_shorts)}")
        console.print(f"   📁 Ubicación: {shorts_dir}")
        
        if successful_shorts:
            console.print("\n📊 [bold]Shorts generados:[/bold]")
            for i, result in enumerate(successful_shorts, 1):
                file_path = result["output_path"]
                duration = result["duration"]
                file_size = result["file_size_mb"]
                console.print(f"   {i}. {file_path.name} ({duration:.1f}s, {file_size:.1f}MB)")
        
        console.print(f"\n💡 [yellow]Para ver los videos:[/yellow] xdg-open {shorts_dir}")
    
    except (TranscriptionError, SegmentationError, CompositionError) as e:
        console.print(f"❌ [red]Error en el pipeline: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ [red]Error inesperado: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def compose(
    candidates_path: str = typer.Argument(..., help="Ruta al archivo de candidatos JSON"),
    podcast_video: str = typer.Argument(..., help="Ruta al video de podcast"),
    broll_video: str = typer.Argument(..., help="Ruta al video de B-roll"),
    transcript_path: str = typer.Argument(..., help="Ruta al archivo de transcripción JSON"),
    output_dir: str = typer.Option("data/shorts", help="Directorio de salida"),
    max_shorts: int = typer.Option(3, help="Máximo número de Shorts a crear"),
    no_subtitles: bool = typer.Option(False, help="No incluir subtítulos quemados")
):
    """Componer Shorts finales con layout dual-panel."""
    from pathlib import Path
    from .pipeline.editor import compose_short_from_files, CompositionError
    
    console.print(f"🎬 [bold]Componiendo Shorts:[/bold] {max_shorts} shorts máximo")
    
    # Verificar archivos de entrada
    files_to_check = {
        "Candidatos": Path(candidates_path),
        "Video podcast": Path(podcast_video), 
        "Video B-roll": Path(broll_video),
        "Transcripción": Path(transcript_path)
    }
    
    for name, file_path in files_to_check.items():
        if not file_path.exists():
            console.print(f"❌ [red]{name} no encontrado: {file_path}[/red]")
            raise typer.Exit(1)
    
    output_path = Path(output_dir)
    
    try:
        with console.status("Componiendo Shorts..."):
            results = compose_short_from_files(
                podcast_video=Path(podcast_video),
                broll_video=Path(broll_video),
                transcript_json=Path(transcript_path),
                candidates_json=Path(candidates_path),
                output_dir=output_path,
                max_shorts=max_shorts
            )
        
        # Mostrar resultados
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]
        
        console.print("✅ [green]Composición completada[/green]")
        console.print(f"   📹 Shorts creados: {len(successful)}")
        console.print(f"   ❌ Errores: {len(failed)}")
        
        if successful:
            console.print("\n🎯 [bold]Shorts creados exitosamente:[/bold]")
            for i, result in enumerate(successful, 1):
                duration = result.get("duration", 0)
                file_size_mb = result.get("file_size", 0) / (1024 * 1024)
                console.print(
                    f"   {i}. {Path(result['output_path']).name} "
                    f"({duration:.1f}s, {file_size_mb:.1f}MB)"
                )
        
        if failed:
            console.print("\n❌ [bold]Errores en composición:[/bold]")
            for result in failed:
                console.print(f"   • {result['candidate_id']}: {result.get('error', 'Error desconocido')}")
        
        console.print(f"\n📁 Archivos guardados en: {output_path}")
    
    except CompositionError as e:
        console.print(f"❌ [red]Error en composición: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def publish(
    limit: Annotated[int, typer.Option("--limit", help="Límite de publicaciones")] = 1,
    schedule: Annotated[bool, typer.Option("--schedule", help="Programar publicación")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Simular sin publicar")] = False,
):
    """📤 Publicar Shorts en YouTube usando API oficial."""
    rprint("[yellow]📤 Publicando en YouTube...[/yellow]")
    
    # TODO: Implementar publisher.py
    rprint(f"[blue]📊 Límite:[/blue] {limit}")
    rprint(f"[blue]⏰ Programar:[/blue] {schedule}")
    rprint(f"[blue]🔍 Dry run:[/blue] {dry_run}")
    rprint("[yellow]⚠️  Funcionalidad pendiente de implementar[/yellow]")


@app.command()
def status():
    """📊 Mostrar estado actual del pipeline."""
    rprint(Panel.fit(
        "[bold blue]📊 Estado del Pipeline[/bold blue]\n\n"
        "[dim]🔍 Videos descubiertos:[/dim] 0\n"
        "[dim]⬇️  Videos descargados:[/dim] 0\n"
        "[dim]📝 Transcripciones:[/dim] 0\n"
        "[dim]✂️  Clips generados:[/dim] 0\n"
        "[dim]🎬 Shorts compuestos:[/dim] 0\n"
        "[dim]📤 Publicados:[/dim] 0\n\n"
        "[yellow]⚠️  Base de datos no inicializada[/yellow]",
        title="Estado",
    ))


@app.command()
def config(
    show: Annotated[bool, typer.Option("--show", help="Mostrar configuración actual")] = False,
    validate: Annotated[bool, typer.Option("--validate", help="Validar configuración")] = False,
):
    """⚙️ Gestionar configuración del pipeline."""
    if show:
        rprint("[blue]📋 Configuración actual:[/blue]")
        # TODO: Leer y mostrar configuración de .env y configs/
        rprint("[yellow]⚠️  Funcionalidad pendiente de implementar[/yellow]")
    
    if validate:
        rprint("[blue]✅ Validando configuración...[/blue]")
        # TODO: Validar archivos de configuración
        rprint("[yellow]⚠️  Funcionalidad pendiente de implementar[/yellow]")


@app.command()
def doctor():
    """🩺 Diagnosticar problemas del sistema."""
    rprint("[yellow]🩺 Ejecutando diagnósticos...[/yellow]")
    
    # Verificar Python
    python_version = sys.version_info
    if python_version >= (3, 11):
        rprint("[green]✅ Python 3.11+ detectado[/green]")
    else:
        rprint("[red]❌ Se requiere Python 3.11+[/red]")
    
    # Verificar estructura de carpetas
    data_dir = Path("data")
    if data_dir.exists():
        rprint("[green]✅ Estructura de carpetas creada[/green]")
    else:
        rprint("[red]❌ Falta estructura de carpetas (ejecuta 'make setup')[/red]")
    
    # Verificar .env
    env_file = Path(".env")
    if env_file.exists():
        rprint("[green]✅ Archivo .env encontrado[/green]")
    else:
        rprint("[yellow]⚠️  Archivo .env no encontrado (copia .env.example)[/yellow]")
    
    rprint("[blue]💡 Para más diagnósticos, ejecuta 'make doctor'[/blue]")


if __name__ == "__main__":
    app()
