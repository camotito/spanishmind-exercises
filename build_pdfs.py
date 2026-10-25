#!/usr/bin/env python3
"""Genera out/pdf/<tema>-conjugacion.pdf para cada tema con tablas de conjugacion.

Usa Chrome sin ventana sobre out/<tema>.html con el panel abierto (el CSS de
impresion de render.py deja solo las tablas). Hay que correrlo en local tras
render.py y commitear los PDF: el build de Netlify no tiene Chrome.
"""
import glob
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
ABIERTO = '<dialog id="conj" class="teoria conj">'


def main():
    os.makedirs(os.path.join(OUT, "pdf"), exist_ok=True)
    for ruta in sorted(glob.glob(os.path.join(HERE, "content", "*.conjugacion.json"))):
        tema = os.path.basename(ruta)[: -len(".conjugacion.json")]
        with open(os.path.join(OUT, f"{tema}.html"), encoding="utf-8") as f:
            html = f.read().replace(ABIERTO, ABIERTO[:-1] + " open>")
        destino = os.path.join(OUT, "pdf", f"{tema}-conjugacion.pdf")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_html = os.path.join(tmp, "p.html")
            with open(tmp_html, "w", encoding="utf-8") as f:
                f.write(html)
            subprocess.run(
                ["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu",
                 "--no-pdf-header-footer", f"--print-to-pdf={destino}", f"file://{tmp_html}"],
                check=True, capture_output=True)
        print(f"✅ {destino}")


if __name__ == "__main__":
    main()
