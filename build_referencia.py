#!/usr/bin/env python3
"""Genera la referencia gramatical: out/referencia/<slug>.html (una pagina por
tema) y out/referencia/index.html. Lee referencia.yaml y reutiliza lo que ya
hay en content/ (tablas de conjugacion y hojas de teoria) con el mismo render
que las paginas de ejercicios. No crea contenido.

Uso:
    python3 build_referencia.py
"""
import json
import os

import yaml

import render

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out", "referencia")

CSS_REF = """
.ref h2 { font-family: var(--font-heading); color: var(--secondary); font-size: 1.25rem; margin-top: 1.6em; }
.ref h3 { color: var(--primary); font-size: 1rem; margin: 1.4em 0 .3em; }
.ref ul { margin: .3em 0; padding-left: 1.2em; }
.ref p { margin: .5em 0; }
.ref .tbl { overflow-x: auto; }
.ref table.conj td { white-space: nowrap; }
.ref table.conj tbody th { white-space: normal; font-size: .85rem; line-height: 1.3; }
@media (max-width: 480px) { .ref table.conj th, .ref table.conj td { padding: 5px 6px; } }
h1 small { display: block; font-family: var(--font-body); font-size: .95rem; font-weight: 400; color: #777; }
.practica { margin-top: 2.4em; padding-top: 1em; border-top: 2px solid var(--line); }
.practica h2 { font-family: var(--font-heading); color: var(--secondary); font-size: 1.25rem; margin: 0 0 .6em; }
.practica div { display: flex; flex-wrap: wrap; gap: 10px; }
.practica a, .temas a { display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 999px;
    background: var(--primary); color: #fff; text-decoration: none; font-weight: 600; min-height: 44px; }
.practica svg { width: 18px; height: 18px; flex: none; }
.temas { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.temas a { background: var(--card); color: var(--secondary); border: 1px solid var(--line); border-radius: 14px; display: block; }
.temas a small { display: block; font-weight: 400; color: #777; }
"""


LAPIZ = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
         'stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>')


def pagina(titulo, cuerpo, volver):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{render.esc(titulo)}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>{render.CSS}{CSS_REF}</style>
</head>
<body>
{cuerpo}
<a class="volver-indice" href="{volver[0]}">&larr; {volver[1]}</a>
</body>
</html>"""


def titulo_ejercicio(tema):
    with open(os.path.join(render.CONTENT_DIR, f"{tema}.json"), encoding="utf-8") as f:
        return json.load(f).get("titulo", tema)


def build_tema(t):
    partes = []
    for tema in t.get("conjugacion", []):
        conj = render.cargar_conjugacion(tema)
        if not conj:
            raise SystemExit(f"falta content/{tema}.conjugacion.json")
        # el h1 de la pagina ya nombra el tiempo: "Pretérito ...: regular verbs" -> "Regular verbs"
        prefijo = t["titulo"] + ": "
        if conj["titulo"].startswith(prefijo):
            resto = conj["titulo"][len(prefijo):]
            conj = {**conj, "titulo": resto[:1].upper() + resto[1:]}
        partes.append(f'<div class="tbl">{render.render_conjugacion(conj)}</div>')
    for tema in t.get("teoria", []):
        teoria = render.cargar_teoria(tema)
        if not teoria:
            raise SystemExit(f"falta content/{tema}.teoria.html")
        partes.append(teoria)
    practica = "".join(
        f'<a href="../{tema}.html">{LAPIZ}{render.esc(titulo_ejercicio(tema))}</a>'
        for tema in t.get("practica", []))
    cuerpo = (f'<h1>{render.esc(t["titulo"])}</h1>'
              f'<div class="ref">{"".join(partes)}</div>'
              + (f'<section class="practica"><h2>Exercises</h2><div>{practica}</div></section>' if practica else ""))
    return pagina(t["titulo"], cuerpo, ("index.html", "Grammar reference"))


def main():
    with open(os.path.join(HERE, "referencia.yaml"), encoding="utf-8") as f:
        temas = yaml.safe_load(f)
    os.makedirs(OUT_DIR, exist_ok=True)
    for t in temas:
        ruta = os.path.join(OUT_DIR, f"{t['slug']}.html")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(build_tema(t))
        print(f"✅ {ruta}")
    lista = "".join(
        f'<li><a href="{t["slug"]}.html">{render.esc(t["titulo"])}</a></li>'
        for t in temas)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina("Grammar reference", f'<h1>Grammar reference</h1><ul class="temas">{lista}</ul>',
                       ("/", "Exercises")))
    print(f"✅ {os.path.join(OUT_DIR, 'index.html')}")


if __name__ == "__main__":
    main()
