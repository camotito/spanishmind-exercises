#!/usr/bin/env python3
"""
Valida indice.yaml: campos requeridos, slugs duplicados, tipos.
Con --fix: reescribe el YAML normalizado (mismo orden, sin trailing spaces,
formato consistente).

Uso:
    python3 check_indice.py indice.yaml
    python3 check_indice.py indice.yaml --fix
"""
import sys
import yaml

REQUIRED = ["tema", "titulo", "ejemplo"]


def check(indice):
    errors = []
    seen_temas = {}

    for i, t in enumerate(indice):
        for field in REQUIRED:
            if field not in t:
                errors.append(f"[{i}] falta campo '{field}'")

        tema = t.get("tema")
        if tema:
            if tema in seen_temas:
                errors.append(f"[{i}] tema duplicado: '{tema}' (ya en [{seen_temas[tema]}])")
            else:
                seen_temas[tema] = i

            if tema != tema.strip().lower() or " " in tema:
                errors.append(f"[{i}] tema mal formado (espacios/mayusculas): '{tema}'")

        tv = t.get("tiempo_verbal")
        if tv is not None and not isinstance(tv, str):
            errors.append(f"[{i}] tiempo_verbal debe ser string o null, es {type(tv).__name__}")

    return errors


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 check_indice.py <indice.yaml> [--fix]")

    path = sys.argv[1]
    fix = "--fix" in sys.argv

    with open(path, encoding="utf-8") as f:
        indice = yaml.safe_load(f)

    errors = check(indice)

    if errors:
        print(f"❌ {len(errors)} problema(s):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("✅ Sin problemas de estructura")

    if fix:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(indice, f, allow_unicode=True, sort_keys=False)
        print(f"🔧 {path} reescrito con formato normalizado")

    sys.exit(1 if errors and not fix else 0)


if __name__ == "__main__":
    main()
