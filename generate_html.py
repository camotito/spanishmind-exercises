#!/usr/bin/env python3
"""
Genera el HTML final del ejercicio a partir de content/<tema>.json.
Puro script, sin LLM.

Uso:
    python3 generate_html.py                       # menú interactivo
    python3 generate_html.py u07-preterito-perfecto
    python3 generate_html.py --all
"""
import json
import os
import sys

CONTENT_DIR = "content"
OUT_DIR = "."  # raíz del repo, junto a los demás .html

CSS = """
:root {
    --color-bg: #FBF7F0;
    --color-primary: #C1440E;
    --color-secondary: #2E4053;
    --color-accent: #E9B44C;
    --color-correct: #4F7942;
    --color-wrong: #B33A3A;
    --color-text: #2B2B2B;
    --font-heading: 'Playfair Display', serif;
    --font-body: 'DM Sans', sans-serif;
}
* { box-sizing: border-box; }
body {
    font-family: var(--font-body);
    background: var(--color-bg);
    color: var(--color-text);
    max-width: 700px;
    margin: 40px auto;
    padding: 0 20px;
    line-height: 1.6;
}
h1 { font-family: var(--font-heading); color: var(--color-secondary); }
.ejercicio {
    background: white;
    border: 1px solid #e5ddd0;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}
.ejercicio p.enunciado { font-weight: 600; margin-bottom: 12px; }
input[type="text"] {
    font-family: var(--font-body);
    padding: 8px;
    border: 1px solid #ccc;
    border-radius: 4px;
    width: 200px;
}
button {
    font-family: var(--font-body);
    background: var(--color-primary);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    margin-top: 8px;
}
button:hover { opacity: 0.9; }
.opciones label { display: block; margin: 4px 0; cursor: pointer; }
.feedback { margin-top: 8px; font-weight: 600; display: none; }
.feedback.correct { color: var(--color-correct); }
.feedback.wrong { color: var(--color-wrong); }
.pista { font-size: 0.85rem; color: #777; margin-top: 4px; font-style: italic; }
#resumen {
    text-align: center;
    font-family: var(--font-heading);
    font-size: 1.3rem;
    margin-top: 30px;
    display: none;
}
"""

JS = """
function checkFill(id, respuesta) {
    const input = document.getElementById(id);
    const fb = document.getElementById(id + '-fb');
    const ok = input.value.trim().toLowerCase() === respuesta.toLowerCase();
    fb.textContent = ok ? '✔ Correct' : '✘ Try again';
    fb.className = 'feedback ' + (ok ? 'correct' : 'wrong');
    fb.style.display = 'block';
    if (ok) input.dataset.solved = '1';
    updateResumen();
}
function checkChoice(id, respuesta) {
    const selected = document.querySelector(`input[name="${id}"]:checked`);
    const fb = document.getElementById(id + '-fb');
    if (!selected) return;
    const ok = selected.value === respuesta;
    fb.textContent = ok ? '✔ Correct' : '✘ Try again';
    fb.className = 'feedback ' + (ok ? 'correct' : 'wrong');
    fb.style.display = 'block';
    if (ok) selected.closest('.ejercicio').dataset.solved = '1';
    updateResumen();
}
function updateResumen() {
    const total = document.querySelectorAll('.ejercicio').length;
    const solved = document.querySelectorAll('.ejercicio[data-solved="1"], input[data-solved="1"]').length;
    const resumen = document.getElementById('resumen');
    if (solved >= total) {
        resumen.textContent = `¡Completado! ${solved}/${total}`;
        resumen.style.display = 'block';
    }
}
"""


def render_fill_blank(idx, ej):
    eid = f"ej{idx}"
    oracion = ej["oracion"].replace("___", f'<input type="text" id="{eid}">')
    pista = f'<p class="pista">💡 {ej["pista"]}</p>' if ej.get("pista") else ""
    return f"""
    <div class="ejercicio">
        <p class="enunciado">{oracion}</p>
        <button onclick="checkFill('{eid}', '{ej['respuesta']}')">Check</button>
        {pista}
        <p class="feedback" id="{eid}-fb"></p>
    </div>"""


def render_multiple_choice(idx, ej):
    eid = f"ej{idx}"
    opciones = "".join(
        f'<label><input type="radio" name="{eid}" value="{o}"> {o}</label>'
        for o in ej["opciones"]
    )
    nota = f'<p class="pista">💡 {ej["nota"]}</p>' if ej.get("nota") else ""
    return f"""
    <div class="ejercicio" data-solved="0">
        <p class="enunciado">{ej['pregunta']}</p>
        <div class="opciones">{opciones}</div>
        <button onclick="checkChoice('{eid}', '{ej['respuesta']}')">Check</button>
        {nota}
        <p class="feedback" id="{eid}-fb"></p>
    </div>"""


