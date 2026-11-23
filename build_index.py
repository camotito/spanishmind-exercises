#!/usr/bin/env python3
"""Genera out/index.html: la pagina de inicio del sitio, con la lista de
unidades PUBLICADAS (las que ya tienen content/<tema>.json -- no publicar
todo el libro es la decision explicita de este proyecto), agrupadas por
etapa del curso (progresion.yaml) y, dentro de cada etapa, por orden topologico
de depende_de (mismo criterio que index.yaml dice que se debe usar para el orden
de estudio). Falla si una etapa contradice el grafo de dependencias.

Uso:
    python3 build_index.py
"""
import html
import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_YAML = os.path.join(HERE, "index.yaml")
PROGRESION_YAML = os.path.join(HERE, "progresion.yaml")
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


def validar_etapas(indice, por_tema, orden_etapas):
    """Cada tema publicado debe tener etapa, y no puede estar en una etapa anterior
    a la de ningun tema publicado del que dependa (directa o indirectamente)."""
    pos = {e: i for i, e in enumerate(orden_etapas)}
    completo = {t["tema"]: t for t in indice}
    errores = []

    def ancestros(tema, vistos):
        for d in completo[tema].get("depende_de") or []:
            if d in completo and d not in vistos:
                vistos.add(d)
                ancestros(d, vistos)
        return vistos

    for tema, t in por_tema.items():
        if t.get("etapa") not in pos:
            errores.append(f"{tema}: etapa {t.get('etapa')!r} no esta en progresion.yaml")
            continue
        for a in ancestros(tema, set()):
            if a in por_tema and por_tema[a].get("etapa") in pos and pos[por_tema[a]["etapa"]] > pos[t["etapa"]]:
                errores.append(f"{tema} (etapa {t['etapa']}) depende de {a} (etapa {por_tema[a]['etapa']}), que va despues")
    if errores:
        raise SystemExit("Etapas incoherentes con el grafo de dependencias:\n  " + "\n  ".join(errores))


def main():
    with open(INDEX_YAML, encoding="utf-8") as f:
        indice = yaml.safe_load(f)

    publicados = [t for t in indice if os.path.isfile(os.path.join(CONTENT_DIR, f"{t['tema']}.json"))]
    por_tema = {t["tema"]: t for t in publicados}
    # orden topologico sobre TODO el grafo (no solo lo publicado), para que una
    # dependencia que pasa por un tema sin publicar tambien cuente
    orden = [tema for tema in orden_topologico(indice) if tema in por_tema]

    with open(PROGRESION_YAML, encoding="utf-8") as f:
        etapas = yaml.safe_load(f)
    validar_etapas(indice, por_tema, [e["etapa"] for e in etapas])

    secciones = []
    for e in etapas:
        temas = [t for t in orden if por_tema[t]["etapa"] == e["etapa"]]
        if not temas:
            continue
        lis = "".join(
            f'<li><a href="{esc(tema)}.html">{esc(por_tema[tema].get("titulo", tema))}</a>'
            f'<span class="tecnico">{esc(DESCRIPCION_EN.get(tema, por_tema[tema].get("descripcion_gramatical", "")))}</span></li>'
            for tema in temas
        )
        secciones.append(f'<section><h2>{esc(e["titulo"])}</h2><ol>{lis}</ol></section>')
    items = "".join(secciones)

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
ol {{ list-style: none; padding: 0; }}
body {{ counter-reset: unidad; }}
h2 {{ font-family: var(--font-body); font-size: 1rem; font-weight: 600; color: var(--secondary); margin: 32px 0 4px; }}
li {{ counter-increment: unidad; background: var(--card); border: 1px solid var(--line);
    border-radius: 10px; padding: 14px 18px; margin: 10px 0; }}
li::before {{ content: counter(unidad) ". "; color: var(--primary); font-weight: 700; }}
a {{ color: var(--secondary); text-decoration: none; font-weight: 600; font-size: 1.05rem; }}
a:hover {{ text-decoration: underline; }}
li {{ position: relative; }}
li a::after {{ content: ""; position: absolute; inset: 0; }}
.tecnico {{ display: block; font-size: .8rem; color: #888; font-weight: 400; margin-top: 2px; }}
</style>
</head>
<body>
<h1>SpanishMind</h1>
<p><a href="referencia/index.html">Grammar reference &rarr;</a></p>
{items}
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
