#!/usr/bin/env python3
"""
Aplica la asignacion de clasificar_otros.py: (1) añade las tipologias nuevas
(T8-T17) a Gemini/Exercises_typology.md en el mismo formato que las T1-T7
existentes; (2) reetiqueta "tipologia" en ejercicios_raw/*.json para cada
subejercicio que estaba en "OTRO" (o T3/T4 revertidos), conservando
"tipologia_libre" como nota de referencia. NO llama a la API -- es texto puro
sobre datos ya extraidos.

Uso:
    python3 clasificar_otros.py      # genera asignacion_tipologias.json (revisar antes)
    python3 aplicar_tipologias.py
    python3 merge_ejemplos.py        # regenera ejemplos/*.json con las tipologias nuevas
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GEMINI_DIR = os.path.join(HERE, "..", "Gemini")
TYPOLOGY_PATH = os.path.join(GEMINI_DIR, "Exercises_typology.md")
RAW_DIR = os.path.join(HERE, "ejercicios_raw")

ASIGNACION_PATH = os.path.join(HERE, "asignacion_tipologias.json")
DESCRIPCIONES_PATH = os.path.join(HERE, "descripciones_tipologias.json")


def actualizar_catalogo(descripciones):
    with open(TYPOLOGY_PATH, encoding="utf-8") as f:
        contenido = f.read()

    ya_presentes = {t for t in descripciones if f"`[{t}]`" in contenido}
    nuevas = {t: d for t, d in descripciones.items() if t not in ya_presentes}
    if not nuevas:
        print("  (el catalogo ya tiene todas las tipologias nuevas, no se toca)")
        return

    bloques = []
    for tipo in sorted(nuevas, key=lambda t: int(t[1:])):
        nombre, descripcion, proposito = nuevas[tipo]
        bloques.append(
            f"\n## `[{tipo}]` {nombre}\n"
            f"* **Descripción:** {descripcion}\n"
            f"* **Propósito:** {proposito}\n"
        )

    nota = (
        "\n---\n\n"
        "> **Nota (2026-07-20):** las tipologías T8-T17 se añadieron tras digitalizar el libro "
        "completo (126 unidades) -- el catálogo original (T1-T7) se había definido usando solo "
        "12 de las 126 unidades y no cubría patrones reales frecuentes (completar con banco de "
        "palabras adaptadas, ordenar segmentos, combinar/reescribir oraciones, emparejamiento en "
        "columnas, clasificación en tabla, enumeración abierta, acentuación directa sobre la "
        "palabra). Ver `libro_pipeline/clasificar_otros.py` para el criterio de asignación."
    )

    with open(TYPOLOGY_PATH, "w", encoding="utf-8") as f:
        f.write(contenido.rstrip("\n") + "\n" + nota + "\n" + "".join(bloques))

    print(f"  ✅ {len(nuevas)} tipologia(s) nueva(s) añadida(s) a {TYPOLOGY_PATH}")


def reetiquetar_ejercicios(asignacion):
    tocados = 0
    for path in sorted(glob.glob(os.path.join(RAW_DIR, "*.json")), key=lambda p: int(os.path.basename(p)[:-5])):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        cambiado = False
        for ej in data.get("ejercicios", []):
            sub = ej.get("subejercicio")
            if sub in asignacion:
                nuevo_tipo = asignacion[sub]
                if ej.get("tipologia") != nuevo_tipo:
                    ej["tipologia_libre_original"] = ej.get("tipologia_libre")
                    ej["tipologia"] = nuevo_tipo
                    ej["tipologia_libre"] = None
                    cambiado = True

        if cambiado:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tocados += 1

    print(f"  ✅ {tocados} archivo(s) de ejercicios_raw/ reetiquetados")


def main():
    if not os.path.exists(ASIGNACION_PATH):
        raise SystemExit("Corre primero clasificar_otros.py para generar asignacion_tipologias.json")

    with open(ASIGNACION_PATH, encoding="utf-8") as f:
        asignacion = json.load(f)
    with open(DESCRIPCIONES_PATH, encoding="utf-8") as f:
        descripciones = json.load(f)

    print("→ actualizando catalogo de tipologias...")
    actualizar_catalogo(descripciones)

    print("→ reetiquetando ejercicios_raw/...")
    reetiquetar_ejercicios(asignacion)

    print("\n✅ listo -- corre merge_ejemplos.py para regenerar ejemplos/*.json")


if __name__ == "__main__":
    main()
