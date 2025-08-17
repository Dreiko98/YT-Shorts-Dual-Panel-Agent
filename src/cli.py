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
    model: Annotated[
        str, 
        typer.Option("--model", "-m", help="Modelo de Whisper")
    ] = "base",
    device: Annotated[
        str, 
        typer.Option("--device", "-d", help="Dispositivo (cpu/cuda)")
    ] = "cpu",
    language: Annotated[
        Optional[str], 
        typer.Option("--lang", "-l", help="Idioma forzado (es, en, etc.)")
    ] = None,
):
    """📝 Generar transcripciones usando Whisper local."""
    rprint("[yellow]📝 Generando transcripciones...[/yellow]")
    
    # TODO: Implementar transcribe.py
    rprint(f"[blue]🤖 Modelo Whisper:[/blue] {model}")
    rprint(f"[blue]💻 Dispositivo:[/blue] {device}")
    if language:
        rprint(f"[blue]🌍 Idioma:[/blue] {language}")
    rprint("[yellow]⚠️  Funcionalidad pendiente de implementar[/yellow]")


@app.command()
def segment(
    min_duration: Annotated[int, typer.Option("--min", help="Duración mínima en segundos")] = 20,
    max_duration: Annotated[int, typer.Option("--max", help="Duración máxima en segundos")] = 60,
    max_clips: Annotated[int, typer.Option("--clips", help="Máximo clips por vídeo")] = 3,
):
    """✂️ Crear clips candidatos basado en transcripciones."""
    rprint("[yellow]✂️  Creando clips candidatos...[/yellow]")
    
    # TODO: Implementar segmenter.py
    rprint(f"[blue]⏱️  Duración:[/blue] {min_duration}s - {max_duration}s")
    rprint(f"[blue]📊 Máximo clips:[/blue] {max_clips}")
    rprint("[yellow]⚠️  Funcionalidad pendiente de implementar[/yellow]")


@app.command()
def compose(
    test_mode: Annotated[bool, typer.Option("--test-mode", help="Modo de prueba con archivos locales")] = False,
    layout: Annotated[str, typer.Option("--layout", help="Layout a usar")] = "default",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Simular sin generar archivos")] = False,
):
    """🎬 Componer Shorts finales con dual-panel y subtítulos."""
    rprint("[yellow]🎬 Componiendo Shorts finales...[/yellow]")
    
    if test_mode:
        rprint("[blue]🎯 Modo de prueba activado[/blue]")
        rprint("[dim]Buscando archivos de ejemplo en data/raw/...[/dim]")
    
    # TODO: Implementar editor.py + layout.py + subtitles.py
    rprint(f"[blue]🎨 Layout:[/blue] {layout}")
    rprint(f"[blue]🔍 Dry run:[/blue] {dry_run}")
    rprint("[yellow]⚠️  Funcionalidad pendiente de implementar[/yellow]")


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
