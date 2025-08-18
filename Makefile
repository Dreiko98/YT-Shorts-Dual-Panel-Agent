.PHONY: help setup doctor clean lint test discover download normalize transcribe segment compose publish

# Variables
PYTHON := python3
PIP := pip3
VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip

# Default target
help:
	@echo "🎬 YT Shorts Dual-Panel Agent"
	@echo ""
	@echo "Targets disponibles:"
	@echo "  setup       - Instalar dependencias y crear estructura"
	@echo "  doctor      - Verificar prerequisitos del sistema"
	@echo "  clean       - Limpiar archivos temporales"
	@echo ""
	@echo "Pipeline:"
	@echo "  discover    - Descubrir nuevos episodios (requiere API)"
	@echo "  download    - Descargar podcasts pendientes"
	@echo "  normalize   - Normalizar audio/video"
	@echo "  transcribe  - Generar transcripciones con Whisper"
	@echo "  segment     - Crear clips candidatos (método tradicional)"
	@echo "  segment-ai  - Crear clips candidatos con IA (ChatGPT) 🤖"
	@echo "  compose     - Generar Shorts finales"
	@echo "  publish     - Subir a YouTube (requiere OAuth)"
	@echo ""
	@echo "Pipeline Completo:"
	@echo "  pipeline-ai - Todo en uno: transcribir → IA → componer 🚀"
	@echo ""
	@echo "Desarrollo:"
	@echo "  lint        - Ejecutar linting (ruff + black)"
	@echo "  test        - Ejecutar tests"
	@echo "  compose-test - Prueba rápida con archivos de ejemplo"

# Setup del entorno
setup: $(VENV_DIR)
	@echo "🔧 Configurando entorno virtual..."
	$(VENV_PIP) install --upgrade pip setuptools wheel
	$(VENV_PIP) install -e ".[dev]"
	@echo "📁 Creando estructura de carpetas..."
	mkdir -p data/raw/podcast data/raw/broll/subway data/raw/broll/parkour data/raw/broll/asmr
	mkdir -p data/normalized/podcast data/normalized/broll
	mkdir -p data/transcriptions data/segments data/composites data/logs
	mkdir -p assets/fonts assets/frames assets/permissions
	mkdir -p tests
	@echo "📄 Copiando archivos de configuración..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "⚠️  Recuerda configurar .env con tus credenciales"; fi
	@echo "✅ Setup completo! Ejecuta 'make doctor' para verificar."

$(VENV_DIR):
	@echo "🐍 Creando entorno virtual..."
	$(PYTHON) -m venv $(VENV_DIR)

# Verificar prerequisitos
doctor:
	@echo "🩺 Verificando prerequisitos del sistema..."
	@echo -n "Python 3.11+: "
	@$(PYTHON) -c "import sys; print('✅' if sys.version_info >= (3, 11) else '❌'); exit(0 if sys.version_info >= (3, 11) else 1)"
	@echo -n "ffmpeg: "
	@ffmpeg -version >/dev/null 2>&1 && echo "✅" || echo "❌ No encontrado"
	@echo -n "yt-dlp (via pip): "
	@$(VENV_PYTHON) -c "import yt_dlp; print('✅')" 2>/dev/null || echo "❌ No instalado"
	@echo -n "Whisper: "
	@$(VENV_PYTHON) -c "import whisper; print('✅')" 2>/dev/null || echo "❌ No instalado"
	@echo -n "Estructura de carpetas: "
	@[ -d "data/raw/podcast" ] && [ -d "data/raw/broll" ] && echo "✅" || echo "❌ Faltan carpetas"
	@echo -n "Archivo .env: "
	@[ -f ".env" ] && echo "✅" || echo "❌ Falta archivo .env"
	@echo ""
	@echo "💡 Si hay errores, ejecuta 'make setup' primero"

# Limpieza
clean:
	@echo "🧹 Limpiando archivos temporales..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ 2>/dev/null || true
	@echo "✅ Limpieza completa"

# Desarrollo
lint: $(VENV_DIR)
	@echo "🔍 Ejecutando linting..."
	$(VENV_PYTHON) -m black --check src/ tests/
	$(VENV_PYTHON) -m ruff check src/ tests/
	@echo "✅ Linting completo"

lint-fix: $(VENV_DIR)
	@echo "🔧 Aplicando correcciones de linting..."
	$(VENV_PYTHON) -m black src/ tests/
	$(VENV_PYTHON) -m ruff check --fix src/ tests/
	@echo "✅ Correcciones aplicadas"

test: $(VENV_DIR)
	@echo "🧪 Ejecutando tests..."
	$(VENV_PYTHON) -m pytest tests/ -v
	@echo "✅ Tests completos"

# Pipeline commands
discover: $(VENV_DIR)
	@echo "🔍 Descubriendo nuevos episodios..."
	$(VENV_PYTHON) -m src.cli discover

download: $(VENV_DIR)
	@echo "⬇️  Descargando podcasts pendientes..."
	$(VENV_PYTHON) -m src.cli download

