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
      "grafico_necesario": true,   # solo si hay contexto_grafico -- ver mas abajo
      "items": [
        {"texto_enunciado": "Antonio Oliva vive en el _____ piso.",
         "solucion_correcta": ["segundo"]}
      ]
    }
  ]
}

"grafico_necesario" (bool, solo si hay "contexto_grafico"): calculado a mano
para las 126 unidades del libro (ver ejemplos/*.json, fuente de verdad). true
= el grafico aporta informacion que NO esta en el texto de los items (p.ej.
una senal de trafico concreta) y se muestra el sustituto en texto. false = el
grafico es decorativo (el texto de los items ya trae todo lo necesario) y no
se renderiza nada. Si falta el campo, se asume true (mostrar) por seguridad.
Al promover una unidad de ejemplos/ a content/, copiar este valor a mano.

Tokenización de items (un solo tokenizador cubre T2/T3/T4/T5):
  - "(a/b/c)"  (paréntesis CON barra)  -> <select>   (elección inline, T5)
  - "_____"                            -> <input>    (hueco libre, T2/T3/T4)
  - "(2.º)"    (paréntesis SIN barra)  -> texto en cursiva (estímulo, no widget)
Cada widget consume, en orden, un elemento de solucion_correcta.
Un "–" (raya) dentro de texto_enunciado marca el inicio de una intervención de
minidiálogo: cada tramo se renderiza en su propia línea dentro del mismo item.
Si un elemento de solucion_correcta contiene "/" (p. ej. "lo/le"), el hueco
(solo huecos "_____", no elecciones T5) acepta cualquiera de las alternativas;
al revelar la solución se rellena con la primera y se muestra una nota junto
al hueco indicando que las demás también son válidas.

Cada ejercicio se pagina: una pagina por ejercicio (grupo de items), con
navegacion Anterior/Siguiente client-side dentro del mismo HTML estatico
(sin routing de servidor). --paginar=item genera en su lugar una variante
experimental de una pagina por item, en out_preview/ (no se usa en el sitio
ni en el dashboard, solo para comparar sensaciones).

Uso:
    python3 render.py                 # todos los .json de content/
    python3 render.py numeros-ordinales
    python3 render.py --paginar=item numeros-ordinales   # variante experimental
"""
import html
import itertools
import json
import os
import re
import sys

_hint_ids = itertools.count(1)

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(HERE, "content")
OUT_DIR = os.path.join(HERE, "out")
RENDER_CONFIG_PATH = os.path.join(HERE, "render_config.json")


def cargar_config():
    """render_config.json: ajustes editables desde el dashboard (p.ej. que
    tipologias no se renderizan por defecto). Si no existe, todo activo."""
    if not os.path.exists(RENDER_CONFIG_PATH):
        return {"tipologias_desactivadas": []}
    with open(RENDER_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

# Paréntesis que contienen al menos una barra -> elección inline (T5).
CHOICE_RE = re.compile(r"\(([^()]*?/[^()]*?)\)")
# Paréntesis SIN barra, p. ej. "(Tener)", "(a un amigo)" -- estimulo/pista que
# el alumno debe usar para completar el hueco; se muestra en cursiva, no es
# un widget interactivo.
HINT_RE = re.compile(r"\(([^()/]+)\)")
BLANK = "_____"


def tokenize_events(text):
    """Escanea `text` y devuelve los eventos (start, end, kind, payload)
    ordenados -- "choice" y "blank" son widgets (consumen una solucion cada
    uno), "estimulo" es texto entre parentesis sin barra que solo se resalta en
    cursiva. Compartido por render_widgets() (huecos interactivos) y
    render_ejemplo() (el mismo item ya resuelto, de solo lectura)."""
    events = []
    for m in CHOICE_RE.finditer(text):
        events.append((m.start(), m.end(), "choice", m.group(1)))
    for m in re.finditer(re.escape(BLANK), text):
        events.append((m.start(), m.end(), "blank", None))
    for m in HINT_RE.finditer(text):
        events.append((m.start(), m.end(), "estimulo", m.group(0)))
    events.sort()
    return events

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
.item-row + .item-row { margin-top: 4px; }
.item-row .blank, .item-row select.blank { vertical-align: middle; }
.blank { font-family: var(--font-body); padding: 2px 2px; border: none;
    border-bottom: 2px solid var(--secondary); border-radius: 0;
    background: transparent; width: 150px; max-width: 100%; font-size: .95rem; }
select.blank { width: auto; min-width: 90px; background: transparent; cursor: pointer; }
.blank-wide { display: block; width: 100%; margin-top: 4px; }
.blank.ok { border-bottom-color: var(--ok); background: transparent; }
.blank.bad { border-bottom-color: var(--bad); background: transparent; }
.hint-paren { font-style: italic; }
.alt-hint { display: block; font-size: .78rem;
    color: var(--secondary); opacity: .85; margin-top: 2px; }
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
.scene-list { list-style: none; margin: 0 0 18px; padding: 10px 14px;
    border: 2px solid var(--secondary); border-radius: 8px; background: #fffdf8; }
.scene-list li { padding: 4px 0; border-top: 1px dashed var(--line); }
.scene-list li:first-child { border-top: none; }
.scene-num { color: var(--secondary); font-weight: 700; }
.tabla-titulo { font-weight: 700; color: var(--secondary); background: #fffdf8;
    border: 2px solid var(--secondary); border-radius: 8px; padding: 8px 14px;
    margin-bottom: 18px; }
.wordbox { display: flex; flex-wrap: wrap; gap: 8px; border: 2px solid var(--secondary);
    border-radius: 8px; padding: 12px; margin-bottom: 18px; background: #fffdf8; }
.word-chip { background: #fff; border: 1px solid var(--line); border-radius: 20px;
    padding: 4px 12px; font-size: .88rem; color: var(--secondary); }
.ejemplo { background: #f2f7ef; border: 1px solid var(--ok); border-radius: 6px;
    padding: 8px 12px; margin-bottom: 10px; }
.ejemplo-tag { display: block; text-align: right; color: var(--ok); font-weight: 700;
    font-size: .68rem; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 4px; }
input.blank-example { color: var(--text); font-weight: 600; border-bottom-color: var(--ok);
    background: transparent; cursor: default; }
.page-nav { display: flex; justify-content: space-between; align-items: center;
    margin: 24px 0; gap: 12px; }
#page-indicator { font-family: var(--font-heading); color: var(--secondary); font-size: 1rem; }
button:disabled { opacity: .4; cursor: default; }
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
  if (sol.includes('/')) return sol.split('/').some(alt => norm(val) === norm(alt));
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
}
function revealGroup(btn){
  const section = btn.closest('.ejercicio');
  section.querySelectorAll('[data-sol]').forEach(f => {
    const sol = f.getAttribute('data-sol');
    if (f.tagName === 'SELECT') {
      [...f.options].forEach(o => { if (norm(o.value) === norm(sol)) f.value = o.value; });
    } else if (sol.includes('/')) {
      const opciones = sol.split('/');
      f.value = opciones[0];
      const hintId = f.getAttribute('data-hint');
      const hint = hintId ? section.querySelector('#' + hintId) : null;
      if (hint) {
        const citadas = opciones.map(o => '"' + o.trim() + '"').join(' or ');
        hint.textContent = '(' + citadas + ' both accepted)';
        hint.hidden = false;
      }
    } else {
      f.value = sol;
    }
    f.classList.remove('bad'); f.classList.add('ok');
  });
}
let currentPage = 0;
function showPage(i){
  const pages = document.querySelectorAll('.page');
  if (!pages.length) return;
  currentPage = Math.max(0, Math.min(i, pages.length - 1));
  pages.forEach((p, idx) => { p.hidden = idx !== currentPage; });
  const indicator = document.getElementById('page-indicator');
  if (indicator) indicator.textContent = (currentPage + 1) + ' / ' + pages.length;
  const prev = document.getElementById('btn-prev');
  const next = document.getElementById('btn-next');
  if (prev) prev.disabled = currentPage === 0;
  if (next) next.disabled = currentPage === pages.length - 1;
  window.scrollTo(0, 0);
}
document.addEventListener('DOMContentLoaded', () => showPage(0));
"""


def esc(s):
    return html.escape(str(s), quote=True)


def esc_body(s):
    """Como esc(), pero deja pasar <u>/</u> (el libro los usa para marcar la
    oracion original que hay que reescribir; no es HTML libre del usuario)."""
    return esc(s).replace("&lt;u&gt;", "<u>").replace("&lt;/u&gt;", "</u>")


def input_width(sol):
    """Ancho del campo de texto en 'ch' (anchura de caracter), a partir de la
    respuesta correcta mas larga entre las alternativas aceptadas (separadas
    por "/"), para que el hueco no de pistas de mas ni se quede corto."""
    opciones = sol.split("/") if sol else [""]
    n = max((len(o.strip()) for o in opciones), default=0)
    return max(n, 2) + 2


# a partir de este ancho (p.ej. reescritura de oracion completa en T10/T11/T12)
# el hueco inline ya no cabe junto al resto de la frase sin desbordar la
# tarjeta -- pasa a ocupar su propia linea a ancho completo (.blank-wide).
ANCHO_INLINE_MAX = 20


def render_widgets(text, solutions):
    """Convierte texto con tokens en HTML, consumiendo `solutions` en orden.
    Devuelve (html, n_widgets, hint_ids). hint_ids son los ids (uno por hueco
    con alternativas "a/b") de los <span class="alt-hint"> que hay que colocar
    al FINAL del item (no aqui mismo, en medio de la frase)."""
    events = tokenize_events(text)

    out = []
    hint_ids = []
    pos = 0
    widx = 0
    for start, end, kind, payload in events:
        out.append(esc_body(text[pos:start]))
        if kind == "estimulo":
            out.append(f'<em class="hint-paren">{esc_body(payload)}</em>')
            pos = end
            continue
        sol = solutions[widx] if widx < len(solutions) else ""
        if kind == "choice":
            opciones = payload.split("/")
            opts = '<option value="">—</option>' + "".join(
                f"<option>{esc(o.strip())}</option>" for o in opciones
            )
            out.append(f'<select class="blank" data-sol="{esc(sol)}">{opts}</select>')
        else:
            hint_id = f"hint-{next(_hint_ids)}" if "/" in sol else ""
            ancho = input_width(sol)
            if ancho > ANCHO_INLINE_MAX:
                out.append(
                    f'<input type="text" class="blank blank-wide" data-sol="{esc(sol)}" '
                    f'data-hint="{hint_id}" autocomplete="off">'
                )
            else:
                out.append(
                    f'<input type="text" class="blank" data-sol="{esc(sol)}" '
                    f'data-hint="{hint_id}" style="width: {ancho}ch" autocomplete="off">'
                )
            if hint_id:
                hint_ids.append(hint_id)
        widx += 1
        pos = end
    out.append(esc_body(text[pos:]))
    return "".join(out), widx, hint_ids


def render_directory(datos):
    plates = "".join(
        f'<div class="plate"><span class="plate-name">{esc(d["nombre"])}</span>'
        f'<span class="plate-floor">{esc(d["piso"])}</span></div>'
        for d in datos
    )
    return f'<div class="directory">{plates}</div>'


def render_functional_images(datos):
    """El libro muestra un dibujo por escena (situacion/orden). No tenemos
    las imagenes reales recortadas (no implementado, ademas de derechos de
    autor del escaneo) -- se listan como escenas numeradas en texto, que es
    el contexto que de verdad hace falta para resolver el ejercicio. Las
    claves varian entre unidades ("descripcion" o "escena", con o sin
    "numero" explicito), asi que se usa lo que haya."""
    filas = []
    for i, d in enumerate(datos, start=1):
        numero = d.get("numero", str(i))
        texto = d.get("descripcion") or d.get("escena") or ""
        filas.append(f'<li><span class="scene-num">{esc(numero)}.</span> {esc(texto)}</li>')
    return f'<ul class="scene-list">{"".join(filas)}</ul>'


def render_titulo_tabla(datos):
    """Algunas unidades traen una tabla con titulo propio en el libro (p.ej.
    "Consejos para el ahorro de energia") que no aporta datos en si misma,
    solo contexto -- se pinta como encabezado antes de los items."""
    return f'<p class="tabla-titulo">{esc(datos["titulo"])}</p>'


GRAFICO_RENDERERS = {
    "directory": render_directory,
    "functional_images": render_functional_images,
    "titulo_tabla": render_titulo_tabla,
    # pendientes: family_tree, clocks, visual_count, map, vocabulary_box, ...
}


DIALOGO_RE = re.compile(r"(?=–)")


def render_item(n, item):
    body, nw, hint_ids = render_widgets(item["texto_enunciado"], item["solucion_correcta"])
    ns = len(item["solucion_correcta"])
    if nw != ns:
        raise ValueError(
            f"Item {n}: {nw} hueco(s) pero {ns} solución(es) -> revisa el JSON:\n  {item['texto_enunciado']!r}"
        )
    lines = [l for l in DIALOGO_RE.split(body) if l.strip()] or [body]
    rows = "".join(f'<div class="item-row"><span>{line}</span></div>' for line in lines)
    # las notas "(x or y both accepted)" van DESPUES de toda la frase del item,
    # no pegadas al hueco -- por eso se generan aparte y no dentro de `rows`.
    hints = "".join(f'<span class="alt-hint" id="{hid}" hidden></span>' for hid in hint_ids)
    return f"""
        <div class="item" data-solved="0">
            {rows}
            {hints}
        </div>"""


def render_ejemplo(item):
    """El libro imprime el primer item de cada bloque de huecos ya resuelto,
    como modelo (en cursiva) -- lo mostramos completado y no interactivo en
    vez de como un hueco mas (ver ejemplos/*: solucion_correcta ya trae la
    respuesta del solucionario para este item tambien)."""
    texto = item["texto_enunciado"]
    respuestas = item["solucion_correcta"]
    events = tokenize_events(texto)
    out = []
    pos = 0
    widx = 0
    for start, end, kind, payload in events:
        out.append(esc_body(texto[pos:start]))
        if kind == "estimulo":
            out.append(f'<em class="hint-paren">{esc_body(payload)}</em>')
            pos = end
            continue
        sol = respuestas[widx] if widx < len(respuestas) else ""
        primera = sol.split("/")[0].strip() if "/" in sol else sol
        ancho = input_width(primera)
        clase = "blank blank-example blank-wide" if ancho > ANCHO_INLINE_MAX else "blank blank-example"
        estilo = "" if ancho > ANCHO_INLINE_MAX else f' style="width: {ancho}ch"'
        out.append(
            f'<input type="text" class="{clase}" value="{esc(primera)}"{estilo} readonly tabindex="-1">'
        )
        widx += 1
        pos = end
    out.append(esc_body(texto[pos:]))
    body = "".join(out)
    lines = [l for l in DIALOGO_RE.split(body) if l.strip()] or [body]
    rows = "".join(
        f'<div class="item-row"><span>{line}</span></div>'
        for line in lines
    )
    return f'<div class="ejemplo"><span class="ejemplo-tag">Example</span>{rows}</div>'


ENUNCIADO_OPT_RE = re.compile(r"\*([^*]+)\*")


def render_enunciado(text):
    """*palabra* en el enunciado marca una opcion citada del libro (impresa en
    cursiva); por ahora la mostramos entre comillas -- si algun dia se quiere
    cursiva u otra cosa, solo cambia esta funcion, no los datos."""
    out = []
    pos = 0
    for m in ENUNCIADO_OPT_RE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        out.append(f'"{esc(m.group(1))}"')
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def render_wordbox(palabras):
    chips = "".join(f'<span class="word-chip">{esc(p)}</span>' for p in palabras)
    return f'<div class="wordbox">{chips}</div>'


GROUP_CONTROLS = """
        <div class="group-controls">
            <button onclick="checkGroup(this)">Check answers</button>
            <button class="ghost" onclick="revealGroup(this)">Show solutions</button>
            <span class="group-feedback"></span>
        </div>"""


def render_ejercicio_paginas(ej, granularidad="ejercicio"):
    """Devuelve una lista de fragmentos <section class="ejercicio">...</section>,
    una por pagina. granularidad="ejercicio" (por defecto, la que usa el sitio
    y el dashboard): una pagina con todos los items del ejercicio, como antes.
    granularidad="item" (variante experimental, ver --paginar=item): una
    pagina por item, repitiendo enunciado/grafico/recuadro en cada una -- la
    correccion (Check/Show solutions) siempre ocurre una vez por pagina, sea
    cual sea el contenido de esta."""
    grafico = ""
    ctx = ej.get("contexto_grafico")
    # grafico_necesario: false = el grafico es puramente decorativo (el texto
    # de los items ya trae todo lo necesario para resolver) -- calculado a
    # mano para las 126 unidades del libro, ver ejemplos/*.json. Si falta el
    # campo (ejercicio sin revisar todavia) se muestra por defecto, seguro.
    if ctx and ej.get("grafico_necesario", True):
        renderer = GRAFICO_RENDERERS.get(ctx["tipo"])
        if renderer is None:
            grafico = f'<p class="pista">[graphic "{esc(ctx["tipo"])}" not implemented yet]</p>'
        else:
            grafico = renderer(ctx["datos"])
    banco = ej.get("banco_palabras")
    # lista de listas = un recuadro DISTINTO por item (poco comun, ej. 122.1);
    # lista plana = un recuadro compartido por todo el ejercicio (lo normal).
    banco_por_item = bool(banco) and isinstance(banco[0], list)
    wordbox = render_wordbox(banco) if (banco and not banco_por_item) else ""

    items_data = ej["items"]
    ejemplo = ""
    ejemplo_wordbox = ""
    # el ejemplo resuelto solo se muestra si el enunciado lo referencia
    # explicitamente ("como en el ejemplo" / "as in the example(s)", fiel a
    # la traduccion del libro) o si se fuerza a mano con "forzar_ejemplo"
    # (p.ej. desde el dashboard) para casos que lo necesitan igual.
    hay_ejemplo = len(items_data) >= 2 and (
        ej.get("forzar_ejemplo") or re.search(r"example", ej["enunciado"], re.I)
    )
    if hay_ejemplo:
        if banco_por_item:
            ejemplo_wordbox = render_wordbox(banco[0])
            banco = banco[1:]
        ejemplo = render_ejemplo(items_data[0])
        items_data = items_data[1:]

    header = f'<p class="enunciado">{render_enunciado(ej["enunciado"])}</p>{grafico}{wordbox}'

    if granularidad == "item":
        paginas = []
        for i, it in enumerate(items_data):
            piezas = [header]
            if i == 0 and ejemplo:
                piezas += [ejemplo_wordbox, ejemplo]
            if banco_por_item:
                piezas.append(render_wordbox(banco[i]))
            piezas.append(render_item(i + 1, it))
            piezas.append(GROUP_CONTROLS)
            paginas.append(f'<section class="ejercicio">{"".join(piezas)}</section>')
        return paginas or [f'<section class="ejercicio">{header}{GROUP_CONTROLS}</section>']

    if banco_por_item:
        items = "".join(
            render_wordbox(banco[i]) + render_item(i + 1, it)
            for i, it in enumerate(items_data)
        )
    else:
        items = "".join(render_item(i, it) for i, it in enumerate(items_data, start=1))
    pagina = f"""<section class="ejercicio">
        {header}
        {ejemplo_wordbox}
        {ejemplo}
        {items}
        {GROUP_CONTROLS}
    </section>"""
    return [pagina]


def build_html(data, granularidad="ejercicio"):
    titulo = data.get("titulo", data["tema"])
    # "oculto": true permite desactivar un bloque de ejercicios sin borrarlo
    # del JSON (p.ej. desde el dashboard) -- simplemente no se renderiza.
    # tipologias_desactivadas (render_config.json) hace lo mismo pero a nivel
    # de tipologia entera (p.ej. T2, sin imagenes reales todavia). Un
    # ejercicio concreto de una tipologia desactivada puede igual mostrarse
    # con "forzar_mostrar": true -- caso confirmado a mano de que ESE
    # ejercicio no tiene el problema que motivo desactivar la tipologia
    # (p.ej. numeros-ordinales usa "directory", una tabla real, no el
    # sustituto de texto de "functional_images").
    tipologias_desactivadas = set(cargar_config().get("tipologias_desactivadas", []))
    ejercicios_visibles = [
        ej for ej in data["ejercicios"]
        if not ej.get("oculto")
        and (ej.get("tipologia") not in tipologias_desactivadas or ej.get("forzar_mostrar"))
    ]
    paginas = []
    for ej in ejercicios_visibles:
        paginas.extend(render_ejercicio_paginas(ej, granularidad))
    # cada "pagina" es un <section class="ejercicio"> completo (con su propio
    # Check/Show solutions); el JS solo muestra una a la vez y navega con
    # Anterior/Siguiente -- sin routing de servidor, todo client-side, sigue
    # siendo un unico HTML estatico por tema.
    pages_html = "".join(
        f'<div class="page" data-page="{i}" hidden>{p}</div>'
        for i, p in enumerate(paginas)
    )
    nav = """
    <div class="page-nav">
        <button class="ghost" id="btn-prev" onclick="showPage(currentPage - 1)">&larr; Anterior</button>
        <span id="page-indicator"></span>
        <button id="btn-next" onclick="showPage(currentPage + 1)">Siguiente &rarr;</button>
    </div>""" if paginas else ""
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
{pages_html}
{nav}
<script>{JS}</script>
</body>
</html>"""


def generate(tema, granularidad="ejercicio"):
    with open(os.path.join(CONTENT_DIR, f"{tema}.json"), encoding="utf-8") as f:
        data = json.load(f)
    html = build_html(data, granularidad)
    if granularidad == "item":
        # variante experimental para comparar "un item por pagina" -- aparte
        # de out/, no se integra al build de Netlify ni al dashboard todavia.
        out_dir = os.path.join(HERE, "out_preview")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{tema}--item.html")
    else:
        os.makedirs(OUT_DIR, exist_ok=True)
        out_path = os.path.join(OUT_DIR, f"{tema}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {out_path}")


def main():
    granularidad = "ejercicio"
    temas_arg = []
    for arg in sys.argv[1:]:
        if arg.startswith("--paginar="):
            granularidad = arg.split("=", 1)[1]
        else:
            temas_arg.append(arg)
    temas = temas_arg or sorted(
        fn[:-5] for fn in os.listdir(CONTENT_DIR) if fn.endswith(".json")
    )
    for tema in temas:
        generate(tema, granularidad)


if __name__ == "__main__":
    main()
