#!/usr/bin/env python3
"""Genera out/index.html: la pagina de inicio del sitio, con la lista de
unidades PUBLICADAS (las que ya tienen content/<tema>.json -- no publicar
todo el libro es la decision explicita de este proyecto), ordenadas por
orden topologico de depende_de (mismo criterio que index.yaml dice que se
debe usar para el orden de estudio).

Uso:
    python3 build_index.py
"""
import html
import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_YAML = os.path.join(HERE, "index.yaml")
CONTENT_DIR = os.path.join(HERE, "content")
OUT_DIR = os.path.join(HERE, "out")

# La pagina de inicio es UI/scaffolding (como los enunciados de ejercicios):
# en ingles. Los titulos de cada unidad (el link) son contenido -- se quedan
# en espanol, igual que el resto del sitio. descripcion_gramatical se
# almacena en espanol en index.yaml (para buscar por terminologia, ver
# cabecera de ese fichero) asi que aqui se traduce solo para mostrarla, sin
# tocar el dato fuente.
DESCRIPCION_EN = {
    "numeros-ordinales": "Ordinal numbers",
    "pronombres-lo-la-le": "Direct and indirect object pronouns",
    "pronombres-reflexivos-y-con-valor-reciproco": "Reflexive and reciprocal pronouns",
    "imperativo-afirmativo-verbos-regulares": "Affirmative imperative: regular verbs",
    "imperativo-negativo-verbos-regulares": "Negative imperative: regular verbs",
    "imperativo-verbos-irregulares-1": "Imperative: irregular verbs (1)",
    "imperativo-verbos-irregulares-2": "Imperative: irregular verbs (2)",
    "imperativo-de-verbos-con-se": "Imperative of reflexive verbs (with se)",
    "imperativo-con-pronombres-de-complemento": "Imperative with object pronouns",
    "adverbios-de-tiempo-2": "Time adverbs (2)",
    "oraciones-impersonales": "Impersonal sentences",
}


def esc(s):
    return html.escape(str(s), quote=True)


def orden_topologico(temas):
    """Mismo algoritmo (duplicado a proposito, no importado, ver
    merge_ejemplos.py para el mismo criterio) que
    libro_pipeline/compute_tiempos_permitidos.py."""
    por_tema = {t["tema"]: t for t in temas}
    visitado = {}
    orden = []

    def visitar(tema, pila):
        if visitado.get(tema) == "hecho":
            return
        if visitado.get(tema) == "en_curso":
            raise SystemExit(f"ciclo en depende_de: {' -> '.join(pila + [tema])}")
        visitado[tema] = "en_curso"
        for dep in por_tema[tema].get("depende_de") or []:
            if dep in por_tema:
                visitar(dep, pila + [tema])
        visitado[tema] = "hecho"
        orden.append(tema)

    for t in temas:
        visitar(t["tema"], [])
    return orden


def main():
    with open(INDEX_YAML, encoding="utf-8") as f:
        indice = yaml.safe_load(f)

    publicados = [t for t in indice if os.path.isfile(os.path.join(CONTENT_DIR, f"{t['tema']}.json"))]
    por_tema = {t["tema"]: t for t in publicados}
    orden = [tema for tema in orden_topologico(publicados) if tema in por_tema]

    items = "".join(
        f'<li><a href="{esc(tema)}.html">{esc(por_tema[tema].get("titulo", tema))}</a>'
        f'<span class="tecnico">{esc(DESCRIPCION_EN.get(tema, por_tema[tema].get("descripcion_gramatical", "")))}</span></li>'
        for tema in orden
    )

    out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SpanishMind — Spanish grammar exercises</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>
:root {{
    --bg: #FBF7F0; --card: #ffffff; --primary: #C1440E; --secondary: #2E4053;
    --line: #e5ddd0; --text: #2B2B2B;
    --font-heading: 'Playfair Display', serif; --font-body: 'DM Sans', sans-serif;
}}
* {{ box-sizing: border-box; }}
body {{ font-family: var(--font-body); background: var(--bg); color: var(--text);
    max-width: 640px; margin: 40px auto; padding: 0 20px; line-height: 1.7; }}
h1 {{ font-family: var(--font-heading); color: var(--secondary); }}
p.subtitle {{ color: #666; margin-top: -8px; }}
ol {{ list-style: none; counter-reset: unidad; padding: 0; }}
li {{ counter-increment: unidad; background: var(--card); border: 1px solid var(--line);
    border-radius: 10px; padding: 14px 18px; margin: 10px 0; }}
li::before {{ content: counter(unidad) ". "; color: var(--primary); font-weight: 700; }}
a {{ color: var(--secondary); text-decoration: none; font-weight: 600; font-size: 1.05rem; }}
a:hover {{ text-decoration: underline; }}
.tecnico {{ display: block; font-size: .8rem; color: #888; font-weight: 400; margin-top: 2px; }}
</style>
</head>
<body>
<h1>SpanishMind</h1>
<p class="subtitle">Interactive Spanish grammar exercises — {len(orden)} unit(s) published.</p>
<ol>{items}</ol>
</body>
</html>
"""

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"✅ {out_path} ({len(orden)} unidad(es))")


if __name__ == "__main__":
    main()
