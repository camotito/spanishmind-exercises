#!/usr/bin/env python3
"""
Paso 3 del pipeline: transcribe la seccion "Soluciones a los ejercicios" del
libro (texto impreso denso, ~10 unidades por pagina) via vision.

Es la fuente de verdad de las respuestas -- ver la nota en extract_ejercicios.py
sobre por que no le pedimos respuestas a la pagina de ejercicio en si.

Esta pagina es la mas dificil de transcribir del libro (texto denso, letra
pequena, muchas respuestas cortas parecidas -- lo/la/le/los/las/les). Se
comprobo con un piloto que TANTO Gemini 3.1 Flash Lite como GPT-5.6-sol
cometen errores de CONTENIDO ahi (no solo de conteo de huecos, que ya
validamos en merge_ejemplos.py) -- por eso este script soporta --provider
gemini|openai por separado, y compare_soluciones.py cruza ambas salidas:
donde coinciden, alta confianza; donde discrepan, se marca para revision
manual en vez de aceptar cualquiera a ciegas.

Requiere haber corrido extract_toc.py antes (usa la seccion
"Soluciones a los ejercicios" de mapa_unidades.json para saber el rango de
scans a procesar).

Decision (2026-07-15): en las 5 discrepancias verificadas contra el libro
fisico hasta ahora (unidades 27, 38, 44), OpenAI acerto las 5 y Gemini fallo
las 5 -- por eso ya no hace falta correr ambos proveedores por defecto.
--provider sigue disponible por si se quiere volver a contrastar.

Uso:
    export OPENAI_API_KEY="tu-key"
    python3 extract_soluciones.py                            # OpenAI por defecto
    python3 extract_soluciones.py --provider gemini           # comparar con Gemini
    python3 extract_soluciones.py --start 275 --end 275
"""
import argparse
import json
import os

from openai_client import InsufficientQuotaError
from providers import DEFAULT_PROVIDER, build_client, call_client

PROMPT = """Estas viendo una pagina de la seccion "Soluciones a los ejercicios" \
de "Gramatica de uso del espanol" (Aragones/Palencia). Cada unidad tiene uno o \
mas subejercicios marcados como "N.M." (ej. "38.1.", "38.2."), y dentro de cada \
uno una lista numerada de respuestas "1. ... 2. ... 3. ...".

Cuando un numero de la lista trae varias respuestas separadas por punto y coma \
(ej. "5. Le; se; la; Se; la."), son las respuestas de VARIOS huecos seguidos \
dentro del MISMO item -- no items distintos.

Si un numero trae dos respuestas separadas por barra (ej. "3. lo/le."), es UNA \
sola respuesta con dos formas igualmente validas -- transcribela tal cual, \
como un unico string "lo/le", no la separes en dos elementos.

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
- Transcribe la letra mayuscula/minuscula tal como aparece impresa.
- Si una respuesta es el simbolo de conjunto vacio (a veces escrito "0" o "ø" \
por error de imprenta/escaneo cuando la solucion es la ausencia del articulo), \
transcribela como "ø".
- Si la pagina no pertenece a esta seccion o no tiene contenido reconocible, \
devuelve {"entradas": []}.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "entradas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "unidad": {"type": "integer"},
                    "subejercicio": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "required": ["unidad", "subejercicio", "items"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["entradas"],
    "additionalProperties": False,
}

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRO_DIR = os.path.join(HERE, "..", "..", "libro")
MAPA_PATH = os.path.join(HERE, "mapa_unidades.json")


def main():
    parser = argparse.ArgumentParser(description="Extrae el solucionario via vision")
    parser.add_argument("--provider", choices=["gemini", "openai"], default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=None, help="override del modelo (default: el de cada proveedor)")
    parser.add_argument("--start", type=int, help="scan inicial (default: el de mapa_unidades.json)")
    parser.add_argument("--end", type=int, help="scan final, inclusive (default: el de mapa_unidades.json)")
    args = parser.parse_args()

    out_path = os.path.join(HERE, f"soluciones_{args.provider}.json")

    if args.start is not None and args.end is not None:
        scan_inicio, scan_fin = args.start, args.end
    else:
        with open(MAPA_PATH, encoding="utf-8") as f:
            mapa = json.load(f)
        seccion = mapa.get("secciones", {}).get("Soluciones a los ejercicios")
        if not seccion:
            raise SystemExit(
                'No hay seccion "Soluciones a los ejercicios" en mapa_unidades.json -- '
                "corre extract_toc.py primero (quiza con --end mas alto), o usa --start/--end."
            )
        scan_inicio = seccion["scan_inicio"]
        scan_fin = seccion["scan_fin"]

    soluciones = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            soluciones = json.load(f)

    checkpoint_path = os.path.join(HERE, f".estado_soluciones_{args.provider}.json")
    client = build_client(args.provider, checkpoint_path, model=args.model)

    for scan_index in range(scan_inicio, scan_fin + 1):
        key = f"solucion:{scan_index:03d}"
        path = os.path.join(LIBRO_DIR, f"libro-rojo-{scan_index:03d}.png")

        if client.is_done(key):
            print(f"  ya procesado libro-rojo-{scan_index:03d}.png, se salta")
            continue
        if not os.path.exists(path):
            print(f"  (sin scan {scan_index:03d}, se salta)")
            continue

        print(f"→ libro-rojo-{scan_index:03d}.png ({args.provider})")
        try:
            raw = call_client(client, args.provider, path, PROMPT, schema=SCHEMA)
            data = json.loads(raw, strict=False)  # el modelo a veces mete saltos de linea literales en strings
        except InsufficientQuotaError as e:
            print(f"\n🛑 {e}\nParando el pipeline aqui -- relanza el mismo comando cuando haya saldo, retoma solo.")
            return
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

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(soluciones, f, ensure_ascii=False, indent=2, sort_keys=True)

        client.mark_done(key, {"n_entradas": len(data.get("entradas", []))})
        print(f"  ✅ {len(data.get('entradas', []))} subejercicio(s)")

    print(f"\n✅ {len(soluciones)} subejercicio(s) con solucion en {out_path}")


if __name__ == "__main__":
    main()
