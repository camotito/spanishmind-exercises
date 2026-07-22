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
    export OPENAI_API_KEY="tu-key"
    python3 extract_ejercicios.py                          # todas las unidades del mapa (OpenAI por defecto)
    python3 extract_ejercicios.py 5 27 38                  # solo estas unidades
    python3 extract_ejercicios.py 38 --provider gemini      # comparar con Gemini
"""
import argparse
import json
import os

from openai_client import InsufficientQuotaError
from providers import DEFAULT_PROVIDER, build_client, call_client

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRO_DIR = os.path.join(HERE, "..", "libro")
GEMINI_DIR = os.path.join(HERE, "..", "Gemini")
MAPA_PATH = os.path.join(HERE, "mapa_unidades.json")
RAW_DIR = os.path.join(HERE, "ejercicios_raw")

# Sin JSON schema estricto aqui a proposito: "contexto_grafico.datos" cambia de
# forma segun el tipo de grafico (nombre/piso para directory, otros campos para
# family_tree/clocks/...), y un schema fijo lo aplana a strings y degrada la
# lectura (se comprobo con la unidad 27: forzar datos a array de strings hizo
# que el propio texto -- "14.º" -- se leyera mal). Confiamos en el prompt, como
# con Gemini.
PROMPT_TMPL = """Estas viendo la pagina de EJERCICIOS de una unidad de \
"Gramatica de uso del espanol" (Aragones/Palencia). Transcribe su contenido \
a JSON estructurado siguiendo EXACTAMENTE estas reglas de sintaxis:

{reglas_sintaxis}

Catalogo de tipologias (T1-T7). ESTE CATALOGO SE CREO A PARTIR DE SOLO 12 DE LAS \
126 UNIDADES DEL LIBRO (unidades 1-10, 27, 38) -- es muy posible que la unidad que \
tienes delante tenga un molde de ejercicio que NO esta descrito aqui. NO fuerces un \
bloque a la tipologia mas parecida si en realidad no encaja: usa "tipologia": "OTRO" \
y rellena "tipologia_libre" con una descripcion breve del molde real que ves (que \
elemento se presenta, que debe hacer el alumno, que apoyo visual hay). Es preferible \
"OTRO" bien descrito a un T1-T7 forzado que no representa lo que hay en la pagina.

{tipologias}

Devuelve JSON exacto, sin markdown, con esta forma:
{{
  "ejercicios": [
    {{
      "subejercicio": "5.1",
      "tipologia": "T2",
      "tipologia_libre": null,
      "enunciado": "texto del enunciado tal cual aparece (en espanol)",
      "banco_palabras": ["palabra1", "palabra2"],
      "contexto_grafico": {{"tipo": "directory", "datos": [{{"nombre": "Antonio Oliva", "piso": "2.º C"}}]}},
      "items": [
        {{"texto_enunciado": "frase con _____ o (opcion1/opcion2) segun corresponda", "estimulo_visual": null}}
      ]
    }}
  ]
}}

- "tipologia_libre" solo se rellena (con la descripcion) cuando "tipologia" es "OTRO"; \
en caso contrario, "null".
- "estimulo_visual": casi siempre "null". Rellenalo SOLO cuando el hueco de ESE item concreto \
depende de una imagen/dibujo PROPIO de ese item (no de texto ni de un grafico compartido por \
todo el bloque) -- ej. una fila numerada de dibujos donde cada numero tiene su propio hueco \
debajo y el enunciado del item esta vacio o es solo "_____.". En ese caso describe brevemente \
que muestra el dibujo de ESE item (ej. "dibujo de un tren"), para no perder la pista visual.

ADVERTENCIA IMPORTANTE sobre la forma de "items": este formato (lista de frases con huecos, una \
solucion por hueco, en el mismo orden) asume que el ejercicio es una lista lineal. NO TODOS los \
ejercicios del libro son asi. Ejemplos reales que NO encajan en esa forma:
  - Clasificar un banco de palabras en columnas de una tabla (ej. tabla "EL... / LA..." con ~30 \
palabras para repartir): no hay "items" con huecos, hay una tabla a rellenar.
  - Tabla de pares (ej. "MASCULINO / FEMENINO" con el gato -> la gata, el gallo -> ?, ? -> la vaca).
  - Enumeracion abierta a partir de un dibujo compartido (ej. "seguir describiendo los objetos \
que aparecen en el dibujo", con un numero de respuestas NO fijo de antemano).
Si el bloque tiene esta forma (o cualquier otra que no sea una lista lineal de frases con huecos), \
usa "tipologia": "OTRO" y en "tipologia_libre" describe la estructura COMPLETA con todo el detalle \
que puedas -- el banco de palabras entero, los encabezados y filas de la tabla, que celdas estan \
ya rellenas y cuales vacias, cuantas respuestas se esperan si se puede saber. Es preferible dejar \
"items" vacio o incompleto con una "tipologia_libre" fiel y completa, a forzar una lista de items \
que no representa lo que hay en la pagina -- lo importante es no perder informacion, no que la \
forma de items encaje a la fuerza.

