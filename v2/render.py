#!/usr/bin/env python3
"""
Renderizador v2: consume content/<tema>.json (schema v2) -> out/<tema>.html
Puro script, sin LLM.

Schema v2 (nivel unidad):
{
  "tema": "numeros-ordinales",
  "titulo": "Primero, segundo, tercero...",
  "descripcion_gramatical": "Los numerales ordinales",  # solo para buscar por nombre gramatical, no se renderiza
  "ejercicios": [
    {
      "tipologia": "T2",
      "enunciado": "Observa el directorio y completa las frases.",
      "contexto_grafico": {"tipo": "directory", "datos": [...]},   # opcional
      "items": [
        {"texto_enunciado": "Antonio Oliva vive en el _____ piso.",
         "solucion_correcta": ["segundo"]}
      ]
    }
  ]
}

Tokenización de items (un solo tokenizador cubre T2/T3/T4/T5):
  - "(a/b/c)"  (paréntesis CON barra)  -> <select>   (elección inline, T5)
  - "_____"                            -> <input>    (hueco libre, T2/T3/T4)
  - "(2.º)"    (paréntesis SIN barra)  -> texto literal (estímulo visual)
Cada widget consume, en orden, un elemento de solucion_correcta.
Un "–" (raya) dentro de texto_enunciado marca el inicio de una intervención de
minidiálogo: cada tramo se renderiza en su propia línea dentro del mismo item.

Uso:
    python3 render.py                 # todos los .json de content/
    python3 render.py numeros-ordinales
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(HERE, "content")
OUT_DIR = os.path.join(HERE, "out")

# Paréntesis que contienen al menos una barra -> elección inline (T5).
# Uno sin barra, p. ej. "(2.º)", NO casa y se queda como texto literal.
CHOICE_RE = re.compile(r"\(([^()]*?/[^()]*?)\)")
BLANK = "_____"

CSS = """
:root {
    --bg: #FBF7F0; --card: #ffffff; --primary: #C1440E; --secondary: #2E4053;
    --accent: #E9B44C; --ok: #4F7942; --bad: #B33A3A; --text: #2B2B2B;
    --line: #e5ddd0;
    --font-heading: 'Playfair Display', serif; --font-body: 'DM Sans', sans-serif;
}
* { box-sizing: border-box; }
body { font-family: var(--font-body); background: var(--bg); color: var(--text);
    max-width: 760px; margin: 40px auto; padding: 0 20px; line-height: 1.7; }
h1 { font-family: var(--font-heading); color: var(--secondary); }
.ejercicio { background: var(--card); border: 1px solid var(--line);
    border-radius: 10px; padding: 20px 22px; margin: 24px 0; }
.ejercicio > .enunciado { font-weight: 600; color: var(--secondary);
    margin: 0 0 14px; }
