#!/usr/bin/env python3
"""
Paso 0 (solo para libros que llegan como PDF de imagenes): renderiza cada
pagina a libros/<libro>/img/p-NNN.jpg (NNN = pagina del PDF, base 1).
Reanudable: salta las paginas que ya existen.

Uso:
    python3 render_pdf.py --libro c1-c2 [--dpi 200]
"""
import argparse
import os
import subprocess

from libro_ctx import Libro, add_libro_arg


def main():
    parser = argparse.ArgumentParser(description="Renderiza un PDF escaneado a imagenes por pagina")
    add_libro_arg(parser)
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()

    libro = Libro(args.libro)
    if libro.legacy:
        raise SystemExit("a1-b2 ya tiene sus scans en libro/; render_pdf.py es para libros nuevos")
    pdf = libro.config["pdf"]
    os.makedirs(libro.scans_dir, exist_ok=True)

    info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True, check=True).stdout
    n_paginas = int(next(l.split()[1] for l in info.splitlines() if l.startswith("Pages:")))
    existentes = set(libro.available_scan_indices())

    hechas = 0
    for p in range(1, n_paginas + 1):
        if p in existentes:
            continue
        destino = libro.scan_path(p)
        prefijo = destino[: -len(".jpg")]
        subprocess.run(
            ["pdftoppm", "-f", str(p), "-l", str(p), "-r", str(args.dpi), "-jpeg", "-jpegopt", "quality=90",
             "-singlefile", pdf, prefijo],
            check=True,
        )
        hechas += 1
    print(f"✅ {hechas} pagina(s) renderizadas, {n_paginas} en total, en {libro.scans_dir}")


if __name__ == "__main__":
    main()
