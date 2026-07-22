#!/usr/bin/env python3
"""Deriva `ejercicios_permitidos` en index.yaml a partir de las tipologias
REALES encontradas en ejemplos/<tema>.json, para cada tema con unidad_libro.

Por que no usa yaml.safe_dump para reescribir todo el fichero: pyyaml no
conserva comentarios ni el formato a mano de index.yaml (los aplanaria).
En vez de eso, parsea con pyyaml SOLO para calcular los valores nuevos, y
aplica el cambio como un reemplazo de texto quirurgico (una linea por tema),
dejando todo lo demas del fichero exactamente igual.

Uso:
    python3 sync_ejercicios_permitidos.py           # aplica los cambios
    python3 sync_ejercicios_permitidos.py --check   # solo informa, no escribe (para CI/hooks)
"""
import argparse
import json
import os
import re

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
V2_DIR = os.path.join(HERE, "..")
INDEX_PATH = os.path.join(V2_DIR, "index.yaml")
EJEMPLOS_DIR = os.path.join(V2_DIR, "ejemplos")


def tipos_reales(tema):
    path = os.path.join(EJEMPLOS_DIR, f"{tema}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    tipos = []
    for ej in data["ejercicios"]:
        tp = ej.get("tipologia")
        if tp and tp not in tipos:
            tipos.append(tp)
    return tipos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="solo informa, no escribe")
    args = parser.parse_args()

    with open(INDEX_PATH, encoding="utf-8") as f:
        raw = f.read()
    indice = yaml.safe_load(raw)

    cambios = []
    for t in indice:
        tema = t["tema"]
        if not t.get("unidad_libro"):
            continue
        tipos = tipos_reales(tema)
        if tipos is None:
            print(f"⚠️  {tema}: no existe ejemplos/{tema}.json, se salta")
            continue
        if tipos != t.get("ejercicios_permitidos"):
            cambios.append((tema, t.get("ejercicios_permitidos"), tipos))

    if not cambios:
        print("✅ ejercicios_permitidos ya esta sincronizado con ejemplos/ para todas las unidades con unidad_libro.")
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
    PERM_RE = re.compile(r"^(\s*ejercicios_permitidos:\s*)\[.*\]\s*$")
    for i, line in enumerate(lines):
        m_tema = TEMA_RE.match(line)
        if m_tema:
            tema_actual = m_tema.group(1)
            continue
        m_perm = PERM_RE.match(line)
        if m_perm and tema_actual in cambios_por_tema:
            nuevo_valor = ", ".join(cambios_por_tema[tema_actual])
            lines[i] = f"{m_perm.group(1)}[{nuevo_valor}]\n"
            del cambios_por_tema[tema_actual]

    if cambios_por_tema:
        raise SystemExit(f"no se encontro la linea ejercicios_permitidos para: {list(cambios_por_tema)}")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"✅ {INDEX_PATH} actualizado.")


if __name__ == "__main__":
    main()
