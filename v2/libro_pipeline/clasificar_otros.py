#!/usr/bin/env python3
"""
Clasifica las 158 instancias "OTRO" en un catalogo formal T8-T17, a partir de
patrones estructurales leidos a mano sobre el corpus completo (otros_corpus.json).
Solo texto -- cero llamadas a la API. Imprime la asignacion para revisar antes
de aplicarla con aplicar_tipologias.py.
"""
import json

corpus = json.load(open("otros_corpus.json"))

# clave: "unidad.sub" -> nuevo codigo. Asignado a mano leyendo las 158 descripciones
# completas (no por heuristica de palabras clave, para evitar falsos positivos).
ASIGNACION = {
    # T8: completar seleccionando y adaptando (conjugar/concordar) una palabra de un banco compartido
    "13.3": "T8", "14.3": "T8", "16.1": "T8", "16.2": "T8", "21.2": "T8",
    "50.1": "T8", "50.2": "T8", "51.2": "T8", "51.3": "T8", "51.4": "T8",
    "53.2": "T8", "54.2": "T8", "56.2": "T8", "58.4": "T8", "59.2": "T8",
    "59.3": "T8", "60.3": "T8", "63.2": "T8", "63.3": "T8", "67.3": "T8",
    "68.1": "T8", "69.2": "T8", "70.3": "T8", "71.4": "T8", "75.1": "T8",
    "76.2": "T8", "82.2": "T8", "83.2": "T8", "87.3": "T8", "87.4": "T8",
    "90.2": "T8", "90.3": "T8", "90.4": "T8", "91.1": "T8", "91.2": "T8",
    "91.4": "T8", "93.3": "T8", "94.4": "T8", "97.3": "T8", "99.1": "T8",
    "99.2": "T8", "106.3": "T8", "107.1": "T8", "110.4": "T8", "112.3": "T8",
    "113.4": "T8", "114.4": "T8", "115.3": "T8", "118.1": "T8", "119.2": "T8",
    "119.4": "T8", "121.3": "T8", "122.1": "T8",
    # T9: ordenar / construir una frase a partir de palabras o segmentos dados (a veces con barras)
    "30.1": "T9", "32.1": "T9", "39.4": "T9", "42.3": "T9", "61.2": "T9",
    "68.2": "T9", "97.4": "T9", "100.3": "T9", "101.2": "T9", "112.1": "T9",
    "119.1": "T9",
    # T10: unir dos oraciones en una sola (conector/relativo dado), reescribiendo el resultado
    "28.2": "T10", "28.3": "T10", "29.1": "T10", "66.1": "T10", "79.3": "T10",
    "80.2": "T10", "81.2": "T10", "82.3": "T10", "83.3": "T10", "84.2": "T10",
    "86.1": "T10", "86.3": "T10", "93.2": "T10", "116.2": "T10", "116.3": "T10",
    "118.4": "T10", "119.3": "T10", "120.3": "T10", "121.1": "T10", "121.4": "T10",
    "122.3": "T10",
    # T11: reescribir una frase completa aplicando una transformacion indicada
    "94.2": "T11", "94.3": "T11", "103.2": "T11", "105.1": "T11", "107.3": "T11",
    "108.1": "T11", "108.2": "T11", "108.3": "T11", "125.1": "T11", "125.2": "T11",
    "125.3": "T11",
    # T12: produccion de una frase/respuesta completa a partir de una situacion o dato (sin frase base)
    "22.2": "T12", "33.3": "T12", "36.2": "T12", "36.3": "T12", "52.2": "T12",
    "52.3": "T12", "56.3": "T12", "61.4": "T12", "62.3": "T12", "72.4": "T12",
    "82.1": "T12", "83.1": "T12", "84.3": "T12", "84.4": "T12", "88.1": "T12",
    "88.3": "T12", "89.1": "T12", "89.2": "T12", "90.1": "T12", "102.2": "T12",
    "86.4": "T12", "47.2": "T12",
    # T13: emparejar/relacionar elementos de columnas o listas
    "31.1": "T13", "92.3": "T13", "110.1": "T13", "114.2": "T13", "115.1": "T13",
    "117.1": "T13", "120.1": "T13", "125.4": "T13", "61.3": "T13", "91.3": "T13",
    # T14: clasificar/repartir un banco de palabras (o datos) en categorias de una tabla
    "2.1": "T14", "2.2": "T14", "103.3": "T14",
    # T16: enumeracion abierta a partir de un dibujo o situacion compartida
    "3.2": "T15",
    # T17: marcar/anotar directamente sobre palabras dadas (acentuacion), sin "_____" independiente
    "123.1": "T16", "123.2": "T16", "123.4": "T16", "124.1a": "T16",
    "124.1b": "T16", "124.2": "T16", "124.3": "T16", "124.4": "T16",
    # sin cambios -- ya encajaban en un tipo del catalogo original, la extraccion se paso de cauta
    "8.3": "T3", "110.3": "T4",
    # revision de los 17 que faltaban (mismos criterios, opciones dadas en el enunciado
    # en vez de en un recuadro visual cuentan igualmente como T8)
    "29.3": "T8", "104.3": "T8", "109.1": "T8", "109.2": "T8", "109.3": "T8",
    "109.4": "T8", "114.3": "T8", "122.4": "T8", "33.1": "T8", "39.2": "T8",
    "73.1": "T8", "98.4": "T8",
    "30.3": "T12",
    "66.2": "T13",
    "108.4": "T10",
    "122.2": "T11",
}

