#!/usr/bin/env python3
"""Servidor local del dashboard de contenido (solo localhost, sin dependencias
externas -- http.server de la stdlib). Permite:
  - listar/editar las oraciones (texto_enunciado) de los items de content/<tema>.json
  - ocultar/mostrar un bloque de ejercicios sin borrarlo (campo "oculto")
  - re-renderizar out/<tema>.html automaticamente al guardar
  - lanzar la sincronizacion de ejercicios_permitidos (index.yaml) en un click
  - servir libro_pipeline/indice_unidades.html embebido (indice buscable del libro)

Uso:
    python3 dashboard/server.py           # arranca en http://127.0.0.1:8765
    python3 dashboard/server.py --port 9000

Nunca expone el server fuera de localhost (bind explicito a 127.0.0.1) --
es una herramienta personal de edicion, no parte del sitio servido.
"""
import argparse
import json
import mimetypes
import os
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(HERE)
CONTENT_DIR = os.path.join(ROOT_DIR, "content")
OUT_DIR = os.path.join(ROOT_DIR, "out")
INDEX_YAML = os.path.join(ROOT_DIR, "index.yaml")
TYPOLOGY_MD = os.path.join(ROOT_DIR, "Gemini", "Exercises_typology.md")
RENDER_CONFIG_PATH = os.path.join(ROOT_DIR, "render_config.json")

sys.path.insert(0, ROOT_DIR)
import render  # noqa: E402  (necesita el sys.path.insert de arriba)

sys.path.insert(0, os.path.join(ROOT_DIR, "libro_pipeline"))
import sync_ejercicios_permitidos as sync_perm  # noqa: E402

import yaml  # noqa: E402


def cargar_titulos():
    if not os.path.exists(INDEX_YAML):
        return {}
    with open(INDEX_YAML, encoding="utf-8") as f:
        indice = yaml.safe_load(f) or []
    return {
        t["tema"]: {"titulo": t.get("titulo", t["tema"]), "unidad_libro": t.get("unidad_libro")}
        for t in indice
    }


def listar_temas():
    info_yaml = cargar_titulos()
    temas = []
    for fn in sorted(os.listdir(CONTENT_DIR)):
        if not fn.endswith(".json"):
            continue
        tema = fn[:-5]
        with open(os.path.join(CONTENT_DIR, fn), encoding="utf-8") as f:
            data = json.load(f)
        n_ejercicios = len(data.get("ejercicios", []))
        n_ocultos = sum(1 for ej in data.get("ejercicios", []) if ej.get("oculto"))
        tipologias = sorted({ej.get("tipologia") for ej in data.get("ejercicios", []) if ej.get("tipologia")})
        info = info_yaml.get(tema, {})
        temas.append({
            "tema": tema,
            "titulo": info.get("titulo", data.get("titulo", tema)),
            "unidad_libro": info.get("unidad_libro"),
            "n_ejercicios": n_ejercicios,
            "n_ocultos": n_ocultos,
            "tipologias": tipologias,
        })
    return temas


TIPOLOGIA_RE = re.compile(
    r"## `\[(T\d+)\]` (.+?)\n"
    r"\* \*\*Descripción:\*\* (.+?)\n"
    r"\* \*\*Propósito:\*\* (.+?)(?=\n\n|\n##|\Z)",
    re.S,
)


def listar_tipologias():
    """Parsea Gemini/Exercises_typology.md (fuente unica de verdad, sin
    duplicar el contenido en un JSON aparte) a una lista de dicts."""
    if not os.path.exists(TYPOLOGY_MD):
        return []
    with open(TYPOLOGY_MD, encoding="utf-8") as f:
        texto = f.read()
    tipologias = []
    for m in TIPOLOGIA_RE.finditer(texto):
        codigo, nombre, descripcion, proposito = m.groups()
        tipologias.append({
            "codigo": codigo,
            "nombre": nombre.strip(),
            "descripcion": " ".join(descripcion.split()),
            "proposito": " ".join(proposito.split()),
        })
    tipologias.sort(key=lambda t: int(t["codigo"][1:]))
    return tipologias


