#!/usr/bin/env python3
"""Calcula `tiempos_permitidos` en index.yaml recorriendo el GRAFO de
`depende_de` (sustituye al viejo compute_tenses.py de v1, que recorria una
lista lineal -- v2 cambio de lista a grafo).

Para cada tema: orden topologico de depende_de, y tiempos_permitidos = union
de su propio `forma_verbal` + el de TODOS sus ancestros transitivos (en
orden de aparicion), con fallback a ["presente de indicativo"] si no hay
ninguno -- misma logica que v1, adaptada a grafo en vez de lista.

Reescribe index.yaml con el mismo parcheo quirurgico de texto que
sync_ejercicios_permitidos.py (una linea por tema, no rompe formato/comentarios).

Uso:
    python3 compute_tiempos_permitidos.py           # aplica los cambios
    python3 compute_tiempos_permitidos.py --check   # solo informa, no escribe
"""
import argparse
import os
import re

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
V2_DIR = os.path.join(HERE, "..")
INDEX_PATH = os.path.join(V2_DIR, "index.yaml")


def orden_topologico(indice):
    por_tema = {t["tema"]: t for t in indice}
    visitado = {}
    orden = []

    def visitar(tema, pila):
        if visitado.get(tema) == "hecho":
            return
        if visitado.get(tema) == "en_curso":
            raise SystemExit(f"ciclo en depende_de: {' -> '.join(pila + [tema])}")
        visitado[tema] = "en_curso"
        for dep in por_tema[tema].get("depende_de") or []:
            if dep not in por_tema:
                raise SystemExit(f"tema '{tema}' depende de '{dep}', que no existe en index.yaml")
            visitar(dep, pila + [tema])
        visitado[tema] = "hecho"
        orden.append(tema)

    for t in indice:
        visitar(t["tema"], [])
    return orden


def compute(indice):
    por_tema = {t["tema"]: t for t in indice}
    orden = orden_topologico(indice)

    acumulado = {}  # tema -> lista ordenada de formas verbales vistas hasta (e incluyendo) el
    for tema in orden:
        t = por_tema[tema]
        vistos = []
        for dep in t.get("depende_de") or []:
            for f in acumulado[dep]:
                if f not in vistos:
                    vistos.append(f)
        fv = t.get("forma_verbal")
        if fv and fv not in vistos:
            vistos.append(fv)
        acumulado[tema] = vistos

    cambios = []
    for t in indice:
        nuevo = acumulado[t["tema"]] or ["presente de indicativo"]
        if nuevo != t.get("tiempos_permitidos"):
            cambios.append((t["tema"], t.get("tiempos_permitidos"), nuevo))
    return cambios


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="solo informa, no escribe")
    args = parser.parse_args()

    with open(INDEX_PATH, encoding="utf-8") as f:
        raw = f.read()
    indice = yaml.safe_load(raw)

    cambios = compute(indice)

    if not cambios:
        print("✅ tiempos_permitidos ya esta sincronizado con el grafo depende_de/forma_verbal.")
        return

    print(f"{'Cambios detectados' if args.check else 'Aplicando cambios'} ({len(cambios)} tema(s)):")
    for tema, antes, despues in cambios:
        print(f"  {tema}: {antes} -> {despues}")

    if args.check:
        return

    lines = raw.splitlines(keepends=True)
    cambios_por_tema = {tema: despues for tema, _, despues in cambios}
    tema_actual = None
    TEMA_RE = re.compile(r"^- tema:\s*(\S+)")
    TIEMPOS_RE = re.compile(r"^(\s*tiempos_permitidos:\s*)\[.*\]\s*$")
    for i, line in enumerate(lines):
        m_tema = TEMA_RE.match(line)
        if m_tema:
            tema_actual = m_tema.group(1)
            continue
        m_tiempos = TIEMPOS_RE.match(line)
        if m_tiempos and tema_actual in cambios_por_tema:
            valores = ", ".join(f'"{v}"' for v in cambios_por_tema[tema_actual])
            lines[i] = f"{m_tiempos.group(1)}[{valores}]\n"
            del cambios_por_tema[tema_actual]

    if cambios_por_tema:
        raise SystemExit(f"no se encontro la linea tiempos_permitidos para: {list(cambios_por_tema)}")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"✅ {INDEX_PATH} actualizado.")


if __name__ == "__main__":
    main()