DESCRIPCIONES = {
    "T8": (
        "Completar con Banco de Palabras Adaptadas",
        "Se ofrece un conjunto compartido de opciones (verbos en infinitivo, adjetivos, "
        "expresiones...) -- en un recuadro visual o enumeradas en el propio enunciado -- y el "
        "alumno debe elegir la adecuada para cada hueco y adaptarla (conjugarla, concordarla en "
        "género/número) al contexto de la frase.",
        "Entrenar la selección léxica contextual junto con la flexión morfológica correcta, "
        "sin la ambigüedad de un hueco totalmente libre ni la rigidez de un estímulo fijo por hueco.",
    ),
    "T9": (
        "Ordenar Palabras o Segmentos Dados",
        "Se presentan las palabras o segmentos de una frase desordenados (a menudo separados por "
        "barras oblicuas) y el alumno debe reescribirlos en el orden correcto, a veces completando "
        "además alguna parte de la frase.",
        "Practicar el orden sintáctico correcto de la oración en español (posición del verbo, "
        "pronombres, adjetivos...) de forma explícita.",
    ),
    "T10": (
        "Combinar Dos Oraciones en Una",
        "Se presentan dos oraciones independientes y el alumno debe unirlas en una sola oración "
        "usando el conector, relativo o estructura gramatical indicada (en el enunciado o entre "
        "paréntesis), realizando los cambios sintácticos necesarios.",
        "Practicar la subordinación y coordinación de oraciones, y el manejo de nexos "
        "(relativos, causales, concesivos, consecutivos...) en producción libre.",
    ),
    "T11": (
        "Reescribir una Oración Transformada",
        "Se da una oración completa y el alumno debe reescribirla entera aplicando una "
        "transformación indicada: cambiar a forma negativa, insertar una expresión en un punto "
        "marcado, corregir un error, adaptar mayúsculas...",
        "Practicar una transformación gramatical u ortográfica concreta sobre una oración ya "
        "construida, reforzando la reestructuración completa en vez de un hueco puntual.",
    ),
    "T12": (
        "Producción Libre desde una Situación",
        "A partir de una situación, dato o pregunta (sin una oración base que transformar o "
        "combinar), el alumno redacta una frase o respuesta nueva -- una pregunta, una respuesta "
        "de diálogo, una transformación a estilo indirecto, un deseo, una queja...",
        "Practicar la producción espontánea guiada, más abierta que T10/T11 porque no parte de "
        "una oración ya escrita que transformar, sino de un contexto o dato.",
    ),
    "T13": (
        "Emparejamiento en Columnas",
        "Dos (o tres) columnas de elementos -- inicios y finales de frase, preguntas y "
        "respuestas, siglas y nombres -- que el alumno debe relacionar correctamente, a veces "
        "escribiendo después la oración completa resultante.",
        "Practicar el reconocimiento de qué elementos combinan correctamente (léxica o "
        "gramaticalmente) antes o en vez de producir la oración desde cero.",
    ),
    "T14": (
        "Clasificación en Tabla",
        "Un banco de palabras o datos debe repartirse en las categorías de una tabla (columnas "
        "con encabezado, pares correspondientes, o una escala ordenada), en vez de rellenar "
        "huecos en frases.",
        "Practicar la categorización gramatical (género, mayor/menor frecuencia...) de forma "
        "visual y agrupada.",
    ),
    "T15": (
        "Enumeración Abierta desde un Gráfico",
        "A partir de un dibujo o situación compartida, el alumno continúa una enumeración con "
        "un número de respuestas no fijado de antemano (cuenta y nombra lo que observa).",
        "Practicar vocabulario y estructuras de cantidad/enumeración en un contexto "
        "abierto, no acotado a un número fijo de huecos.",
    ),
    "T16": (
        "Anotación Directa sobre la Palabra",
        "El alumno marca o modifica directamente las palabras ya impresas (subrayar la sílaba "
        "tónica, añadir una tilde, dividir en sílabas), sin un hueco '_____' independiente.",
        "Practicar reglas de acentuación y silabeo trabajando sobre la propia palabra, no sobre "
        "una frase con hueco.",
    ),
}


def main():
    by_sub = {f"{o['unidad']}.{o['sub'].split('.', 1)[1]}" if False else o["sub"]: o for o in corpus}
    # nota: la clave real del corpus es "sub" (ej. "13.3"), que ya es unica en todo el libro
    faltan = [o["sub"] for o in corpus if o["sub"] not in ASIGNACION]
    if faltan:
        print(f"⚠️  {len(faltan)} instancia(s) sin asignar todavia:", faltan)
    else:
        print("✅ las 158 instancias tienen asignacion")

    from collections import Counter
    conteo = Counter(ASIGNACION.values())
    for tipo, n in sorted(conteo.items()):
        nombre = DESCRIPCIONES.get(tipo, ("(revertido a catalogo original)",))[0]
        print(f"  {tipo}: {n:3d}  -- {nombre}")

    json.dump(ASIGNACION, open("asignacion_tipologias.json", "w"), ensure_ascii=False, indent=2, sort_keys=True)
    json.dump(DESCRIPCIONES, open("descripciones_tipologias.json", "w"), ensure_ascii=False, indent=2)
    print("\n✅ escrito asignacion_tipologias.json y descripciones_tipologias.json")


if __name__ == "__main__":
    main()
