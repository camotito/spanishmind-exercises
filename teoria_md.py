#!/usr/bin/env python3
"""Convierte una teoria escrita en Markdown (Obsidian, en contenido-clases/)
a content/<tema>.teoria.html. Uso: python3 teoria_md.py <fichero.md> <tema>

Quita el frontmatter y los comentarios %%...%% de Obsidian, convierte el # del
titulo en <h2> (la hoja de teoria empieza por h2) y trata los saltos de linea
simples como <br>, igual que Obsidian."""
import os
import re
import sys

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))


def convertir(md_text):
    md_text = re.sub(r"\A---\n.*?\n---\n", "", md_text, flags=re.S)
    md_text = re.sub(r"%%.*?%%", "", md_text, flags=re.S)
    html = markdown.markdown(md_text.strip(), extensions=["nl2br", "sane_lists"])
    html = re.sub(r"<h1>(.*?)</h1>", r"<h2>\1</h2>", html)
    return "\n" + html + "\n"


if __name__ == "__main__":
    md_path, tema = sys.argv[1], sys.argv[2]
    with open(md_path, encoding="utf-8") as f:
        html = convertir(f.read())
    destino = os.path.join(HERE, "content", f"{tema}.teoria.html")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK", destino)
