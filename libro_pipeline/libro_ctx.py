#!/usr/bin/env python3
"""
Contexto por libro del pipeline de digitalizacion: de donde salen los scans,
donde se escriben los datos intermedios y el offset de paginacion.

Dos modos:
- sin --libro (o "a1-b2"): el libro original, con el layout historico
  (libro/libro-rojo-NNN.png, datos en libro_pipeline/, salida en ejemplos/).
- --libro <nombre> (ej. "c1-c2"): todo bajo libros/<nombre>/, con su propia
  config en libros/<nombre>/libro.json. Nunca toca ejemplos/, content/ ni
  index.yaml del libro original (las unidades se solaparian: la unidad 1 existe
  en los dos).

libros/<nombre>/libro.json:
    {"pdf": "/ruta/al/libro.pdf", "offset": -1, "titulo": "..."}
  offset = scan_index - pagina_impresa (en a1-b2 es +1; en c1-c2 es -1).
  "cambios_offset": [[pagina_impresa_desde, offset], ...] opcional: tramos donde
  el offset cambia porque al PDF le faltan paginas (ej. c1-c2: falta la pagina
  impresa 76, asi que desde la 77 el offset es -2).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
LEGACY = "a1-b2"


class Libro:
    def __init__(self, nombre=None):
        self.nombre = nombre or LEGACY
        self.legacy = self.nombre == LEGACY

        if self.legacy:
            self.base = HERE
            self.scans_dir = os.path.join(REPO, "libro")
            self._scan_fmt = "libro-rojo-{:03d}.png"
            self.scan_re = re.compile(r"^libro-rojo-(\d{3})\.png$")
            self.ejemplos_dir = os.path.join(REPO, "ejemplos")
            self.index_path = os.path.join(REPO, "index.yaml")
            self.offset = 1
            self.cambios_offset = []
            self.config = {}
        else:
            self.base = os.path.join(REPO, "libros", self.nombre)
            cfg_path = os.path.join(self.base, "libro.json")
            if not os.path.exists(cfg_path):
                raise SystemExit(f"No existe {cfg_path} (crea libros/{self.nombre}/libro.json con pdf y offset)")
            with open(cfg_path, encoding="utf-8") as f:
                self.config = json.load(f)
            self.scans_dir = os.path.join(self.base, "img")
            self._scan_fmt = "p-{:03d}.jpg"
            self.scan_re = re.compile(r"^p-(\d{3})\.jpg$")
            self.ejemplos_dir = os.path.join(self.base, "ejemplos")
            self.index_path = None
            self.offset = int(self.config["offset"])
            self.cambios_offset = sorted((int(d), int(o)) for d, o in self.config.get("cambios_offset", []))

        self.mapa_path = os.path.join(self.base, "mapa_unidades.json")
        self.raw_dir = os.path.join(self.base, "ejercicios_raw")

    def scan_for_page(self, pagina_impresa):
        """Indice de scan de una pagina impresa, teniendo en cuenta los tramos
        de offset (paginas que faltan en el PDF)."""
        off = self.offset
        for desde, o in self.cambios_offset:
            if pagina_impresa >= desde:
                off = o
        return pagina_impresa + off

    def scan_name(self, scan_index):
        return self._scan_fmt.format(scan_index)

    def scan_path(self, scan_index):
        return os.path.join(self.scans_dir, self.scan_name(scan_index))

    def available_scan_indices(self):
        indices = []
        if os.path.isdir(self.scans_dir):
            for name in os.listdir(self.scans_dir):
                m = self.scan_re.match(name)
                if m:
                    indices.append(int(m.group(1)))
        return sorted(indices)

    def estado(self, nombre):
        return os.path.join(self.base, f".estado_{nombre}.json")

    def soluciones_path(self, provider):
        return os.path.join(self.base, f"soluciones_{provider}.json")

    def soluciones_final_path(self):
        """soluciones.json si existe (legacy, ya cruzado entre proveedores);
        si no, el de OpenAI (default del pipeline)."""
        final = os.path.join(self.base, "soluciones.json")
        if os.path.exists(final):
            return final
        return self.soluciones_path("openai")


def add_libro_arg(parser):
    parser.add_argument(
        "--libro",
        default=LEGACY,
        help=f"libro a procesar (default: {LEGACY}, el original). Ej.: c1-c2 -> libros/c1-c2/",
    )


def find_solucionario(secciones):
    """Devuelve (nombre, info) de la seccion de soluciones, sea cual sea su
    titulo exacto ('Soluciones a los ejercicios', 'Solucionario'...)."""
    for nombre, info in secciones.items():
        if re.search(r"(?i)soluci", nombre):
            return nombre, info
    return None, None
