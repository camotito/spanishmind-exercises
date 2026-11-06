# spanishmind-exercises

Ejercicios interactivos de gramática española, autocorregibles, generados a partir de "Gramática de uso del español" (Aragonés/Palencia) y desplegados como sitio estático.

- `render.py` + `content/*.json` → `out/*.html` (páginas de ejercicios)
- `build_index.py` → `out/index.html` (portada, solo las unidades ya publicadas)
- `libro_pipeline/` — pipeline de digitalización del libro (banco crudo en `ejemplos/`)
- `dashboard/` — editor local de contenido (`python3 dashboard/server.py`)
- `index.yaml` — grafo de dependencias entre unidades, tiempos verbales y tipologías permitidas

Desplegado en Netlify (`netlify.toml`: build = `render.py` + `build_index.py`, publish = `out/`).

Publicado: https://spanish-exes.netlify.app/ (dominio previsto: `ejercicios.spanishmind.se`).

## Extracción de libros escaneados (lecciones)

Pipeline en `~/Documents/Proyectos/web-apps/web-exes-static/libro_pipeline/` (hecho con el libro de Aragonés y Palencia, A1-B2, 126 unidades). Pasos: índice, mapa unidad→página, ejercicios de cada unidad a JSON, solucionario aparte y cruce de los dos (`merge_ejemplos.py`). Lo que se aprendió:

- **Visión de IA, no OCR clásico, y el proveedor importa.** Con el solucionario (letra pequeña, respuestas cortas parecidas como lo/la/le), Gemini 3.1 Flash Lite y GPT-5.6-sol cometieron errores de contenido. En 5 discrepancias comprobadas contra el libro físico, GPT-5.6-sol acertó las 5 y Gemini falló las 5. Desde el 15 de julio de 2026 el proveedor por defecto es OpenAI; Gemini solo para contrastar.
- **Nunca pedir respuestas a la página del ejercicio.** Las respuestas salen solo del solucionario impreso. Así no se inventa nada.
- **Validar y marcar, no corregir en silencio.** El cruce compara huecos con respuestas y marca `revisar: true` (hubo 280 avisos en 25 unidades). Verificar contra el escaneo.
- **No forzar un esquema JSON estricto** en gráficos y datos de forma variable: degrada la lectura.
- **Contrastar con el libro físico** cuando una unidad dependa de subrayados, tablas o imágenes.

### Varios libros

El pipeline acepta `--libro <nombre>` (por defecto `a1-b2`, el original). Cada libro nuevo vive en `libros/<nombre>/` con su `libro.json` (ruta del PDF y offset de paginación), sus imágenes, su mapa y su salida. No toca `ejemplos/`, `content/` ni `index.yaml`.

- Si el libro es un PDF de imágenes, `render_pdf.py` lo pasa a una imagen por página.
- **El offset de paginación no es constante** si al PDF le faltan páginas. Comprobar el número impreso al final de varias páginas repartidas (`cambios_offset` en `libro.json`).
- El número de unidad lo da el índice, no la página: el modelo llegó a leer la pestaña "34" como "43".
- Libro C1-C2 (`libros/c1-c2/`, 106 unidades): mapa, ejercicios y solucionario extraídos. Al PDF le falta la teoría de la unidad 34 (página impresa 76).
- Su índice para otros agentes es `libros/c1-c2/indice.md`, generado con `libro_pipeline/build_indice.py`. Incluye `auto: sí/no` por ejercicio (si la web lo corrige sola), las disputas de solución y un resumen de teoría solo en las unidades 57 a 70 y 106 (`teoria.json`). No se edita a mano: se regenera.
- Quedan por resolver las 35 disputas de solución entre Flash y Pro (`disputas_soluciones.json`).
