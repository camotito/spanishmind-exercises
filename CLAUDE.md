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
- **`progresion.yaml`** — etapas del curso en el orden en que Javi las enseña (fuente: `contenido-clases/mapa/progresion/progresion-gruesa.md`). Cada tema publicado lleva `etapa:` en `index.yaml`. `build_index.py` agrupa la portada por etapa y, dentro de cada una, por orden topológico de `depende_de`; falla si una etapa contradice el grafo (un tema no puede ir en una etapa anterior a la de algo de lo que depende). El grafo de dependencias es la fuente de qué conocimiento previo tiene cada tema.
- **`herramientas/`** — `audit_movil.py` (móvil, ver flujo) y `check_gramatica_vista.py` (avisa de gramática no vista: *nosotros*, *vosotros*, reflexivos y pasados que el grafo no permite al tema). `teoria_md.py` (en la raíz) convierte la teoría escrita en Markdown a `content/<tema>.teoria.html`. `borradores/` guarda temas sin validar, fuera de `content/`.
- **`render_config.json`** — qué tipologías están desactivadas por defecto en el renderizado (hoy `T2`, sin imágenes reales todavía). Editable a mano o desde `dashboard/tipologias.html`.

## Piezas clave de `render.py`

- Tokenizador único (`tokenize_events`) cubre huecos libres (`_____`), elección inline `(a/b)` y estímulo en cursiva `(palabra)` sin barra — compartido por ítems normales y por el ejemplo resuelto.
- `grafico_necesario` (bool, por ejercicio): si el gráfico del libro es decorativo (el texto del ítem ya trae todo) se omite el sustituto en texto. Calculado a mano contra el libro real, no con heurística — ver el campo en `ejemplos/*.json`.
- El ejemplo resuelto (primer ítem ya completado, como en el libro) solo se muestra si el enunciado menciona "example(s)" o `forzar_ejemplo: true`.
- Paginación: cada tema se sirve como una serie de páginas (una por ejercicio por defecto) navegables con JS client-side, no una sola página larga.

## Convenciones de trabajo

- **Commit por paso, push solo cuando Javi lo pida**: cada cambio significativo se commitea, pero nunca se hace `git push` por iniciativa propia (cada push despliega en Netlify y gasta créditos del nivel gratis). Los cambios se prueban siempre en local antes (`python3 render.py && python3 build_index.py`, servidor en `out/`, p. ej. `python3 -m http.server 8765`). Javi pide el push cuando todo está listo y depurado. Una orden de publicar vale solo para ese push: después, todo vuelve a ser en local hasta la siguiente orden. Cualquier otra publicación a Netlify (deploy, CLI, etc.) sigue la misma regla.
- **Pedir el OK siempre con la URL local (regla de Javi, 26 nov 2026).** Todo cambio para Netlify espera su OK antes de publicarse. Al pedirlo, dejar arrancado el servidor local (`python3 -m http.server 8765` en `out/`) y dar la URL exacta de cada página cambiada (ej. `http://localhost:8765/referencia/a-personal.html`). Sin URL, Javi no puede revisar ni dar el OK.
- **Curaduría de datos contra el libro real cuando haga falta** (imágenes necesarias, subrayados, tablas faltantes): si hay escaneo disponible en `libro/`, verificar ahí antes de asumir un patrón por el enunciado o la tipología — el enunciado por sí solo no siempre predice si algo está subrayado o no en el libro impreso.

## Textos para alumnos (teoría, enunciados)

- Las reglas de pedagogía y de vocabulario gramatical (terminología mínima, Thinking Method, formato de equivalencias con `=` y sublistas) viven en `~/Documents/Proyectos/contenido-clases/CLAUDE.md`. No se duplican aquí: léelas antes de escribir o editar una hoja `*.teoria.html`.
- La fuente de una teoría se edita en Markdown en `contenido-clases/` y se convierte a `content/<tema>.teoria.html`.
- **De dónde sale la teoría de una unidad (regla de Javi, 1 nov 2026).** Fuente principal: la página de teoría del libro. Muchas unidades no tienen la teoría digitalizada: está solo como escaneo (`libro/libro-rojo-NNN.png`). La página de teoría de la unidad N es `pagina` en `libro_pipeline/mapa_unidades.json` (la de ejercicios es `pagina_ejercicios`), y el escaneo es esa página + 1 (unidad 9: página 26, `libro-rojo-027.png`). Se lee la imagen, no se asume por el enunciado.
- Después se combina con los apuntes y ejemplos propios de Javi en `contenido-clases/` (buscar primero ahí). Solo lo que falte tras las dos fuentes lo escribe la IA, avisando de que es nuevo. Ningún texto de teoría se escribe sin haber mirado antes el libro.
- Luego se aplican las reglas de estilo de `contenido-clases/CLAUDE.md` (inglés por defecto, terminología mínima, `=`, sin explicar lo que funciona como en inglés), se adapta al español de España y se revisa con Gemini o GPT.

## Referencia gramatical (la chuleta del alumno enlaza aquí)

