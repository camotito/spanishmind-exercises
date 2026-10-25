# CLAUDE.md

Ver `README.md` para el resumen corto.

## Estructura de carpetas

- **`content/`** — banco final que se sirve, uno por tema (`<tema>.json`). Editado a mano y/o con ayuda de LLM a partir de `ejemplos/`. `render.py` lee de aquí.
- **`ejemplos/`** — banco crudo de las 126 unidades del libro ya extraídas y fusionadas (pipeline completo, ver `libro_pipeline/`). Fuente de verdad para curaduría a nivel de todo el libro (p. ej. `grafico_necesario`), incluso para unidades que todavía no están en `content/`. Cada ejercicio trae `"subejercicio": "<unidad>.<n>"` (p. ej. `"74.1"`) para relacionarlo con el libro físico.
- **`libro_pipeline/`** — scripts del pipeline de digitalización: `extract_toc.py`/`extract_ejercicios.py`/`extract_soluciones.py` (OCR/vision sobre los escaneos), `merge_ejemplos.py` (cruza `ejercicios_raw/` + `soluciones.json` → `ejemplos/<tema>.json`), `clasificar_otros.py`/`aplicar_tipologias.py` (asignación de tipologías T8-T16), `sync_ejercicios_permitidos.py` (sincroniza `index.yaml`). Datos intermedios: `mapa_unidades.json` (unidad → página/escaneo), `soluciones.json` (solucionario del libro), `asignacion_tipologias.json`.
- **`libro/`** — escaneos página por página (`libro-rojo-NNN.png`, NNN = número de página física, gitignored por tamaño/derechos). Usar `mapa_unidades.json` para encontrar la página de una unidad concreta (`pagina_ejercicios`/`scan_ejercicios`).
- **`dashboard/`** — editor local de contenido, solo localhost (`python3 dashboard/server.py`). `index.html` = panel de "Contenido" (editar enunciado/ítems/soluciones, ocultar ejercicios, forzar ejemplo) + pestaña "Índice del libro". `tipologias.html` = catálogo T1-T16 con toggle de activación, hoja aparte. `server.py` expone `/api/temas`, `/api/content/<tema>`, `/api/tipologias`, `/api/tipologias-config`, `/api/sync-permitidos`.
- **`Gemini/`** — `Exercises_typology.md` es la fuente de verdad de las descripciones de tipologías (T1-T16), consumida en vivo por `dashboard/server.py` (no se duplica en JSON).
- **`out/`** — salida del build (`render.py` + `build_index.py`), lo que se publica en Netlify.
- **`content/<tema>.conjugacion.json`** — tablas de conjugación opcionales (botón de tabla en la página, columnas con igual conjugación fusionadas). `build_pdfs.py` genera `out/pdf/<tema>-conjugacion.pdf` con Chrome sin ventana; Netlify no tiene Chrome, así que los PDF se commitean. El hook `.githooks/pre-commit` (activar una vez por clon: `git config core.hooksPath .githooks`) regenera `out/` y los PDF en cada commit que toque `content/` o el render.
- **`out_preview/`** — salida de variantes experimentales (p. ej. `render.py --paginar=item`), no se sirve ni se integra al build.
- **`index.yaml`** — grafo de dependencias entre temas: `tema`, `titulo`, `unidad_libro` (número de unidad en el libro si viene de ahí, cruza con `ejemplos/<tema>.json`), `depende_de`, `ejercicios_permitidos`, `tiempos_permitidos`.
- **`render_config.json`** — qué tipologías están desactivadas por defecto en el renderizado (hoy `T2`, sin imágenes reales todavía). Editable a mano o desde `dashboard/tipologias.html`.

## Piezas clave de `render.py`

- Tokenizador único (`tokenize_events`) cubre huecos libres (`_____`), elección inline `(a/b)` y estímulo en cursiva `(palabra)` sin barra — compartido por ítems normales y por el ejemplo resuelto.
- `grafico_necesario` (bool, por ejercicio): si el gráfico del libro es decorativo (el texto del ítem ya trae todo) se omite el sustituto en texto. Calculado a mano contra el libro real, no con heurística — ver el campo en `ejemplos/*.json`.
- El ejemplo resuelto (primer ítem ya completado, como en el libro) solo se muestra si el enunciado menciona "example(s)" o `forzar_ejemplo: true`.
- Paginación: cada tema se sirve como una serie de páginas (una por ejercicio por defecto) navegables con JS client-side, no una sola página larga.

## Convenciones de trabajo

- **Commit por paso, push solo cuando Javi lo pida**: cada cambio significativo se commitea, pero nunca se hace `git push` por iniciativa propia (cada push despliega en Netlify y gasta créditos del nivel gratis). Los cambios se prueban siempre en local antes (`python3 render.py && python3 build_index.py`, servidor en `out/`, p. ej. `python3 -m http.server 8765`). Javi pide el push cuando todo está listo y depurado.
- **Curaduría de datos contra el libro real cuando haga falta** (imágenes necesarias, subrayados, tablas faltantes): si hay escaneo disponible en `libro/`, verificar ahí antes de asumir un patrón por el enunciado o la tipología — el enunciado por sí solo no siempre predice si algo está subrayado o no en el libro impreso.
