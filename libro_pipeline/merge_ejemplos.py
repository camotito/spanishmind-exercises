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
    python3 merge_ejemplos.py --libro c1-c2   # otro libro (libros/c1-c2/)
"""
import glob
import json
import os
import re
import sys

import yaml

from libro_ctx import Libro, LEGACY

# se rellenan en main() segun --libro (default: el libro original)
RAW_DIR = SOLUCIONES_PATH = INDEX_PATH = EJEMPLOS_DIR = None

# mismos patrones que el tokenizador de render.py -- deben mantenerse en sync
CHOICE_RE = re.compile(r"\(([^()]*?/[^()]*?)\)")
BLANK = "_____"

# algunas extracciones (sobre todo de antes de que el prompt lo prohibiera
# explicitamente) incluyen el numero de lista del item dentro del propio texto
# (ej. "1. (mujer) _____"); render.py ya numera cada item por su cuenta, asi
# que aqui se quita para no duplicarlo -- barato (regex) y cubre tanto lo ya
# extraido como lo nuevo, sin tener que volver a pagar la extraccion.
NUMBERING_RE = re.compile(r"^\s*\d{1,3}[.\)]\s+")


# subejercicios donde "(a/b)" es un estimulo (palabras dadas), no una lista de opciones
SUBS_PARENTESIS_ESTIMULO = {"7.2", "22.5", "40.3", "102.4", "103.4", "105.3"}


def n_huecos(texto, sub=None):
    if sub in SUBS_PARENTESIS_ESTIMULO:
        return texto.count(BLANK)
    return len(CHOICE_RE.findall(texto)) + texto.count(BLANK)


TOKEN_RE = re.compile(r"\(([^()]*?/[^()]*?)\)|_____")


def dividir_opcion_hueco(texto, respuestas):
    """Caso "(el/la) _____" -> el libro da una sola respuesta "la jarra" pero el
    ejercicio tiene un desplegable y un hueco seguidos (2 slots). Parte la
    respuesta en ["la", "jarra"] cuando empieza por una de las opciones.
    Devuelve la lista nueva, o None si no se puede dividir con seguridad."""
    tokens = list(TOKEN_RE.finditer(texto))
    out, r = [], list(respuestas)
    i = 0
    while i < len(tokens):
        t = tokens[i]
        es_opcion = t.group(1) is not None
        sigue_hueco = (
            es_opcion and i + 1 < len(tokens) and tokens[i + 1].group(1) is None
            and texto[t.end():tokens[i + 1].start()].strip() == ""
        )
        if not r:
            return None
        if sigue_hueco and len(r) < len(tokens) - i:
            ops = [o.strip() for o in t.group(1).split("/")]
            ans = r[0]
            for o in ops:
                if ans.lower().startswith(o.lower() + " ") and len(ans) > len(o) + 1:
                    out += [ans[:len(o)], ans[len(o) + 1:].strip()]
                    break
            else:
                return None
            r.pop(0)
            i += 2
        else:
            out.append(r.pop(0))
            i += 1
    return out if not r and len(out) == len(tokens) else None


def tema_por_unidad():
    if not INDEX_PATH:  # libros nuevos: no hay index.yaml, los temas son unidad-N
        return {}
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
            esperados = n_huecos(texto, sub)
            respuestas = items_sol[i] if i < len(items_sol) else None

            item_out = {"texto_enunciado": texto}
            if item.get("estimulo_visual"):
                item_out["estimulo_visual"] = item["estimulo_visual"]
            if respuestas is None:
                item_out["solucion_correcta"] = None
                item_out["revisar"] = True
                avisos.append(f"unidad {num} / {sub} / item {i + 1}: sin solucion disponible")
            elif len(respuestas) != esperados and len(respuestas) < esperados and (
                dividir_opcion_hueco(texto, respuestas) is not None
            ):
                item_out["solucion_correcta"] = dividir_opcion_hueco(texto, respuestas)
            elif len(respuestas) == 1 and esperados >= 2 and len(respuestas[0].split()) >= 2 * esperados:
                # el libro da la frase entera (ordenar/reescribir/construir): no es un
                # fallo de extraccion, la respuesta no se reparte por hueco
                item_out["solucion_correcta"] = respuestas
                item_out["respuesta_frase_completa"] = True
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
    global RAW_DIR, SOLUCIONES_PATH, INDEX_PATH, EJEMPLOS_DIR
    args = sys.argv[1:]
    nombre = LEGACY
    if "--libro" in args:
        i = args.index("--libro")
        nombre = args[i + 1]
        del args[i:i + 2]
    libro = Libro(nombre)
    RAW_DIR = libro.raw_dir
    SOLUCIONES_PATH = libro.soluciones_final_path()
    INDEX_PATH = libro.index_path
    EJEMPLOS_DIR = libro.ejemplos_dir

    tema_map = tema_por_unidad()

    soluciones = {}
    if os.path.exists(SOLUCIONES_PATH):
        with open(SOLUCIONES_PATH, encoding="utf-8") as f:
            soluciones = json.load(f)
    else:
        print("⚠️  no existe soluciones.json -- corre extract_soluciones.py antes; "
              "se continua sin respuestas (todo quedara marcado 'revisar')")

    if args:
        unidades = args
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
