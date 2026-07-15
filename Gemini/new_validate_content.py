import re

def validar_consistencia_ejercicio(ejercicio_json):
    tipologia = ejercicio_json.get("tipologia")
    items = ejercicio_json.get("items", [])
    
    for item in items:
        texto = item.get("texto_enunciado", "")
        soluciones = item.get("solucion_correcta", [])
        idx = item.get("index")
        
        # 1. Validar correspondencia exacta entre número de huecos y soluciones
        num_huecos = len(re.findall(r"_____", texto))
        if num_huecos != len(soluciones):
            return False, f"Item {idx}: Se encontraron {num_huecos} huecos '_____', pero hay {len(soluciones)} soluciones en el array."
            
        # 2. Validar sintaxis limpia de opciones en T5 (sin espacios internos dañinos)
        if tipologia == "T5":
            # Detecta si hay espacios alrededor de la barra dentro de los paréntesis: (lo / la)
            if re.search(r"\(\s*[^)]+\s*/\s*[^)]+\s*\)", texto):
                return False, f"Item {idx}: La opción múltiple inline tiene espacios incorrectos cerca de la barra divisoria."
                
        # 3. Validar presencia de etiquetas de subrayado obligatorias en T7
        if tipologia == "T7":
            if "<u>" not in texto or "</u>" not in texto:
                return False, f"Item {idx}: Ejercicio de tipología T7 (Reescritura) requiere un segmento de texto envuelto en <u>...</u>."
                
    return True, "OK"