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
import re

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
@media (max-width: 480px) { .ref table.conj { font-size: .88rem; } .ref table.conj th, .ref table.conj td { padding: 5px 5px; } .ref details { padding: 0 12px; } }
.resumen { font-size: 1.15rem; line-height: 1.5; color: var(--secondary); margin: -.3em 0 1.2em; }
.ref .pares { display: flex; flex-wrap: wrap; gap: 6px 16px; }
.ref .par { white-space: nowrap; }
.ref .par .nueva { background: var(--accent); color: var(--secondary); border-radius: 6px; padding: 1px 8px; font-weight: 700; margin-left: 2px; }
.plegadas { display: flex; flex-direction: column; gap: 10px; margin-top: 1.2em; }
.ref details { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 0 16px; }
.ref summary { cursor: pointer; padding: 12px 0; font-weight: 600; color: var(--secondary); min-height: 44px;
    list-style: none; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.ref summary::-webkit-details-marker { display: none; }
.ref summary::after { content: "+"; font-size: 1.3rem; color: var(--primary); transition: transform .2s; }
.ref details[open] summary::after { transform: rotate(45deg); }
.ref details[open] { padding-bottom: 12px; }
@media (prefers-reduced-motion: reduce) { .ref summary::after { transition: none; } }
h1 small { display: block; font-family: var(--font-body); font-size: 1.05rem; font-weight: 600; color: var(--primary); margin-top: .2em; }
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


RAIZ_RE = re.compile(r"\[\[[^\]]*\]\]")


def conj_plegada(conj):
    """Bloques de irregulares: arriba, el texto y la nota del primer bloque;
    debajo, un desplegable por bloque. La cabecera de cada uno ya dice el
    cambio de raiz (estar estuv-), la tabla se abre al tocar."""
    b0 = conj["bloques"][0]
    texto0 = re.sub(r"(<br>)+$", "", RAIZ_RE.sub("", b0.get("intro", "")))
    h2 = f"<h2>{render.esc(conj['titulo'])}</h2>" if conj["titulo"] else ""
    arriba = (f"{h2}<p>{texto0}</p>"
              + (f"<p>{b0['nota']}</p>" if b0.get("nota") else ""))
    plegadas = ""
    for i, b in enumerate(conj["bloques"]):
        raices = {}
        for m in RAIZ_RE.findall(b.get("intro", "")):
            raiz, fin, nueva = m[2:-2].split("|")
            raices[raiz + fin] = nueva
        b = {**b, "intro": "" if i == 0 else re.sub(r"(<br>)+$", "", RAIZ_RE.sub("", b.get("intro", ""))).strip()}
        if i == 0:
            b.pop("nota", None)
        verbos = [v for c in b["columnas"] for v in c["verbos"]]
        if raices:
            cab = "".join(f'<span class="par">{render.esc(v)} <span class="nueva">{render.esc(n)}-</span></span>'
                          for v, n in raices.items())
        else:
            cab = "".join(f'<span class="par">{render.esc(v)}</span>' for v in verbos)
        tabla = render.render_conjugacion({"titulo": "", "bloques": [b]}).replace("<h2></h2>", "", 1)
        plegadas += f'<details><summary><span class="pares">{cab}</span></summary><div class="tbl">{tabla}</div></details>'
    return arriba + f'<div class="plegadas">{plegadas}</div>'


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
        if conj["titulo"].lower() == t.get("sub", "").lower():
            conj = {**conj, "titulo": ""}  # ya lo dice el subtitulo de la pagina
        if tema in t.get("plegar", []):
            partes.append(conj_plegada(conj))
        else:
            tabla = render.render_conjugacion(conj).replace("<h2></h2>", "", 1)
            partes.append(f'<div class="tbl">{tabla}</div>')
    for tema in t.get("teoria", []):
        teoria = render.cargar_teoria(tema)
        if not teoria:
            raise SystemExit(f"falta content/{tema}.teoria.html")
        teoria = re.sub(r"^\s*<h2>.*?</h2>", "", teoria, count=1)  # el h1 ya nombra el tema
        if t.get("resumen"):
            teoria = teoria.replace(f"<p>{t['resumen']}</p>", "", 1)
        partes.append(teoria)
    practica = "".join(
        f'<a href="../{tema}.html">{LAPIZ}{render.esc(titulo_ejercicio(tema))}</a>'
        for tema in t.get("practica", []))
    sub = f'<small>{render.esc(t["sub"])}</small>' if t.get("sub") else ""
    cuerpo = (f'<h1>{render.esc(t["titulo"])}{sub}</h1>'
              + (f'<p class="resumen">{t["resumen"]}</p>' if t.get("resumen") else "")
              +               f'<div class="ref">{"".join(partes)}</div>'
              + (f'<section class="practica"><h2>Exercises</h2><div>{practica}</div></section>' if practica else ""))
    return pagina(t["titulo"] + (f": {t['sub']}" if t.get("sub") else ""), cuerpo, ("index.html", "Grammar reference"))


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
        f'<li><a href="{t["slug"]}.html">{render.esc(t["titulo"])}{f'<small>{render.esc(t["sub"])}</small>' if t.get("sub") else ""}</a></li>'
        for t in temas)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina("Grammar reference", f'<h1>Grammar reference</h1><ul class="temas">{lista}</ul>',
                       ("/", "Exercises")))
    print(f"✅ {os.path.join(OUT_DIR, 'index.html')}")


if __name__ == "__main__":
    main()