.item { padding: 8px 0; border-top: 1px dashed var(--line); }
.item:first-of-type { border-top: none; }
.item-row { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 4px; }
.item-row + .item-row { margin-top: 4px; }
.item-num { color: #999; font-variant-numeric: tabular-nums; min-width: 1.6em; }
.blank { font-family: var(--font-body); padding: 4px 8px; border: 1px solid #ccc;
    border-radius: 6px; width: 150px; font-size: .95rem; }
select.blank { width: auto; min-width: 90px; background: #fff; cursor: pointer; }
.blank.ok { border-color: var(--ok); background: #f0f6ee; }
.blank.bad { border-color: var(--bad); background: #fbeeee; }
.group-controls { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--line);
    display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
button { font-family: var(--font-body); background: var(--primary); color: #fff;
    border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: .85rem; }
button.ghost { background: transparent; color: var(--secondary); text-decoration: underline; padding: 8px 4px; }
button:hover { opacity: .9; }
.group-feedback { font-weight: 600; font-size: .9rem; display: none; margin-left: auto; }
.group-feedback.correct { color: var(--ok); }
.group-feedback.wrong { color: var(--bad); }
/* soporte gráfico */
.directory { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px;
    border: 2px solid var(--secondary); border-radius: 8px; padding: 10px;
    margin-bottom: 18px; background: #fffdf8; }
.plate { text-align: center; padding: 10px 6px; border: 1px solid var(--line);
    border-radius: 6px; background: #fff; }
.plate-name { display: block; font-weight: 600; font-size: .82rem; color: var(--secondary); }
.plate-floor { display: block; margin-top: 4px; font-size: .95rem; color: var(--primary); font-weight: 700; }
@media (max-width: 620px) { .directory { grid-template-columns: repeat(2, 1fr); } }
#resumen { text-align: center; font-family: var(--font-heading); font-size: 1.3rem;
    margin-top: 30px; color: var(--secondary); }
"""

JS = """
function norm(s){
  return (s||'').trim().toLowerCase()
    .normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');
}
function fieldOk(f){
  const sol = f.getAttribute('data-sol');
  const val = f.value;
  if (sol === '\\u00f8') return val.trim() === '' || norm(val) === norm('\\u00f8');
  return norm(val) === norm(sol);
}
function checkGroup(btn){
  const section = btn.closest('.ejercicio');
  let total = 0, correct = 0;
  section.querySelectorAll('.item').forEach(item => {
    const fields = item.querySelectorAll('[data-sol]');
    let itemOk = true;
    fields.forEach(f => {
      const ok = fieldOk(f);
      f.classList.toggle('ok', ok);
      f.classList.toggle('bad', !ok);
      total++;
      if (ok) { correct++; } else { itemOk = false; }
    });
    item.dataset.solved = itemOk ? '1' : '0';
  });
  const allok = correct === total;
  const fb = section.querySelector('.group-feedback');
  fb.textContent = allok ? ('\\u2714 All correct! (' + correct + '/' + total + ')')
                          : ('\\u2718 ' + correct + '/' + total + ' correct \\u2014 review the marked ones');
  fb.className = 'group-feedback ' + (allok ? 'correct' : 'wrong');
  fb.style.display = 'inline';
  updateResumen();
}
function revealGroup(btn){
  const section = btn.closest('.ejercicio');
  section.querySelectorAll('[data-sol]').forEach(f => {
    const sol = f.getAttribute('data-sol');
    if (f.tagName === 'SELECT') {
      [...f.options].forEach(o => { if (norm(o.value) === norm(sol)) f.value = o.value; });
    } else { f.value = sol; }
    f.classList.remove('bad'); f.classList.add('ok');
  });
}
function updateResumen(){
  const total = document.querySelectorAll('.item').length;
  const solved = document.querySelectorAll('.item[data-solved="1"]').length;
  const r = document.getElementById('resumen');
  r.textContent = solved >= total ? ('Done! ' + solved + '/' + total)
                                   : ('Progress: ' + solved + '/' + total);
}
document.addEventListener('DOMContentLoaded', updateResumen);
"""


def esc(s):
    return html.escape(str(s), quote=True)


def render_widgets(text, solutions):
    """Convierte texto con tokens en HTML, consumiendo `solutions` en orden.
    Devuelve (html, n_widgets). Falla si el nº de tokens != nº de soluciones."""
    events = []
    for m in CHOICE_RE.finditer(text):
        events.append((m.start(), m.end(), "choice", m.group(1)))
    for m in re.finditer(re.escape(BLANK), text):
        events.append((m.start(), m.end(), "blank", None))
    events.sort()

    out = []
    pos = 0
    widx = 0
    for start, end, kind, payload in events:
        out.append(esc(text[pos:start]))
        sol = solutions[widx] if widx < len(solutions) else ""
        if kind == "choice":
            opciones = payload.split("/")
            opts = '<option value="">—</option>' + "".join(
                f"<option>{esc(o.strip())}</option>" for o in opciones
            )
            out.append(f'<select class="blank" data-sol="{esc(sol)}">{opts}</select>')
        else:
            out.append(f'<input type="text" class="blank" data-sol="{esc(sol)}" autocomplete="off">')
        widx += 1
        pos = end
    out.append(esc(text[pos:]))
    return "".join(out), widx


def render_directory(datos):
    plates = "".join(
        f'<div class="plate"><span class="plate-name">{esc(d["nombre"])}</span>'
        f'<span class="plate-floor">{esc(d["piso"])}</span></div>'
        for d in datos
    )
    return f'<div class="directory">{plates}</div>'


GRAFICO_RENDERERS = {
    "directory": render_directory,
    # pendientes: family_tree, clocks, visual_count, map, vocabulary_box, ...
}


DIALOGO_RE = re.compile(r"(?=–)")


def render_item(n, item):
    body, nw = render_widgets(item["texto_enunciado"], item["solucion_correcta"])
    ns = len(item["solucion_correcta"])
    if nw != ns:
        raise ValueError(
            f"Item {n}: {nw} hueco(s) pero {ns} solución(es) -> revisa el JSON:\n  {item['texto_enunciado']!r}"
        )
    lines = [l for l in DIALOGO_RE.split(body) if l.strip()] or [body]
    rows = "".join(
        f'<div class="item-row"><span class="item-num">{f"{n}." if i == 0 else ""}</span> <span>{line}</span></div>'
        for i, line in enumerate(lines)
    )
    return f"""
        <div class="item" data-solved="0">
            {rows}
        </div>"""


def render_ejercicio(ej):
    grafico = ""
    ctx = ej.get("contexto_grafico")
    if ctx:
        renderer = GRAFICO_RENDERERS.get(ctx["tipo"])
        if renderer is None:
            grafico = f'<p class="pista">[graphic "{esc(ctx["tipo"])}" not implemented yet]</p>'
        else:
            grafico = renderer(ctx["datos"])
    items = "".join(render_item(i, it) for i, it in enumerate(ej["items"], start=1))
    return f"""
    <section class="ejercicio">
        <p class="enunciado">{esc(ej['enunciado'])}</p>
        {grafico}
        {items}
        <div class="group-controls">
            <button onclick="checkGroup(this)">Check answers</button>
            <button class="ghost" onclick="revealGroup(this)">Show solutions</button>
            <span class="group-feedback"></span>
        </div>
    </section>"""


def build_html(data):
    titulo = data.get("titulo", data["tema"])
    body = "".join(render_ejercicio(ej) for ej in data["ejercicios"])
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(titulo)}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<h1>{esc(titulo)}</h1>
{body}
<p id="resumen"></p>
<script>{JS}</script>
</body>
</html>"""


def generate(tema):
    with open(os.path.join(CONTENT_DIR, f"{tema}.json"), encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"{tema}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(build_html(data))
    print(f"✅ {out_path}")


def main():
    if len(sys.argv) >= 2:
        temas = sys.argv[1:]
    else:
        temas = sorted(
            fn[:-5] for fn in os.listdir(CONTENT_DIR) if fn.endswith(".json")
        )
    for tema in temas:
        generate(tema)


if __name__ == "__main__":
    main()
