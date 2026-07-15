#!/usr/bin/env python3
"""
Genera contenido de ejercicios en bulk vía API de Gemini, infiriendo
automaticamente los tiempos verbales permitidos según el indice del curso.

Uso:
    export GEMINI_API_KEY="tu-key"
    python3 generate_bulk.py [--indice ruta/indice.yaml]

    Muestra una lista numerada de los temas del indice (con su ejemplo) y
    pide seleccionar uno o mas por numero (ej: "3", "1,4,7" o "1-5").

Salida: content/<tema>.json (uno por tema elegido)
"""
import argparse
import json
import os
import sys
import time
import yaml
import requests
from validate_content import validate

DEFAULT_INDICE_PATH = "indice.yaml"
DEFAULT_PROMPT_PATH = "prompt.txt"
OUT_DIR = "content"
MODEL = "gemini-3.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def load_prompt_template(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_indice(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def allowed_tenses(indice, topic, indice_path):
    """Lee tiempos_permitidos ya precalculado (ver compute_tenses.py)."""
    for t in indice:
        if t["tema"] == topic:
            tenses = t.get("tiempos_permitidos")
            if not tenses:
                raise ValueError(
                    f"'{topic}' no tiene tiempos_permitidos. Ejecuta compute_tenses.py primero."
                )
            return tenses
    raise ValueError(f"Tema '{topic}' no esta en {indice_path}")


def print_indice(indice):
    for i, t in enumerate(indice, start=1):
        ejemplo = t.get("ejemplo", "")
        print(f"{i:3d}. {t['tema']:60s} {ejemplo}")


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


def call_gemini(prompt, max_retries=5):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("Falta GEMINI_API_KEY en el entorno")

    for attempt in range(max_retries):
        resp = requests.post(
            f"{API_URL}?key={key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=60,
        )
        if resp.status_code == 429 and attempt < max_retries - 1:
            wait = 2 ** attempt * 5  # 5, 10, 20, 40...
            print(f"  ⏳ 429 (rate limit), reintentando en {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        break

    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    # Limpieza por si Gemini envuelve en ```json
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text.removeprefix("json").strip()

    return text


def generate_topic(indice, topic, indice_path, prompt_template):
    tenses = allowed_tenses(indice, topic, indice_path)
    prompt = prompt_template.replace("{topic}", topic).replace(
        "{tenses}", ", ".join(tenses)
    )

    print(f"→ {topic} | tiempos permitidos: {tenses}")
    raw = call_gemini(prompt)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"{topic}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(raw)

    try:
        validate(out_path)
    except SystemExit:
        print(f"  ⚠️  {topic} generado pero no paso la validacion, revisa {out_path}")
        return

    print(f"  ✅ guardado en {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Genera ejercicios en bulk vía Gemini")
    parser.add_argument(
        "--indice",
        default=DEFAULT_INDICE_PATH,
        help=f"Ruta al archivo indice.yaml (default: {DEFAULT_INDICE_PATH})",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT_PATH,
        help=f"Ruta al fichero con el prompt (default: {DEFAULT_PROMPT_PATH})",
    )
    args = parser.parse_args()

    indice = load_indice(args.indice)
    prompt_template = load_prompt_template(args.prompt)

    print_indice(indice)
    raw = input("\nElige tema(s) por numero (ej: 3 | 1,4,7 | 1-5): ").strip()
    try:
        seleccion = parse_selection(raw, len(indice))
    except ValueError as e:
        sys.exit(f"Selección inválida: {e}")

    if not seleccion:
        sys.exit("No se seleccionó ningún tema.")

    for n, i in enumerate(seleccion):
        if n > 0:
            time.sleep(10)  # margen entre llamadas para evitar 429
        topic = indice[i - 1]["tema"]
        generate_topic(indice, topic, args.indice, prompt_template)


if __name__ == "__main__":
    main()