Reglas adicionales:
- "banco_palabras" solo si hay una caja/recuadro de palabras para elegir; si no, omite el campo.
  Si el bloque tiene UN SOLO recuadro compartido por todos los items (lo mas comun), es una \
lista plana: ["palabra1", "palabra2", ...]. Si en cambio el libro imprime un recuadro \
DISTINTO para cada item/parrafo (varias cajas separadas, cada una con sus propias palabras), \
usa una lista de listas, una sublista por item EN EL MISMO ORDEN que "items": \
[["palabra1", "palabra2"], ["palabra3", "palabra4"]]. No mezcles ambas formas.
- "contexto_grafico" solo si hay un apoyo visual (dibujo, tabla, arbol, reloj...); si no, omite el campo.
  Tipos conocidos y su forma de "datos" (SIEMPRE objetos con estas claves exactas, nunca strings planas):
  - "directory": [{{"nombre": "...", "piso": "..."}}, ...]
  - "family_tree", "clocks", "visual_count", "map", "vocabulary_box", "functional_images", "instruments_visual": \
usa las claves que mejor describan lo que ves (consistentes entre todos los elementos de la lista).
  Si el grafico no encaja en ninguno de esos tipos, usa "descripcion_libre" y describe \
en "datos" (como lista de strings) lo que se ve con suficiente detalle para reconstruirlo.
- Transcribe los numeros con especial cuidado (p. ej. "14.º" no es lo mismo que "11.º"): \
si dudas entre dos cifras parecidas, mira el trazo completo del numero antes de decidir.
- NO incluyas ningun campo de solucion/respuesta: no aparece impresa en esta pagina y no debes \
inventarla.
- No proceses la pagina de TEORIA (explicaciones gramaticales) si por error ves esa en vez de la \
de ejercicios: en ese caso devuelve {{"ejercicios": []}}.
- Transcribe el numero exacto de huecos "_____" y de elecciones "(a/b)" tal como aparecen impresos.
- El primer item de un bloque de huecos suele venir ya resuelto como ejemplo modelo (la respuesta \
ya escrita e impresa, a veces subrayada). Transcribelo IGUAL que los demas, con "_____" en el \
lugar de esa respuesta (no la dejes ya escrita en el texto) -- todos los items deben quedar \
interactivos por igual. Esto NO aplica si el ejemplo modelo esta fuera de la lista de items \
(p. ej. junto al enunciado, no numerado): en ese caso no lo incluyas como item.
- NO incluyas el numero de lista del item ("1.", "2)", etc.) dentro de "texto_enunciado": \
el numero se muestra aparte automaticamente. Empieza "texto_enunciado" directamente por la \
frase (ej. "(mujer) _____", no "1. (mujer) _____").
- En "enunciado" (NO en "texto_enunciado" de los items), el libro suele imprimir en cursiva \
las palabras u opciones concretas que el alumno debe usar (ej. "Complete las frases con \
todavia, aun o ya no."). Marca CADA una de esas palabras/expresiones envolviendola en \
asteriscos: "Complete las frases con *todavia*, *aun* o *ya no*." Solo marca palabras que \
esten en cursiva en el original -- no marques nombres propios, verbos en infinitivo sueltos \
sin cursiva, ni frases enteras que no sean opciones citadas.
"""


def load_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(description="Extrae paginas de ejercicios via vision")
    parser.add_argument("unidades", nargs="*", help="numeros de unidad a procesar (default: todas las del mapa)")
    parser.add_argument("--provider", choices=["gemini", "openai"], default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=None, help="override del modelo (default: el de cada proveedor)")
    args = parser.parse_args()

    with open(MAPA_PATH, encoding="utf-8") as f:
        mapa = json.load(f)
    unidades = mapa["unidades"]

    reglas_sintaxis = load_text(os.path.join(GEMINI_DIR, "prompt.txt"))
    tipologias = load_text(os.path.join(GEMINI_DIR, "Exercises_typology.md"))
    prompt = PROMPT_TMPL.format(reglas_sintaxis=reglas_sintaxis, tipologias=tipologias)

    seleccion = args.unidades or sorted(unidades.keys(), key=int)

    os.makedirs(RAW_DIR, exist_ok=True)
    checkpoint_path = os.path.join(HERE, f".estado_ejercicios_{args.provider}.json")
    client = build_client(args.provider, checkpoint_path, model=args.model)

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

        print(f"→ unidad {num} ({info['titulo']}) -- {info['scan_ejercicios']} ({args.provider})")
        try:
            raw = call_client(client, args.provider, scan_path, prompt)
            data = json.loads(raw, strict=False)  # el modelo a veces mete saltos de linea literales en strings
        except InsufficientQuotaError as e:
            print(f"\n🛑 {e}\nParando el pipeline aqui -- relanza el mismo comando cuando haya saldo, retoma solo.")
            return
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
