#!/usr/bin/env python3
"""
Paso 3b: cruza soluciones_gemini.json y soluciones_openai.json (extraidos por
separado por extract_soluciones.py --provider gemini / --provider openai).

El piloto mostro que ambos modelos aciertan la mayoria pero cada uno comete
errores de CONTENIDO distintos en el texto denso del solucionario (no solo de
conteo de huecos, que merge_ejemplos.py ya valida por separado). Un error de
contenido con el conteo correcto no lo detecta esa validacion -- por eso aqui
NO nos fiamos de un solo modelo: solo pasan a soluciones.json (alta confianza)
los subejercicios donde ambos coinciden exactamente (ignorando mayus/minus,
que no afecta a la correccion en render.py). Todo lo demas -- discrepancias,
o presente en un solo proveedor -- se deja en discrepancias_soluciones.json
para que lo resuelvas tu a mano contra el libro fisico.

Uso:
    python3 extract_soluciones.py --provider gemini
    python3 extract_soluciones.py --provider openai
    python3 compare_soluciones.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GEMINI_PATH = os.path.join(HERE, "soluciones_gemini.json")
OPENAI_PATH = os.path.join(HERE, "soluciones_openai.json")
OUT_PATH = os.path.join(HERE, "soluciones.json")
DISCREPANCIAS_PATH = os.path.join(HERE, "discrepancias_soluciones.json")


def normaliza(items):
    return [[t.strip().lower() for t in item] for item in items]


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    gemini = load(GEMINI_PATH)
    openai = load(OPENAI_PATH)

    if not gemini and not openai:
        raise SystemExit(
            f"No hay nada que comparar -- corre primero:\n"
            f"  python3 extract_soluciones.py --provider gemini\n"
            f"  python3 extract_soluciones.py --provider openai"
        )

    todos_los_subs = sorted(set(gemini) | set(openai), key=lambda s: tuple(map(int, s.split("."))))

    acordados = {}
    discrepancias = []

    for sub in todos_los_subs:
        en_gemini = gemini.get(sub)
        en_openai = openai.get(sub)

        if en_gemini and en_openai:
            if normaliza(en_gemini["items"]) == normaliza(en_openai["items"]):
                acordados[sub] = en_openai  # coinciden -- da igual cual se use
                continue
            discrepancias.append(
                {
                    "subejercicio": sub,
                    "razon": "discrepancia_entre_proveedores",
                    "gemini": en_gemini["items"],
                    "openai": en_openai["items"],
                }
            )
        elif en_gemini or en_openai:
            unico = en_gemini or en_openai
            proveedor = "gemini" if en_gemini else "openai"
            discrepancias.append(
                {
                    "subejercicio": sub,
                    "razon": f"solo_visto_por_{proveedor}",
                    proveedor: unico["items"],
                }
            )

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(acordados, f, ensure_ascii=False, indent=2, sort_keys=True)

    with open(DISCREPANCIAS_PATH, "w", encoding="utf-8") as f:
        json.dump(discrepancias, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(acordados)} subejercicio(s) acordados -> {OUT_PATH}")
    if discrepancias:
        print(f"⚠️  {len(discrepancias)} subejercicio(s) para revisar a mano -> {DISCREPANCIAS_PATH}")
        for d in discrepancias:
            print(f"  - {d['subejercicio']}: {d['razon']}")
    else:
        print("✅ sin discrepancias")


if __name__ == "__main__":
    main()
