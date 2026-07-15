#!/usr/bin/env python3
"""
Paso 2 del pipeline: para cada unidad de mapa_unidades.json, extrae su pagina
de EJERCICIOS (no la de teoria) via Gemini vision.

Deliberadamente NO le pedimos a Gemini "solucion_correcta": las paginas de
ejercicio del libro casi nunca traen la respuesta impresa (solo alguna marca
a boligrafo suelta e incompleta del dueno anterior), asi que inventar
soluciones aqui seria el mismo riesgo de "que lo haga mal" del que veniamos
huyendo. Las respuestas de verdad se sacan del solucionario impreso en
extract_soluciones.py y se cruzan en merge_ejemplos.py.

Uso:
    export GEMINI_API_KEY="tu-key"
    python3 extract_ejercicios.py                 # todas las unidades del mapa
    python3 extract_ejercicios.py 5 27 38          # solo estas unidades
"""
import json
import os
import sys

from gemini_client import GeminiVisionClient

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRO_DIR = os.path.join(HERE, "..", "..", "libro")
GEMINI_DIR = os.path.join(HERE, "..", "..", "Gemini")
MAPA_PATH = os.path.join(HERE, "mapa_unidades.json")
CHECKPOINT_PATH = os.path.join(HERE, ".estado_ejercicios.json")
RAW_DIR = os.path.join(HERE, "ejercicios_raw")

PROMPT_TMPL = """Estas viendo la pagina de EJERCICIOS de una unidad de \
"Gramatica de uso del espanol" (Aragones/Palencia). Transcribe su contenido \
a JSON estructurado siguiendo EXACTAMENTE estas reglas de sintaxis:

{reglas_sintaxis}

Catalogo de tipologias (usa el codigo T1-T7 que mejor describa cada bloque \
numerado de la pagina, ej. "5.1", "5.2"):

{tipologias}

Devuelve JSON exacto, sin markdown, con esta forma:
{{
  "ejercicios": [
    {{
      "subejercicio": "5.1",
      "tipologia": "T2",
      "enunciado": "texto del enunciado tal cual aparece (en espanol)",
      "banco_palabras": ["palabra1", "palabra2"],
      "contexto_grafico": {{"tipo": "directory|family_tree|clocks|visual_count|map|vocabulary_box|functional_images|instruments_visual|descripcion_libre", "datos": [...]}},
      "items": [
        {{"texto_enunciado": "frase con _____ o (opcion1/opcion2) segun corresponda"}}
      ]
    }}
  ]
}}

Reglas adicionales:
- "banco_palabras" solo si hay una caja/recuadro de palabras para elegir; si no, omite el campo.
- "contexto_grafico" solo si hay un apoyo visual (dibujo, tabla, arbol, reloj...); si no, omite el campo.
  Si el grafico no encaja en ninguno de los tipos listados, usa "descripcion_libre" y describe \
en "datos" (como lista de strings) lo que se ve con suficiente detalle para reconstruirlo.
- NO incluyas ningun campo de solucion/respuesta: no aparece impresa en esta pagina y no debes \
inventarla.
- No proceses la pagina de TEORIA (explicaciones gramaticales) si por error ves esa en vez de la \
de ejercicios: en ese caso devuelve {{"ejercicios": []}}.
- Transcribe el numero exacto de huecos "_____" y de elecciones "(a/b)" tal como aparecen impresos.
"""


def load_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    with open(MAPA_PATH, encoding="utf-8") as f:
        mapa = json.load(f)
    unidades = mapa["unidades"]

    reglas_sintaxis = load_text(os.path.join(GEMINI_DIR, "prompt.txt"))
    tipologias = load_text(os.path.join(GEMINI_DIR, "Exercises_typology.md"))
    prompt = PROMPT_TMPL.format(reglas_sintaxis=reglas_sintaxis, tipologias=tipologias)

    seleccion = sys.argv[1:] or sorted(unidades.keys(), key=int)

    os.makedirs(RAW_DIR, exist_ok=True)
    client = GeminiVisionClient(checkpoint_path=CHECKPOINT_PATH)

    for num in seleccion:
        if num not in unidades:
            print(f"⚠️  unidad {num} no esta en {MAPA_PATH}, se salta")
            continue

        info = unidades[num]
        key = f"ejercicio:{num}"
        scan_path = os.path.join(LIBRO_DIR, info["scan_ejercicios"])
        out_path = os.path.join(RAW_DIR, f"{num}.json")

        if client.is_done(key):
            print(f"  ya procesada unidad {num}, se salta")
            continue
        if not os.path.exists(scan_path):
            print(f"⚠️  unidad {num}: no existe {scan_path}")
            client.mark_failed(key, "scan no encontrado")
            continue

        print(f"→ unidad {num} ({info['titulo']}) -- {info['scan_ejercicios']}")
        try:
            raw = client.call(scan_path, prompt)
            data = json.loads(raw)
        except Exception as e:
            print(f"  ⚠️  fallo: {e}")
            client.mark_failed(key, e)
            continue

        data["unidad"] = int(num)
        data["titulo_libro"] = info["titulo"]
        data["scan"] = info["scan_ejercicios"]

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        client.mark_done(key, {"archivo": out_path, "n_ejercicios": len(data.get("ejercicios", []))})
        print(f"  ✅ {len(data.get('ejercicios', []))} ejercicio(s) -> {out_path}")


if __name__ == "__main__":
    main()
