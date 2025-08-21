#!/usr/bin/env python3
from pathlib import Path

print("Buscando todos los archivos .mp4 en el proyecto...")

root = Path('.')
mp4s = list(root.rglob('*.mp4'))

if not mp4s:
    print("No se encontraron archivos .mp4 en el proyecto.")
else:
    print(f"Se encontraron {len(mp4s)} archivos .mp4:")
    for f in mp4s:
        try:
            size = f.stat().st_size
            print(f"- {f}  ({size/1024:.1f} KB)")
        except Exception as e:
            print(f"- {f}  (error leyendo tamaño: {e})")
