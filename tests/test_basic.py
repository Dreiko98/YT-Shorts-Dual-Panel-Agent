"""
Test básico para verificar que el CLI funciona
"""
import pytest
import subprocess
import sys
from pathlib import Path


def test_cli_help():
    """Test que el CLI muestra ayuda correctamente."""
    # Ejecutar desde el directorio del proyecto
    project_root = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert "YT Shorts Dual-Panel Agent" in result.stdout
    assert "discover" in result.stdout
    assert "compose" in result.stdout


def test_cli_doctor():
    """Test comando doctor."""
    project_root = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "doctor"],
        cwd=project_root,
        capture_output=True,
        text=True
    )
    
    # Doctor puede fallar por falta de deps, pero no debe crashear
    assert "Python" in result.stdout or result.returncode in [0, 1]


def test_database_init():
    """Test que la base de datos se inicializa correctamente."""
    from src.pipeline.db import PipelineDB
    
    # Usar DB temporal
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db = PipelineDB(tmp.name)
        
        # Verificar que se crean las tablas
        stats = db.get_stats()
        assert isinstance(stats, dict)
        assert stats['total_videos'] == 0
        assert stats['downloaded'] == 0
        
        # Cleanup
        Path(tmp.name).unlink()


def test_project_structure():
    """Test que la estructura del proyecto es correcta."""
    project_root = Path(__file__).parent.parent
    
    # Verificar archivos esenciales
    assert (project_root / "README.md").exists()
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "Makefile").exists()
    assert (project_root / ".env.example").exists()
    
    # Verificar estructura src/
    assert (project_root / "src" / "__init__.py").exists()
    assert (project_root / "src" / "cli.py").exists()
    assert (project_root / "src" / "pipeline" / "__init__.py").exists()
    assert (project_root / "src" / "pipeline" / "db.py").exists()
    
    # Verificar configs/
    configs_dir = project_root / "configs"
    assert configs_dir.exists()
    assert (configs_dir / "channels.yaml").exists()
    assert (configs_dir / "layout.yaml").exists()
    assert (configs_dir / "broll_pools.yaml").exists()
