#!/usr/bin/env python3
"""Regenera libros/<libro>/indice.md desde ejemplos/, mapa_unidades.json,
disputas_soluciones.json y teoria.json (resumen de la teoría, solo algunas unidades).

Uso: python3 libro_pipeline/build_indice.py [c1-c2]
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRO = sys.argv[1] if len(sys.argv) > 1 else "c1-c2"
D = os.path.join(HERE, "..", "libros", LIBRO)

NO_AUTO_TIPO = {
    "T2": "apoyo gráfico, la web no lo muestra",
    "T6": "producción libre",
    "T12": "producción libre",
    "T13": "emparejar, sin soporte en la web",
    "T14": "sin soporte en la web",
    "T15": "sin soporte en la web",
    "T16": "sin soporte en la web",
    "T17": "tipo sin clasificar",
    "OTRO": "tipo sin clasificar",
}
PALABRAS_FRASE = 4  # solución de 4 o más palabras = frase


def alt_en_frase(sol):
    """True si algún elemento multipalabra lleva alternativas ('/') u opcionales '(...)'."""
    for x in sol:
        if isinstance(x, list):
            return True
        if not isinstance(x, str) or len(x.split()) < 2:
            continue
        if "/" in x or re.search(r"\([^)]*\)", x):
            return True
    return False


def auto(ej):
    items = ej["items"]
    if ej["tipologia"] in NO_AUTO_TIPO:
        return "no", NO_AUTO_TIPO[ej["tipologia"]], []
    if any(not it.get("solucion_correcta") for it in items):
        return "no", "faltan soluciones", []
    alt = [i for i, it in enumerate(items, 1) if alt_en_frase(it["solucion_correcta"])]
    if alt:
        return "no", "alternativas dentro de una frase", alt
    if any(len(x.split()) >= PALABRAS_FRASE for it in items
           for x in it["solucion_correcta"] if isinstance(x, str)):
        return "no", "respuesta de frase completa", []
    return "sí", "", []


def main():
    mapa = json.load(open(os.path.join(D, "mapa_unidades.json")))["unidades"]
    disp = {}
    p = os.path.join(D, "disputas_soluciones.json")
    if os.path.exists(p):
        for x in json.load(open(p)):
            disp.setdefault(x["sub"], []).append(x["item"])
    teoria = {}
    p = os.path.join(D, "teoria.json")
    if os.path.exists(p):
        teoria = json.load(open(p))

    unidades = {}
    for f in glob.glob(os.path.join(D, "ejemplos", "unidad-*.json")):
        u = json.load(open(f))
        unidades[int(u["unidad_libro"])] = u

    n_ej = sum(len(u["ejercicios"]) for u in unidades.values())
    n_it = sum(len(e["items"]) for u in unidades.values() for e in u["ejercicios"])
    n_auto = sum(auto(e)[0] == "sí" for u in unidades.values() for e in u["ejercicios"])
    n_disp = sum(len(v) for v in disp.values())

    out = []
    out.append("# Gramática de uso del español C1-C2 (SM): índice de unidades y ejercicios\n")
    out.append(f"Fuente: libro escaneado, {len(unidades)} unidades, cada una con teoría y ejercicios (solucionario incluido en los datos).")
    out.append(f"Total: {n_ej} ejercicios, {n_it} ítems.")
    out.append("Cada ejercicio indica: número, tipo, nº de ítems, consigna, si la web lo corrige sola y disputas.")
    out.append("Datos completos con soluciones: `libros/c1-c2/ejemplos/unidad-N.json`.\n")
    out.append("Corrección automática (`auto`):")
    out.append("- `auto: sí`: huecos, elecciones o formas cortas; la web compara con la solución sin tildes ni mayúsculas.")
    out.append("- `auto: no (motivo)`: la web no puede garantizar la corrección.")
    out.append(f"- Motivos: tipo sin soporte o de producción libre, faltan soluciones, respuesta de frase completa ({PALABRAS_FRASE} o más palabras) o alternativas dentro de una frase.")
    out.append("- `alternativas en frase: ítems N`: esos ítems tienen variantes dentro de la frase (con `/` o paréntesis); la web no las acepta todas.")
    out.append(f"- Resultado: {n_auto} de {n_ej} ejercicios con `auto: sí`.\n")
    out.append(f"Disputas de solución: `disputa: ítems N` marca los ítems donde Gemini Flash y Gemini Pro dieron soluciones distintas ({n_disp} en total, detalle en `disputas_soluciones.json`). La solución del JSON es la de Pro; revisar contra el libro antes de usarla.\n")
    out.append("Teoría: cada unidad tiene teoría en el libro (página indicada en `libro p. N`). El resumen de la regla solo está escrito para las unidades 57 a 70 y 106 (`teoria.json`).\n")
    out.append("Tipos: T1 clasificar en tablas; T2 completar con apoyo gráfico; T3 completar huecos (gramática libre); T4 transformación morfológica; T5 elección múltiple en la frase; T6 producción escrita pautada; T7 sustitución/reescritura; T8 completar con banco de palabras; T9 ordenar palabras; T10 combinar dos oraciones; T11 reescribir oración; T12 producción libre; T13 emparejar columnas; T14 clasificar en tabla; T15 enumeración desde gráfico; T16 anotación sobre la palabra; T17 otro\n")

    for n in sorted(unidades):
        u = unidades[n]
        m = mapa[str(n)]
        titulo, _, tema = m["titulo"].partition(" -- ")
        out.append(f"## {n}. {titulo}")
        out.append(f"Tema: {tema} · libro p. {m['pagina']} · {len(u['ejercicios'])} ejercicios")
        if str(n) in teoria:
            out.append("Teoría del libro:")
            out += [f"- {l}" for l in teoria[str(n)]]
            out.append("Ejercicios:")
        for e in u["ejercicios"]:
            tipo = e["tipologia"]
            enun = re.sub(r"\s*>\s*APÉNDICE.*$", "", e["enunciado"].replace("*", ""))
            a, motivo, alt = auto(e)
            extra = f" | auto: {a}" + (f" ({motivo})" if motivo else "")
            if alt:
                extra += " | alternativas en frase: ítems " + ", ".join(map(str, alt))
            if e["subejercicio"] in disp:
                extra += " | disputa: ítems " + ", ".join(
                    "(varios)" if i is None else str(i) for i in disp[e["subejercicio"]])
            out.append(f"- {e['subejercicio']} [{tipo}] {len(e['items'])} ítems: {enun}{extra}")
        out.append("")
    open(os.path.join(D, "indice.md"), "w").write("\n".join(out))
    print(f"indice.md: {len(unidades)} unidades, {n_ej} ejercicios, {n_it} ítems, auto sí {n_auto}, disputas {n_disp}")


main()
