#!/usr/bin/env python3
"""
Paso 1 del pipeline de digitalizacion del libro: lee las paginas de indice
(tabla de contenidos) via Gemini vision y construye el mapa unidad -> pagina.

De cada pagina candidata solo nos interesa si es una pagina de indice; el
prompt le pide a Gemini que diga "es_indice: false" si no lo es, asi no hace
falta acotar a mano el rango exacto de paginas de indice (se procesa un
rango con margen de sobra, barato porque solo se ejecuta una vez).

Con el numero de pagina IMPRESA de cada unidad calculamos el scan de su
pagina de ejercicios (offset fijo comprobado a mano: scan_index = pagina + 2,
porque la pagina de ejercicios es la siguiente a la de teoria que lista el
indice, y pagina_impresa = scan_index - 1).

Uso:
    export OPENAI_API_KEY="tu-key"
    python3 extract_toc.py [--start 4] [--end 13]
    python3 extract_toc.py --provider gemini  # comparar con Gemini

Salida: libro_pipeline/mapa_unidades.json
"""
import argparse
import glob
import json
import os
import re

from openai_client import InsufficientQuotaError
from providers import DEFAULT_PROVIDER, build_client

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRO_DIR = os.path.join(HERE, "..", "libro")
OUT_PATH = os.path.join(HERE, "mapa_unidades.json")

SCAN_NAME_RE = re.compile(r"^libro-rojo-(\d{3})\.png$")

TOC_PROMPT = """Esta es una pagina escaneada de un libro de gramatica espanola \
("Gramatica de uso del espanol", Aragones/Palencia). Puede ser una pagina de \
INDICE (tabla de contenidos) o puede ser cualquier otra cosa (portada, prologo, \
teoria, ejercicios, solucionario...).

Si la pagina NO es una pagina de indice/tabla de contenidos, responde exactamente:
{"es_indice": false}

Si SI es una pagina de indice, responde con este JSON exacto (sin markdown, sin texto extra):
{
  "es_indice": true,
  "entradas": [
    {"tipo": "unidad", "numero": 1, "titulo": "el hijo, la hija -- Masculino, femenino (1)", "pagina": 10},
    {"tipo": "seccion", "nombre": "Soluciones a los ejercicios", "pagina": 269}
  ]
}

Reglas:
- "tipo":"unidad" para cada linea "Unidad N: ...", con el numero de pagina IMPRESO \
que aparece a la derecha (tras los puntos suspensivos).
- "tipo":"seccion" para lineas que no son unidades numeradas (ej. "Otras cuestiones", \
"Indice analitico", "Soluciones a los ejercicios"), con su pagina.
- "titulo" combina el ejemplo en cursiva y la descripcion gramatical tal como aparecen \
en la pagina, separados por " -- ".
- No inventes unidades ni paginas que no veas literalmente en la imagen.
- Devuelve TODAS las entradas visibles en esta pagina, no resumas.
"""


def scan_path(scan_index):
    return os.path.join(LIBRO_DIR, f"libro-rojo-{scan_index:03d}.png")


def available_scan_indices():
    indices = []
    for path in glob.glob(os.path.join(LIBRO_DIR, "libro-rojo-*.png")):
        m = SCAN_NAME_RE.match(os.path.basename(path))
        if m:
            indices.append(int(m.group(1)))
    return sorted(indices)


def main():
    parser = argparse.ArgumentParser(description="Extrae el indice del libro via Gemini vision")
    parser.add_argument("--start", type=int, default=4, help="primer scan candidato a indice (default 4)")
    parser.add_argument("--end", type=int, default=13, help="ultimo scan candidato a indice, inclusive (default 13)")
    parser.add_argument("--provider", choices=["gemini", "openai"], default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=None, help="override del modelo (default: el de cada proveedor)")
    args = parser.parse_args()

    disponibles = set(available_scan_indices())
    checkpoint_path = os.path.join(HERE, f".estado_toc_{args.provider}.json")
    client = build_client(args.provider, checkpoint_path, model=args.model)

    unidades = {}
    secciones = {}

    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as f:
            existente = json.load(f)
            unidades.update(existente.get("unidades", {}))
            secciones.update(existente.get("secciones", {}))

    for scan_index in range(args.start, args.end + 1):
        if scan_index not in disponibles:
            print(f"  (sin scan {scan_index:03d}, se salta)")
            continue

        key = f"toc:{scan_index:03d}"
        path = scan_path(scan_index)

        if client.is_done(key):
            print(f"  ya procesado libro-rojo-{scan_index:03d}.png, se salta")
            continue

        print(f"→ libro-rojo-{scan_index:03d}.png")
        try:
            raw = client.call(path, TOC_PROMPT)
            data = json.loads(raw, strict=False)  # el modelo a veces mete saltos de linea literales en strings
        except InsufficientQuotaError as e:
            print(f"\n🛑 {e}\nParando aqui (se guarda el progreso acumulado) -- relanza el mismo comando cuando haya saldo.")
            break
        except Exception as e:
            print(f"  ⚠️  fallo procesando {scan_index:03d}: {e}")
            client.mark_failed(key, e)
            continue

        if not data.get("es_indice"):
            print("  (no es pagina de indice)")
            client.mark_done(key, {"es_indice": False})
            continue

        for entrada in data.get("entradas", []):
            if entrada.get("tipo") == "unidad":
                num = str(entrada["numero"])
                if num in unidades and unidades[num] != entrada:
                    print(f"  ⚠️  unidad {num} ya vista con otro valor, se mantiene la primera")
                    continue
                unidades[num] = {"titulo": entrada["titulo"], "pagina": entrada["pagina"]}
            elif entrada.get("tipo") == "seccion":
                secciones[entrada["nombre"]] = {"pagina": entrada["pagina"]}

        client.mark_done(key, {"es_indice": True, "n_entradas": len(data.get("entradas", []))})
        print(f"  ✅ {len(data.get('entradas', []))} entrada(s)")

    # pagina impresa de la unidad -> pagina de ejercicios (la siguiente) -> scan de esa pagina
    for num, info in unidades.items():
        pagina_teoria = info["pagina"]
        pagina_ejercicios = pagina_teoria + 1
        info["pagina_ejercicios"] = pagina_ejercicios
        info["scan_ejercicios"] = f"libro-rojo-{pagina_ejercicios + 1:03d}.png"

    max_scan = max(disponibles) if disponibles else None
    if "Soluciones a los ejercicios" in secciones:
        inicio = secciones["Soluciones a los ejercicios"]["pagina"]
        secciones["Soluciones a los ejercicios"]["scan_inicio"] = inicio + 1
        secciones["Soluciones a los ejercicios"]["scan_fin"] = max_scan

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"unidades": unidades, "secciones": secciones}, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"\n✅ {len(unidades)} unidad(es) y {len(secciones)} seccion(es) escritas en {OUT_PATH}")
    if "Soluciones a los ejercicios" not in secciones:
        print('⚠️  No se encontro la seccion "Soluciones a los ejercicios" -- revisa el rango --start/--end')


if __name__ == "__main__":
    main()