normalize: $(VENV_DIR)
	@echo "🎵 Normalizando audio/video..."
	$(VENV_PYTHON) -m src.cli normalize

transcribe: $(VENV_DIR)
	@echo "🎤 Transcribiendo video..."
	@if [ -z "$(VIDEO)" ]; then echo "❌ Especifica VIDEO=ruta/al/video.mp4"; exit 1; fi
	$(VENV_PYTHON) -m src.cli transcribe $(VIDEO) --output-dir $(or $(OUTPUT_DIR),data/transcripts) --model $(or $(MODEL),base) $(if $(LANG),--language $(LANG)) --device $(or $(DEVICE),auto)

segment: $(VENV_DIR)
	@echo "✂️ Segmentando transcripción (método tradicional)..."
	@if [ -z "$(TRANSCRIPT)" ]; then echo "❌ Especifica TRANSCRIPT=ruta/al/transcript.json"; exit 1; fi
	$(VENV_PYTHON) -m src.cli segment $(TRANSCRIPT) --output-dir $(or $(OUTPUT_DIR),data/segments) $(if $(KEYWORDS),--keywords "$(KEYWORDS)") --min-duration $(or $(MIN_DUR),15) --max-duration $(or $(MAX_DUR),59)

segment-ai: $(VENV_DIR)
	@echo "🤖 Segmentando transcripción con IA..."
	@if [ -z "$(TRANSCRIPT)" ]; then echo "❌ Especifica TRANSCRIPT=ruta/al/transcript.json"; exit 1; fi
	@if [ -z "$(OPENAI_API_KEY)" ]; then echo "❌ Configura OPENAI_API_KEY en .env"; exit 1; fi
	$(VENV_PYTHON) -m src.cli segment-ai $(TRANSCRIPT) --output-dir $(or $(OUTPUT_DIR),data/segments) $(if $(KEYWORDS),--keywords "$(KEYWORDS)") --max-clips $(or $(MAX_CLIPS),5) --min-duration $(or $(MIN_DUR),15) --max-duration $(or $(MAX_DUR),59)

pipeline-ai: $(VENV_DIR)
	@echo "🚀 Ejecutando pipeline completo con IA..."
	@if [ -z "$(PODCAST)" ]; then echo "❌ Especifica PODCAST=ruta/podcast.mp4"; exit 1; fi
	@if [ -z "$(BROLL)" ]; then echo "❌ Especifica BROLL=ruta/broll.mp4"; exit 1; fi
	@if [ -z "$(OPENAI_API_KEY)" ]; then echo "❌ Configura OPENAI_API_KEY en .env"; exit 1; fi
	$(VENV_PYTHON) -m src.cli pipeline-ai $(PODCAST) $(BROLL) $(if $(KEYWORDS),--keywords "$(KEYWORDS)") --max-shorts $(or $(MAX_SHORTS),3) --whisper-model $(or $(MODEL),small) --language $(or $(LANG),es) --output-base $(or $(OUTPUT_BASE),data)

compose: $(VENV_DIR)
	@echo "🎬 Componiendo Shorts..."
	@if [ -z "$(CANDIDATES)" ]; then echo "❌ Especifica CANDIDATES=ruta/candidates.json"; exit 1; fi
	@if [ -z "$(PODCAST)" ]; then echo "❌ Especifica PODCAST=ruta/podcast.mp4"; exit 1; fi
	@if [ -z "$(BROLL)" ]; then echo "❌ Especifica BROLL=ruta/broll.mp4"; exit 1; fi
	@if [ -z "$(TRANSCRIPT)" ]; then echo "❌ Especifica TRANSCRIPT=ruta/transcript.json"; exit 1; fi
	$(VENV_PYTHON) -m src.cli compose $(CANDIDATES) $(PODCAST) $(BROLL) $(TRANSCRIPT) --output-dir $(or $(OUTPUT_DIR),data/shorts) --max-shorts $(or $(MAX_SHORTS),3) $(if $(NO_SUBS),--no-subtitles)

publish: $(VENV_DIR)
	@echo "📤 Publicando en YouTube..."
	$(VENV_PYTHON) -m src.cli publish

# Test rápido con archivos de ejemplo
compose-test: $(VENV_DIR)
	@echo "🎯 Prueba rápida de composición..."
	@echo "💡 Asegúrate de tener:"
	@echo "   - Un archivo .mp4 en data/raw/podcast/"
	@echo "   - Archivos de B-roll en data/raw/broll/subway/"
	$(VENV_PYTHON) -m src.cli compose --test-mode
	@echo "✅ Revisa data/composites/ para ver el resultado"

# Información del entorno
info:
	@echo "📊 Información del entorno:"
	@echo "Python: $(shell $(VENV_PYTHON) --version 2>&1)"
	@echo "Pip packages:"
	@$(VENV_PIP) list | grep -E "(whisper|moviepy|yt-dlp|typer)" || echo "  Ningún paquete relevante instalado"
	@echo "Espacio disponible:"
	@df -h data/ 2>/dev/null | tail -1 || echo "  Carpeta data/ no encontrada"
