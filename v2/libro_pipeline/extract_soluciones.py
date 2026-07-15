#!/usr/bin/env python3
"""
Paso 3 del pipeline: transcribe la seccion "Soluciones a los ejercicios" del
libro (texto impreso denso, ~10 unidades por pagina) via Gemini vision.

Es la fuente de verdad de las respuestas -- ver la nota en extract_ejercicios.py
sobre por que no le pedimos respuestas a la pagina de ejercicio en si.

Requiere haber corrido extract_toc.py antes (usa la seccion
"Soluciones a los ejercicios" de mapa_unidades.json para saber el rango de
scans a procesar).

Uso:
    export GEMINI_API_KEY="tu-key"
    python3 extract_soluciones.py
"""
import json
import os

from gemini_client import GeminiVisionClient

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRO_DIR = os.path.join(HERE, "..", "..", "libro")
MAPA_PATH = os.path.join(HERE, "mapa_unidades.json")
CHECKPOINT_PATH = os.path.join(HERE, ".estado_soluciones.json")
OUT_PATH = os.path.join(HERE, "soluciones.json")

PROMPT = """Estas viendo una pagina de la seccion "Soluciones a los ejercicios" \
de "Gramatica de uso del espanol" (Aragones/Palencia). Cada unidad tiene uno o \
mas subejercicios marcados como "N.M." (ej. "38.1.", "38.2."), y dentro de cada \
uno una lista numerada de respuestas "1. ... 2. ... 3. ...".

Cuando un numero de la lista trae varias respuestas separadas por punto y coma \
(ej. "5. Le; se; la; Se; la."), son las respuestas de VARIOS huecos seguidos \
dentro del MISMO item -- no items distintos.

Devuelve JSON exacto, sin markdown:
{
  "entradas": [
    {
      "unidad": 38,
      "subejercicio": "38.1",
      "items": [["lo"], ["Lo"], ["la"], ["las"], ["Le", "se", "la", "Se", "la"]]
    }
  ]
}

Reglas:
- "items" es una lista ordenada; cada elemento es a su vez una lista con las \
respuestas de ese item EN ORDEN (una sola respuesta si el item tenia un solo hueco).
- Incluye TODAS las unidades y subejercicios visibles en esta pagina, no resumas.
- Si una respuesta es el simbolo de conjunto vacio (a veces escrito "0" o "ø" \
por error de imprenta/escaneo cuando la solucion es la ausencia del articulo), \
transcribela como "ø".
- Si la pagina no pertenece a esta seccion o no tiene contenido reconocible, \
devuelve {"entradas": []}.
"""


def main():
    with open(MAPA_PATH, encoding="utf-8") as f:
        mapa = json.load(f)

    seccion = mapa.get("secciones", {}).get("Soluciones a los ejercicios")
    if not seccion:
        raise SystemExit(
            'No hay seccion "Soluciones a los ejercicios" en mapa_unidades.json -- '
            "corre extract_toc.py primero (quiza con --end mas alto)."
        )

    scan_inicio = seccion["scan_inicio"]
    scan_fin = seccion["scan_fin"]

    soluciones = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as f:
            soluciones = json.load(f)

    client = GeminiVisionClient(checkpoint_path=CHECKPOINT_PATH)

    for scan_index in range(scan_inicio, scan_fin + 1):
        key = f"solucion:{scan_index:03d}"
        path = os.path.join(LIBRO_DIR, f"libro-rojo-{scan_index:03d}.png")

        if client.is_done(key):
            print(f"  ya procesado libro-rojo-{scan_index:03d}.png, se salta")
            continue
        if not os.path.exists(path):
            print(f"  (sin scan {scan_index:03d}, se salta)")
            continue

        print(f"→ libro-rojo-{scan_index:03d}.png")
        try:
            raw = client.call(path, PROMPT)
            data = json.loads(raw)
        except Exception as e:
            print(f"  ⚠️  fallo: {e}")
            client.mark_failed(key, e)
            continue

        for entrada in data.get("entradas", []):
            sub = entrada["subejercicio"]
            if sub in soluciones:
                print(f"  ⚠️  {sub} ya visto, se mantiene el primero")
                continue
            soluciones[sub] = {"unidad": entrada["unidad"], "items": entrada["items"]}

        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(soluciones, f, ensure_ascii=False, indent=2, sort_keys=True)

        client.mark_done(key, {"n_entradas": len(data.get("entradas", []))})
        print(f"  ✅ {len(data.get('entradas', []))} subejercicio(s)")

    print(f"\n✅ {len(soluciones)} subejercicio(s) con solucion en {OUT_PATH}")


if __name__ == "__main__":
    main()