- `referencia.yaml` lista una página por tema en `out/referencia/` (teoría, tablas y enlace a los ejercicios). Su `punto` es la ficha del árbol de `contenido-clases/mapa`: así `clase chuleta` deduce la última gramática del alumno.
- Una página puede cubrir varios puntos con `puntos:` (punto del árbol y ancla de su apartado). Las anclas las pone `teoria_md.py` a partir de cada cabecera, y la chuleta y los `para <Alumno>` enlazan al apartado (`página.html#ancla`).
- Páginas de principiantes (A1): sus fuentes son `contenido-clases/material/explicaciones/10-…` a `18-…`, juntadas de los apuntes que ya recibió Jake.
- **Por defecto, si el último punto que ha trabajado el alumno no tiene página aquí** (`clase chuleta ALUMNO` avisa con «Sin página de referencia para…»), se crea (regla de Javi, 23 nov 2026):
  1. Buscar antes apuntes locales en `contenido-clases/material/explicaciones` y en el Handbok A1 de Javi (`contenido-clases/referencias/fuentes-editables/Handbok i spanska Nivå A1 (Drive 2026-07-06).txt`, en sueco: se usa como fuente de ideas y ejemplos y se reescribe desde el inglés, nunca se traduce). Si no hay, transcribir del libro rojo (teoría de la unidad: `libro/libro-rojo-NNN.png`, `pagina` + 1 en `mapa_unidades.json`), con el estilo de `contenido-clases/CLAUDE.md`. El apunte se guarda en `contenido-clases/material/explicaciones/NN-<tema>.md` (borrador, `status` con la fuente) y se convierte con `teoria_md.py`.
  2. Ejercicios: `content/<tema>.json` desde `ejemplos/unidad-N.json` (enunciados en inglés) y su entrada en `index.yaml` (con `etapa`, de `progresion.yaml`).
  3. Entrada en `referencia.yaml` (`punto`, `resumen`, `teoria`, `practica`) y su nodo en `mapa/progresion/arbol.md` y `mapa/puntos/`.
  4. `render.py`, `build_index.py`, `build_referencia.py`, captura a 360 px y `audit_movil.py`. Publicar (push a Netlify y chuleta) solo con el OK de Javi.

## Borradores

- `borradores/` guarda temas escritos por IA que Javi aún no ha validado (marcados `[BORRADOR SIN REVISAR]`). Fuera de `content/`, no se renderizan ni se publican. Para publicarlos: moverlos a `content/` y quitar la marca del título (también en `index.yaml`).

## Flujo al generar o cambiar ejercicios

Objetivo (Javi, 1 nov 2026): que el alumno no tenga fricción visual ni mental y todo su espacio cognitivo quede para lo que el ejercicio entrena. Se comprueba siempre, en cada unidad nueva o cambiada, antes de darla por buena:

1. Renderizar y ver las páginas en local, con capturas a 360 px de ancho, de cada página de ejercicios y de la teoría.
2. Pasar `herramientas/audit_movil.py` (instrucciones en su cabecera): sin desbordes, campos de 16 px o más, objetivos táctiles de 40 px o más, sin errores de consola, en 320, 360, 375 y 393 px.
3. Resolver cada ejercicio de punta a punta en móvil simulado (respuestas correctas, incorrectas, Check, Show solutions) y mirar que todo se entiende sin leer instrucciones.
4. Comprobar el conocimiento previo con el grafo de dependencias: un tema solo puede usar la gramática de sus `depende_de` (sus formas verbales están en `tiempos_permitidos` de `index.yaml`) más la primera ronda del curso (solo 1.ª, 2.ª, 3.ª y 6.ª persona: sin *nosotros*, *vosotros*, reflexivos ni pasados hasta que el curso los introduzca). Pasar `python3 herramientas/check_gramatica_vista.py <tema>` (da candidatos, hay que revisarlos) y mirar a mano. Si un ítem del libro usa algo no visto, se cambia con la mínima modificación (normalmente el verbo, la persona o el tiempo, conservando el punto de la unidad y su solución) y los cambios los revisa Gemini antes de darlos por buenos (corrección, solución única, sentido). Los temas cuya materia es justo esa gramática (reflexivos con *nos/os*, imperativo con *vosotros*, pasados) no se tocan. Regla y fuentes en `contenido-clases/CLAUDE.md` ("Solo gramática ya vista").
5. Buscar fricción mental, no solo visual: huecos que no se sabe a qué corresponden (numerar si hay gráfico), enunciados que piden algo que no se puede teclear, palabras gramaticales, textos que se pueden quitar.
6. Repetir 1 a 5 hasta no encontrar nada. No se puede probar Safari de iPhone en este sistema: lo que no se pueda comprobar, decirlo.

## Interfaz de teoría

- Toda hoja de teoría tiene siempre un botón "Download PDF" arriba. `render.py` lo pone solo; `build_pdfs.py` genera `out/pdf/<tema>-teoria.pdf` con Chrome (los PDF se commitean, el hook `.githooks/pre-commit` los regenera cuando cambia un `*.teoria.html`).

## Orden de la portada

- La portada se ordena con `progresion.yaml` + `depende_de` (ver arriba). Al publicar un tema nuevo: ponerle `etapa:` en `index.yaml` y regenerar; si `build_index.py` se queja, el tema o su etapa están mal puestos.
- Pendiente (decisión de Javi): una segunda ronda de ejercicios con todas las personas, pasados y reflexivos. Aún no existe; no se hace nada al respecto hasta que lo pida.
