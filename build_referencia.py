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
.practica { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 2em; }
.practica a, .temas a { display: inline-block; padding: 10px 18px; border-radius: 999px; background: var(--secondary);
    color: #fff; text-decoration: none; font-weight: 600; }
.temas { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.temas a { background: var(--card); color: var(--secondary); border: 1px solid var(--line); border-radius: 14px; display: block; }
.temas a small { display: block; font-weight: 400; color: #777; }
"""


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
        partes.append(f'<div class="tbl">{render.render_conjugacion(conj)}</div>')
    for tema in t.get("teoria", []):
        teoria = render.cargar_teoria(tema)
        if not teoria:
            raise SystemExit(f"falta content/{tema}.teoria.html")
        partes.append(teoria)
    practica = "".join(
        f'<a href="../{tema}.html">{render.esc(titulo_ejercicio(tema))} &rarr;</a>'
        for tema in t.get("practica", []))
    cuerpo = (f'<h1>{render.esc(t["titulo"])}<small>{render.esc(t["en"])}</small></h1>'
              f'<div class="ref">{"".join(partes)}</div>'
              + (f'<div class="practica">{practica}</div>' if practica else ""))
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
        f'<li><a href="{t["slug"]}.html">{render.esc(t["titulo"])}<small>{render.esc(t["en"])}</small></a></li>'
        for t in temas)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina("Grammar reference", f'<h1>Grammar reference</h1><ul class="temas">{lista}</ul>',
                       ("/", "Exercises")))
    print(f"✅ {os.path.join(OUT_DIR, 'index.html')}")


if __name__ == "__main__":
    main()
