#!/usr/bin/env python3
"""
Calcula tiempos_permitidos para cada tema y lo escribe en indice.yaml.
Editable a mano despues si algun tema necesita ajuste.

Uso:
    python3 compute_tenses.py
"""
import sys
import yaml


def compute(indice):
    seen = []
    for t in indice:
        tv = t.get("forma_verbal")
        allowed = list(seen)
        if tv and tv not in allowed:
            allowed.append(tv)
        t["tiempos_permitidos"] = allowed or ["presente de indicativo"]
        if tv and tv not in seen:
            seen.append(tv)
    return indice


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: python3 compute_tenses.py <indice.yaml>")

    path = sys.argv[1]

    with open(path, encoding="utf-8") as f:
        indice = yaml.safe_load(f)

    indice = compute(indice)

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(indice, f, allow_unicode=True, sort_keys=False)

    print(f"✅ tiempos_permitidos escrito para {len(indice)} temas en {path}")


if __name__ == "__main__":
    main()
