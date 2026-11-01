#!/usr/bin/env python3
"""Auditoria de la experiencia en movil de las paginas de out/ (ver CLAUDE.md,
"Flujo al generar o cambiar ejercicios").

Abre cada pagina (y cada una de sus paginas de ejercicios) en 4 anchos de movil
(320, 360, 375 y 393) con Chrome y comprueba:
  - desbordes horizontales (algo sale del ancho de la pantalla),
  - campos de texto/seleccion con letra < 16 px (iOS hace zoom al enfocarlos),
  - botones y enlaces con menos de 40 px de alto o de ancho (objetivo tactil),
  - errores en la consola.
Sin argumentos revisa todas las paginas; con nombres de tema, solo esas.

No prueba Safari/WebKit (en este sistema necesita sudo para sus dependencias):
Chrome emula medidas y pantalla tactil, no el motor de iPhone. Para ver como se ve,
--capturas DIR guarda una captura de pagina completa por ancho.

Preparacion una vez:
  python3 -m venv /tmp/pw && /tmp/pw/bin/pip install playwright
Uso:
  /tmp/pw/bin/python herramientas/audit_movil.py [tema ...] [--capturas DIR]
Sale con codigo 1 si encuentra algo.
"""
import argparse
import glob
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
ANCHOS = [(320, 568), (360, 800), (375, 667), (393, 852)]

JS = """()=>{
const vw=document.documentElement.clientWidth, out={over:document.documentElement.scrollWidth>vw, bad:[], small:[], tap:[]};
for(const el of document.querySelectorAll('body *')){
 const r=el.getBoundingClientRect(); if(!r.width||!r.height) continue;
 const cs=getComputedStyle(el); if(cs.visibility==='hidden') continue;
 if(el.closest('[hidden]')||el.closest('dialog:not([open])')) continue;
 if(r.right>vw+1||r.left<-1) out.bad.push(el.tagName+'.'+el.className);
 if((el.tagName==='INPUT'||el.tagName==='SELECT')&&parseFloat(cs.fontSize)<16) out.small.push(el.tagName+' '+cs.fontSize);
 if((el.tagName==='BUTTON'||el.tagName==='SELECT'||(el.tagName==='A'&&!el.closest('li')))&&(r.height<40||r.width<40)) out.tap.push(el.tagName+'.'+el.className+' '+Math.round(r.width)+'x'+Math.round(r.height));
}
return out}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("temas", nargs="*")
    ap.add_argument("--capturas")
    args = ap.parse_args()
    paginas = sorted(glob.glob(os.path.join(OUT, "*.html")))
    if args.temas:
        paginas = [p for p in paginas if os.path.basename(p)[:-5] in args.temas]
    if args.capturas:
        os.makedirs(args.capturas, exist_ok=True)
    problemas = 0
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        for w, h in ANCHOS:
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2,
                                is_mobile=True, has_touch=True)
            pg = ctx.new_page()
            errs = []
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs.append(str(e)))
            for f in paginas:
                nombre = os.path.basename(f)[:-5]
                pg.goto("file://" + f)
                n = 0
                while True:
                    n += 1
                    r = pg.evaluate(JS)
                    if r["over"] or r["bad"] or r["small"] or r["tap"]:
                        problemas += 1
                        print(f"{w}px {nombre} pag {n}: desborde={r['over']} fuera={sorted(set(r['bad']))[:3]} "
                              f"letra<16={sorted(set(r['small']))[:2]} toque<40={sorted(set(r['tap']))[:3]}")
                    if args.capturas and n == 1:
                        pg.screenshot(path=os.path.join(args.capturas, f"{nombre}_{w}.png"), full_page=True)
                    nx = pg.locator("#btn-next")
                    if nx.count() == 0 or not nx.is_visible() or nx.is_disabled() or n > 15:
                        break
                    nx.click()
            if errs:
                problemas += 1
                print(f"{w}px errores de consola: {sorted(set(errs))[:3]}")
            ctx.close()
        b.close()
    print("Sin problemas." if not problemas else f"{problemas} problema(s).")
    sys.exit(1 if problemas else 0)


if __name__ == "__main__":
    main()
