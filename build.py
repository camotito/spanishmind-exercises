import os
import re

def generate_index():
    html_files = [f for f in os.listdir('.') if f.endswith('.html') and f != 'index.html']
    html_files.sort()

    links_html = ""
    for file in html_files:
        # Intenta extraer el contenido de <title> para que quede bonito, si no usa el nombre del archivo
        title = file.replace('.html', '').replace('-', ' ').title()
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
                if match:
                    title = match.group(1)
        except Exception:
            pass
            
        links_html += f'        <li><a href="{file}">{title}</a></li>\n'

    index_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpanishMind — Ejercicios</title>
    <style>
        body {{ font-family: 'DM Sans', sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; color: #333; }}
        h1 {{ font-family: 'Playfair Display', serif; color: #111; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ margin: 12px 0; }}
        a {{ color: #0066cc; text-decoration: none; font-size: 1.1rem; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>Ejercicios Interactivos</h1>
    <ul>
{links_html}    </ul>
</body>
</html>"""

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(index_template)

if __name__ == '__main__':
    generate_index()