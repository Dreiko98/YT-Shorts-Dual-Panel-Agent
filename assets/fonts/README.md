# 🎨 Fuentes Necesarias

Para el funcionamiento óptimo del pipeline, necesitas instalar estas fuentes:

## Fuentes Principales

### 1. Montserrat (Títulos)
- **URL:** https://fonts.google.com/specimen/Montserrat
- **Pesos necesarios:** Regular (400), SemiBold (600), Bold (700), ExtraBold (800)
- **Uso:** Títulos y textos destacados

### 2. Inter (Subtítulos)  
- **URL:** https://fonts.google.com/specimen/Inter
- **Pesos necesarios:** Regular (400), Medium (500), SemiBold (600)
- **Uso:** Subtítulos y texto corrido

### 3. JetBrains Mono (Código - Opcional)
- **URL:** https://www.jetbrains.com/lp/mono/
- **Pesos necesarios:** Regular (400), Medium (500)
- **Uso:** Código y elementos técnicos

## Instalación en Linux

### Opción 1: Sistema completo
```bash
# Instalar desde repositorios
sudo apt install fonts-google-montserrat fonts-inter

# O descargar manualmente:
# 1. Descarga los .ttf de Google Fonts
# 2. Copia a ~/.local/share/fonts/
# 3. Ejecuta: fc-cache -fv
```

### Opción 2: Solo para el proyecto
```bash
# Crear carpeta de fuentes del proyecto
mkdir -p assets/fonts/montserrat
mkdir -p assets/fonts/inter
mkdir -p assets/fonts/jetbrains-mono

# Coloca aquí los archivos .ttf descargados
```

## Fuentes Fallback

Si no tienes las fuentes principales, el sistema usará:
- **Montserrat** → Arial, Helvetica, sans-serif
- **Inter** → Helvetica, Arial, sans-serif  
- **JetBrains Mono** → Consolas, Monaco, monospace

## Verificación

Para verificar que las fuentes están instaladas:
```bash
fc-list | grep -i montserrat
fc-list | grep -i inter
```