def render_gender_classification(idx, ej):
    eid = f"ej{idx}"
    opciones = "".join(
        f'<label><input type="radio" name="{eid}" value="{o}"> {o}</label>'
        for o in ["masculino", "femenino"]
    )
    nota = f'<p class="pista">💡 {ej["nota"]}</p>' if ej.get("nota") else ""
    return f"""
    <div class="ejercicio" data-solved="0">
        <p class="enunciado">{ej['palabra']}</p>
        <div class="opciones">{opciones}</div>
        <button onclick="checkChoice('{eid}', '{ej['respuesta']}')">Check</button>
        {nota}
        <p class="feedback" id="{eid}-fb"></p>
    </div>"""


def render_error_correction(idx, ej):
    eid = f"ej{idx}"
    return f"""
    <div class="ejercicio">
        <p class="enunciado">Fix the error: {ej['oracion_incorrecta']}</p>
        <input type="text" id="{eid}">
        <button onclick="checkFill('{eid}', '{ej['oracion_correcta']}')">Check</button>
        <p class="pista">💡 {ej.get('explicacion', '')}</p>
        <p class="feedback" id="{eid}-fb"></p>
    </div>"""


def render_transform(idx, ej):
    eid = f"ej{idx}"
    return f"""
    <div class="ejercicio">
        <p class="enunciado">{ej['instruccion']}: {ej['entrada']}</p>
        <input type="text" id="{eid}">
        <button onclick="checkFill('{eid}', '{ej['respuesta']}')">Check</button>
        <p class="feedback" id="{eid}-fb"></p>
    </div>"""


RENDERERS = {
    "fill-blank": render_fill_blank,
    "multiple-choice": render_multiple_choice,
    "gender-classification": render_gender_classification,
    "error-correction": render_error_correction,
    "transform": render_transform,
}


def build_html(data):
    unidad = data["unidad"]
    body = "".join(
        RENDERERS[ej["tipo"]](i, ej) for i, ej in enumerate(data["ejercicios"])
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{unidad}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<h1>{unidad.replace('-', ' ').title()}</h1>
{body}
<p id="resumen"></p>
<script>{JS}</script>
</body>
</html>"""


def generate(topic):
    in_path = os.path.join(CONTENT_DIR, f"{topic}.json")
    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)

    html = build_html(data)
    out_path = os.path.join(OUT_DIR, f"{topic}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ {out_path}")


def list_topics():
    """Devuelve los temas disponibles (nombres de .json sin extension), ordenados."""
    if not os.path.isdir(CONTENT_DIR):
        sys.exit(f"No existe la carpeta '{CONTENT_DIR}'")
    return sorted(
        fname[:-5] for fname in os.listdir(CONTENT_DIR) if fname.endswith(".json")
    )


def print_topics(topics):
    for i, topic in enumerate(topics, start=1):
        print(f"{i:3d}. {topic}")


def parse_selection(raw, total):
    """Acepta '3', '1,4,7', '1-5' o combinaciones tipo '1-3,8,10'."""
    indices = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, end = chunk.split("-", 1)
            start, end = int(start), int(end)
            indices.update(range(start, end + 1))
        else:
            indices.add(int(chunk))

    for i in indices:
        if not (1 <= i <= total):
            raise ValueError(f"Numero fuera de rango: {i}")

    return sorted(indices)


def main():
    # Modo directo: python3 generate_html.py <tema>... | --all
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--all":
            for topic in list_topics():
                generate(topic)
        else:
            for topic in sys.argv[1:]:
                generate(topic)
        return

    # Modo interactivo: muestra los JSON disponibles y pide elegir
    topics = list_topics()
    if not topics:
        sys.exit(f"No hay ficheros .json en '{CONTENT_DIR}'")

    print_topics(topics)
    raw = input("\nElige tema(s) por numero (ej: 3 | 1,4,7 | 1-5 | all): ").strip()

    if raw.lower() == "all":
        seleccion = list(range(1, len(topics) + 1))
    else:
        try:
            seleccion = parse_selection(raw, len(topics))
        except ValueError as e:
            sys.exit(f"Selección inválida: {e}")

    if not seleccion:
        sys.exit("No se seleccionó ningún tema.")

    for i in seleccion:
        generate(topics[i - 1])


if __name__ == "__main__":
    main()
