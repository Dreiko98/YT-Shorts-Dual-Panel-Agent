# 🖼️ Logo y Branding

## Logo Principal

### Requerido: `logo.png`
- **Resolución:** 512x512 píxeles mínimo  
- **Formato:** PNG con transparencia
- **Uso:** Watermark en videos, thumbnails
- **Colores sugeridos:** #FF6B35 (naranja), #004E89 (azul)

### Creación Manual

Si no tienes logo, puedes:

1. **Usar herramientas online:**
   - Canva: https://www.canva.com/logos/
   - LogoMaker: https://www.logomaker.com/
   
2. **Crear con GIMP/Photoshop:**
   - Canvas: 512x512px
   - Fondo transparente  
   - Texto: "YT" o tu marca
   - Color: #FF6B35

3. **Logo temporal por ahora:**
   - El sistema usará texto "YT" como fallback
   - Configurado en configs/branding.yaml

## Verificación

Para verificar que el logo está bien:
```bash
file assets/logo.png
# Debería mostrar: PNG image data, 512 x 512, ...
```

## Próximos pasos

Una vez tengas logo propio:
1. Guárdalo como `assets/logo.png`  
2. Ejecuta `make test` para verificar
3. Los videos usarán tu logo automáticamente
