#!/usr/bin/env python3
"""Avisa de gramatica que un tema publicado usa y que el alumno aun no ha visto.
Ver CLAUDE.md, "Flujo al generar o cambiar ejercicios", paso 4.

Que cuenta como visto lo fija el grafo de dependencias: `tiempos_permitidos` de
cada tema en index.yaml (formas verbales de sus depende_de y las suyas), mas la
primera ronda del curso de Javi: solo 1.ª, 2.ª, 3.ª y 6.ª persona.

Busca en los items de content/<tema>.json (texto y soluciones) y en la hoja de
teoria. Es una heuristica con regex: da CANDIDATOS, no veredictos (puede marcar
de mas, p. ej. 'se' impersonal). No cambia nada. Uso:
    python3 herramientas/check_gramatica_vista.py [tema ...]
Sale con codigo 1 si hay candidatos (para usarlo como comprobacion).
"""
import glob
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(HERE)

NOSOTROS = re.compile(r"\b(?!gramos\b|mismos\b|primos\b|ramos\b|dimos\b)\w+(?:amos|emos|imos)\b|\bnos\b", re.I)
VOSOTROS = re.compile(r"\b(?!pa[ií]s\b)\w+(?:áis|éis)\b|\bos\b", re.I)
REFLEXIVO = re.compile(r"\b(?:me|te|se|nos|os)\s+(?!usa\b)\w+", re.I)
PASADO = re.compile(r"\b(?!qu[eé]\b|caf[eé]\b|s[eé]\b|t[eé]\b|beb[eé]\b|dem[aá]s\b)\w+(?:é|ó|aron|ieron|iste)\b", re.I)


def textos(tema):
    """(origen, texto) de items (frase y solucion) y de la teoria (lineas con ejemplos en negrita)."""
    out = []
    ruta = os.path.join(RAIZ, "content", f"{tema}.json")
    d = json.load(open(ruta, encoding="utf-8"))
    for i, e in enumerate(d.get("ejercicios", []), 1):
        for it in e.get("items", []):
            t = it["texto_enunciado"] + " " + " ".join(it.get("solucion_correcta", []))
            out.append((f"ejercicio {i}", re.sub(r"_+", " ", t)))
    ruta = os.path.join(RAIZ, "content", f"{tema}.teoria.html")
    if os.path.isfile(ruta):
        html = open(ruta, encoding="utf-8").read()
        for b in re.findall(r"<(?:strong|b)>(.*?)</(?:strong|b)>", html):
            out.append(("teoria", re.sub(r"<[^>]+>", "", b)))
    return out


def main():
    indice = yaml.safe_load(open(os.path.join(RAIZ, "index.yaml"), encoding="utf-8"))
    por_tema = {t["tema"]: t for t in indice}
    pedidos = sys.argv[1:]
    temas = pedidos or sorted(
        os.path.basename(f)[:-5] for f in glob.glob(os.path.join(RAIZ, "content", "*.json"))
        if ".conjugacion" not in f)
    total = 0
    for tema in temas:
        visto = " ".join(por_tema.get(tema, {}).get("tiempos_permitidos") or [])
        reglas = [("nosotros (4.ª persona)", NOSOTROS), ("vosotros (5.ª persona)", VOSOTROS)]
        if "reflexivo" not in visto:
            reglas.append(("reflexivo", REFLEXIVO))
        if "pretérito" not in visto and "perfecto" not in visto:
            reglas.append(("pasado", PASADO))
        hallazgos = {}
        for origen, t in textos(tema):
            for nombre, rx in reglas:
                for m in rx.finditer(t):
                    hallazgos.setdefault(nombre, set()).add(f"{m.group(0)} [{origen}]")
        if hallazgos:
            total += 1
            print(f"{tema}  (visto: {visto or 'nada'})")
            for nombre, c in hallazgos.items():
                print(f"   {nombre}: {', '.join(sorted(c)[:6])}{' ...' if len(c) > 6 else ''}")
    print("Sin candidatos." if not total else f"{total} tema(s) con candidatos.")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
