# spanishmind-exercises

Ejercicios interactivos de gramática española, autocorregibles, generados a partir de "Gramática de uso del español" (Aragonés/Palencia) y desplegados como sitio estático.

- `render.py` + `content/*.json` → `out/*.html` (páginas de ejercicios)
- `build_index.py` → `out/index.html` (portada, solo las unidades ya publicadas)
- `libro_pipeline/` — pipeline de digitalización del libro (banco crudo en `ejemplos/`)
- `dashboard/` — editor local de contenido (`python3 dashboard/server.py`)
- `index.yaml` — grafo de dependencias entre unidades, tiempos verbales y tipologías permitidas

Desplegado en Netlify (`netlify.toml`: build = `render.py` + `build_index.py`, publish = `out/`).
