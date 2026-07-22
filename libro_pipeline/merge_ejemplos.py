#!/usr/bin/env python3
"""
Paso 4 (final) del pipeline: cruza ejercicios_raw/<unidad>.json (enunciados e
items, sin respuestas) con soluciones.json (la clave impresa del libro) y
escribe ejemplos/<tema>.json -- el banco de ejemplos reales, separado de
content/<tema>.json (el banco final que se sirve, ampliable por LLM).

El "titulo" de la pagina de indice viene combinado como "ejemplo -- gramatica"
(ver extract_toc.py); lo partimos para rellenar "titulo" (amigable) y
"descripcion_gramatical" (tecnico, no se muestra) igual que en index.yaml.

Cualquier desajuste (huecos != respuestas, subejercicio sin solucion en el
libro) se deja constancia en cada item con "revisar": true y se lista en el
resumen final -- nunca se descarta en silencio ni se inventa una respuesta.

Uso:
    python3 merge_ejemplos.py                # todas las unidades con raw disponible
    python3 merge_ejemplos.py 5 27 38         # solo estas unidades
"""
import glob
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
V2_DIR = os.path.join(HERE, "..")
RAW_DIR = os.path.join(HERE, "ejercicios_raw")
SOLUCIONES_PATH = os.path.join(HERE, "soluciones.json")
INDEX_PATH = os.path.join(V2_DIR, "index.yaml")
EJEMPLOS_DIR = os.path.join(V2_DIR, "ejemplos")

# mismos patrones que el tokenizador de render.py -- deben mantenerse en sync
CHOICE_RE = re.compile(r"\(([^()]*?/[^()]*?)\)")
BLANK = "_____"

# algunas extracciones (sobre todo de antes de que el prompt lo prohibiera
# explicitamente) incluyen el numero de lista del item dentro del propio texto
# (ej. "1. (mujer) _____"); render.py ya numera cada item por su cuenta, asi
# que aqui se quita para no duplicarlo -- barato (regex) y cubre tanto lo ya
# extraido como lo nuevo, sin tener que volver a pagar la extraccion.
NUMBERING_RE = re.compile(r"^\s*\d{1,3}[.\)]\s+")


def n_huecos(texto):
    return len(CHOICE_RE.findall(texto)) + texto.count(BLANK)


def tema_por_unidad():
    with open(INDEX_PATH, encoding="utf-8") as f:
        indice = yaml.safe_load(f)
    return {str(t["unidad_libro"]): t["tema"] for t in indice if t.get("unidad_libro")}


def split_titulo(titulo_libro):
    if " -- " in titulo_libro:
        ejemplo, gramatica = titulo_libro.split(" -- ", 1)
        return ejemplo.strip(), gramatica.strip()
    return titulo_libro, titulo_libro


def merge_unidad(num, tema_map, soluciones, avisos):
    raw_path = os.path.join(RAW_DIR, f"{num}.json")
    if not os.path.exists(raw_path):
        avisos.append(f"unidad {num}: no hay {raw_path}, corre extract_ejercicios.py primero")
        return None

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    tema = tema_map.get(num, f"unidad-{num}")
    titulo, descripcion_gramatical = split_titulo(raw.get("titulo_libro", tema))

    ejercicios = []
    for ej in raw.get("ejercicios", []):
        sub = ej.get("subejercicio")
        clave = soluciones.get(sub)
        if clave is None:
            avisos.append(f"unidad {num} / {sub}: sin entrada en soluciones.json (corre extract_soluciones.py)")

        items_sol = clave["items"] if clave else []
        items_out = []
        for i, item in enumerate(ej.get("items", [])):
            texto = NUMBERING_RE.sub("", item["texto_enunciado"])
            esperados = n_huecos(texto)
            respuestas = items_sol[i] if i < len(items_sol) else None

            item_out = {"texto_enunciado": texto}
            if item.get("estimulo_visual"):
                item_out["estimulo_visual"] = item["estimulo_visual"]
            if respuestas is None:
                item_out["solucion_correcta"] = None
                item_out["revisar"] = True
                avisos.append(f"unidad {num} / {sub} / item {i + 1}: sin solucion disponible")
            elif len(respuestas) != esperados:
                item_out["solucion_correcta"] = respuestas
                item_out["revisar"] = True
                avisos.append(
                    f"unidad {num} / {sub} / item {i + 1}: {esperados} hueco(s) pero "
                    f"{len(respuestas)} solucion(es) -- revisar a mano"
                )
            else:
                item_out["solucion_correcta"] = respuestas

            items_out.append(item_out)

        ejercicio_out = {
            "subejercicio": sub,
            "tipologia": ej.get("tipologia"),
            "enunciado": ej.get("enunciado"),
            "items": items_out,
        }
        if ej.get("tipologia") == "OTRO":
            ejercicio_out["tipologia_libre"] = ej.get("tipologia_libre")
            avisos.append(
                f"unidad {num} / {sub}: tipologia no catalogada (T1-T7) -- {ej.get('tipologia_libre')!r}"
            )
        if ej.get("banco_palabras"):
            ejercicio_out["banco_palabras"] = ej["banco_palabras"]
        if ej.get("contexto_grafico"):
            ejercicio_out["contexto_grafico"] = ej["contexto_grafico"]

        ejercicios.append(ejercicio_out)

    return {
        "tema": tema,
        "titulo": titulo,
        "descripcion_gramatical": descripcion_gramatical,
        "fuente": "libro",
        "unidad_libro": int(num),
        "ejercicios": ejercicios,
    }


def main():
    tema_map = tema_por_unidad()

    soluciones = {}
    if os.path.exists(SOLUCIONES_PATH):
        with open(SOLUCIONES_PATH, encoding="utf-8") as f:
            soluciones = json.load(f)
    else:
        print("⚠️  no existe soluciones.json -- corre extract_soluciones.py antes; "
              "se continua sin respuestas (todo quedara marcado 'revisar')")

    if len(sys.argv) > 1:
        unidades = sys.argv[1:]
    else:
        unidades = sorted(
            (os.path.basename(p)[:-5] for p in glob.glob(os.path.join(RAW_DIR, "*.json"))),
            key=int,
        )

    os.makedirs(EJEMPLOS_DIR, exist_ok=True)
    avisos = []

    for num in unidades:
        resultado = merge_unidad(num, tema_map, soluciones, avisos)
        if resultado is None:
            continue
        out_path = os.path.join(EJEMPLOS_DIR, f"{resultado['tema']}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        print(f"✅ unidad {num} -> {out_path}")

    if avisos:
        print(f"\n⚠️  {len(avisos)} aviso(s) para revisar a mano:")
        for a in avisos:
            print(f"  - {a}")
    else:
        print("\n✅ sin avisos")


if __name__ == "__main__":
    main()
