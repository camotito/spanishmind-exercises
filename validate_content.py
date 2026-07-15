#!/usr/bin/env python3
"""
Valida el JSON de contenido generado por Gemini antes de pasarlo al generador de HTML.
Uso: python3 validate_content.py u01-masculino-femenino.json
"""
import json
import sys

SCHEMAS = {
    "fill-blank": {"required": ["oracion", "respuesta"], "optional": ["pista"]},
    "multiple-choice": {"required": ["pregunta", "opciones", "respuesta"], "optional": ["nota"]},
    "gender-classification": {"required": ["palabra", "respuesta"], "optional": ["nota"]},
    "error-correction": {"required": ["oracion_incorrecta", "oracion_correcta"], "optional": ["explicacion"]},
    "transform": {"required": ["instruccion", "entrada", "respuesta"], "optional": []},
}


def validate(path):
    errors = []

    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ JSON inválido: {e}")
            sys.exit(1)

    if "unidad" not in data:
        errors.append("Falta 'unidad' en el nivel raíz")

    ejercicios = data.get("ejercicios", [])
    if not ejercicios:
        errors.append("'ejercicios' está vacío o no existe")

    tipos_usados = set()
    for i, ej in enumerate(ejercicios):
        tipo = ej.get("tipo")
        tipos_usados.add(tipo)

        if tipo not in SCHEMAS:
            errors.append(f"Ejercicio {i}: tipo desconocido '{tipo}'")
            continue

        for field in SCHEMAS[tipo]["required"]:
            if field not in ej or not ej[field]:
                errors.append(f"Ejercicio {i} ({tipo}): falta campo requerido '{field}'")

        if tipo == "multiple-choice":
            opciones = ej.get("opciones", [])
            if ej.get("respuesta") not in opciones:
                errors.append(f"Ejercicio {i}: 'respuesta' no está en 'opciones'")

    if len(tipos_usados) < 2:
        errors.append(f"Solo hay {len(tipos_usados)} tipo(s) de ejercicio, se requieren mínimo 2")

    if len(ejercicios) < 6:
        errors.append(f"Solo hay {len(ejercicios)} ejercicios, se recomienda mínimo 6")

    if errors:
        print(f"❌ {len(errors)} error(es) encontrado(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"✅ Válido: {len(ejercicios)} ejercicios, tipos: {', '.join(sorted(tipos_usados))}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 validate_content.py <archivo.json>")
        sys.exit(1)
    validate(sys.argv[1])