def cargar_render_config():
    if not os.path.exists(RENDER_CONFIG_PATH):
        return {"tipologias_desactivadas": []}
    with open(RENDER_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def guardar_render_config(config):
    with open(RENDER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[dashboard] " + (fmt % args) + "\n")

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, rel_path):
        # rel_path ya viene relativo a ROOT_DIR; evita path traversal fuera del repo.
        full = os.path.normpath(os.path.join(ROOT_DIR, rel_path))
        if not full.startswith(ROOT_DIR) or not os.path.isfile(full):
            self.send_error(404, "not found")
            return
        ctype, _ = mimetypes.guess_type(full)
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)

        if path == "/" or path == "":
            self._static("dashboard/index.html")
        elif path == "/api/temas":
            self._json(listar_temas())
        elif path == "/api/tipologias":
            self._json({
                "tipologias": listar_tipologias(),
                "desactivadas": cargar_render_config().get("tipologias_desactivadas", []),
            })
        elif path.startswith("/api/content/"):
            tema = path[len("/api/content/"):]
            fpath = os.path.join(CONTENT_DIR, f"{tema}.json")
            if not os.path.isfile(fpath):
                self._json({"error": f"no existe {tema}"}, status=404)
                return
            with open(fpath, encoding="utf-8") as f:
                self._json(json.load(f))
        elif path.startswith("/libro_pipeline/") or path.startswith("/out/") or path.startswith("/dashboard/"):
            self._static(path.lstrip("/"))
        else:
            self.send_error(404, "not found")

    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""

        if path.startswith("/api/content/"):
            tema = path[len("/api/content/"):]
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                self._json({"ok": False, "error": f"JSON invalido: {e}"}, status=400)
                return
            if data.get("tema") != tema:
                self._json({"ok": False, "error": "el campo 'tema' del JSON no coincide con la URL"}, status=400)
                return
            try:
                # valida ANTES de escribir: si algo quedo mal (huecos != soluciones
                # tras editar una frase), build_html lanza ValueError y no se guarda nada.
                render.build_html(data)
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, status=400)
                return
            fpath = os.path.join(CONTENT_DIR, f"{tema}.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
            try:
                render.generate(tema)
            except Exception as e:
                self._json({"ok": True, "warning": f"guardado, pero fallo al re-renderizar: {e}"})
                return
            self._json({"ok": True})

        elif path == "/api/tipologias-config":
            try:
                body = json.loads(raw)
                desactivadas = sorted(set(body["tipologias_desactivadas"]))
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self._json({"ok": False, "error": f"body invalido: {e}"}, status=400)
                return
            guardar_render_config({"tipologias_desactivadas": desactivadas})
            temas = sorted(fn[:-5] for fn in os.listdir(CONTENT_DIR) if fn.endswith(".json"))
            errores = []
            for tema in temas:
                try:
                    render.generate(tema)
                except Exception as e:
                    errores.append(f"{tema}: {e}")
            if errores:
                self._json({"ok": True, "warning": "; ".join(errores)})
            else:
                self._json({"ok": True})

        elif path == "/api/sync-permitidos":
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    sys.argv = ["sync_ejercicios_permitidos.py"]
                    sync_perm.main()
            except SystemExit as e:
                self._json({"ok": False, "log": buf.getvalue(), "error": str(e)}, status=500)
                return
            except Exception:
                self._json({"ok": False, "log": buf.getvalue(), "error": traceback.format_exc()}, status=500)
                return
            self._json({"ok": True, "log": buf.getvalue()})

        else:
            self.send_error(404, "not found")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Dashboard en http://127.0.0.1:{args.port} (solo localhost, Ctrl+C para parar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
