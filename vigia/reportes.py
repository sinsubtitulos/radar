"""Genera los resultados: reporte HTML, CSV para Excel y el archivo que lee el Radar."""
from __future__ import annotations

import csv
import html
import json
import os
from datetime import datetime, timedelta

from .motor import BOGOTA, guardar_json

E = html.escape


def _nuevas_de(estado, oid, desde: str):
    o = estado["orgs"].get(oid, {})
    return [v for v in o.get("vacantes", {}).values()
            if v.get("primera_vez", "") >= desde and not v.get("linea_base") and not v.get("excluida") and not v.get("cerrada") and not v.get("fuera")]


def _activas_de(estado, oid):
    o = estado["orgs"].get(oid, {})
    return [v for v in o.get("vacantes", {}).values() if not v.get("cerrada") and not v.get("excluida") and not v.get("fuera")]


def generar(estado: dict, orgs: list[dict], carpeta: str, cfg: dict):
    os.makedirs(carpeta, exist_ok=True)
    hoy = estado["ultima_corrida"]
    dia = hoy[:10]
    por_id = {o["id"]: o for o in orgs}
    dias_nuevas = cfg.get("dias_como_nueva", 7)
    desde_semana = (datetime.now(BOGOTA) - timedelta(days=dias_nuevas)).strftime("%Y-%m-%d")

    # ── nuevas de ESTA corrida ──────────────────────────────────────────────
    nuevas = []
    for oid in estado["orgs"]:
        if oid not in por_id:
            continue
        for v in _nuevas_de(estado, oid, hoy):
            nuevas.append((por_id[oid], v))
    nuevas.sort(key=lambda x: (not x[1].get("coincide"), x[0]["n"].lower(), x[1]["titulo"].lower()))

    campos = ["Fecha detección", "Organización", "Categoría", "Red AFE", "Vacante", "Ubicación", "Lugar publicado",
              "Fecha publicada", "Coincide con perfil", "Enlace"]
    UBIC = {"colombia": "Colombia", "remoto": "Remoto", "colombia_supuesta": "Colombia (organización colombiana)"}

    def fila(o, v):
        return [v.get("primera_vez", ""), o["n"], o.get("t", ""), "Sí" if o.get("afe") else "", v.get("titulo", ""),
                UBIC.get(v.get("ubicacion", ""), ""), v.get("lugar", ""), v.get("fecha", ""), ", ".join(v.get("coincide") or []), v.get("url", "")]

    def escribir_csv(ruta, filas, modo="w"):
        nuevo = modo == "w" or not os.path.exists(ruta)
        with open(ruta, modo, newline="", encoding="utf-8-sig" if nuevo else "utf-8") as f:
            w = csv.writer(f, delimiter=";")
            if nuevo:
                w.writerow(campos)
            w.writerows(filas)

    escribir_csv(os.path.join(carpeta, "vacantes_nuevas.csv"), [fila(o, v) for o, v in nuevas])
    if nuevas:
        escribir_csv(os.path.join(carpeta, "historial_vacantes_nuevas.csv"), [fila(o, v) for o, v in nuevas], "a")
    activas = [(por_id[oid], v) for oid in estado["orgs"] if oid in por_id for v in _activas_de(estado, oid)]
    activas.sort(key=lambda x: (x[0]["n"].lower(), x[1]["titulo"].lower()))
    escribir_csv(os.path.join(carpeta, "vacantes_activas.csv"), [fila(o, v) for o, v in activas])

    # ── archivo para el Radar ───────────────────────────────────────────────
    radar = {"app": "progresso-radar-vigia", "generado": hoy, "dias_como_nueva": dias_nuevas, "orgs": {}}
    for oid, e in estado["orgs"].items():
        if oid not in por_id:
            continue
        act = _activas_de(estado, oid)
        nv = _nuevas_de(estado, oid, desde_semana)
        radar["orgs"][oid] = {
            "estado": e.get("estado"), "revision": e.get("ultima_revision"), "nota": e.get("nota", ""),
            "activas": len(act), "pagina_cambio": e.get("huella_cambio", "") >= desde_semana if e.get("huella_cambio") else False,
            "nuevas": [{"t": v["titulo"], "u": v.get("url", ""), "l": v.get("lugar", "") or UBIC.get(v.get("ubicacion", ""), ""), "f": v.get("primera_vez", "")[:10],
                        "c": v.get("coincide") or []} for v in sorted(nv, key=lambda v: v.get("primera_vez", ""), reverse=True)][:30],
            "lista": [{"t": v["titulo"], "u": v.get("url", ""), "l": v.get("lugar", "") or UBIC.get(v.get("ubicacion", ""), "")} for v in act][:40],
        }
    guardar_json(os.path.join(carpeta, "radar_vacantes.json"), radar)

    # ── reporte HTML ────────────────────────────────────────────────────────
    res = estado["corridas"][-1]
    modificadas = [(por_id[oid], e) for oid, e in estado["orgs"].items()
                   if oid in por_id and e.get("huella_cambio") == hoy and not _nuevas_de(estado, oid, hoy)]
    revisar = [(por_id[oid], e) for oid, e in estado["orgs"].items()
               if oid in por_id and (e.get("estado") in ("error", "bloqueada") or (e.get("requiere_js") and e.get("metodo") == "html"))]
    revisar.sort(key=lambda x: x[0]["n"].lower())
    omitidas = sum(1 for e in estado["orgs"].values() if e.get("estado") == "omitida")

    grupos: dict[str, list] = {}
    for o, v in nuevas:
        grupos.setdefault(o["id"], []).append(v)

    def chip(t, cls=""):
        return f'<span class="chip {cls}">{E(t)}</span>'

    bloques = []
    for oid, vs in grupos.items():
        o = por_id[oid]
        coinc = any(v.get("coincide") for v in vs)
        items = "".join(
            f'<li class="vac{" match" if v.get("coincide") else ""}" data-q="{E((v["titulo"] + " " + o["n"]).lower())}">'
            f'<a href="{E(v.get("url", ""))}" target="_blank" rel="noopener">{E(v["titulo"])}</a>'
            f'<div class="meta">{chip(UBIC.get(v.get("ubicacion", ""), ""), "loc") if v.get("ubicacion") else ""}{E(v.get("lugar", ""))}{" · " if v.get("lugar") and v.get("fecha") else ""}{E(v.get("fecha", ""))}'
            f'{"".join(chip(c, "ok") for c in (v.get("coincide") or []))}</div></li>' for v in vs)
        bloques.append(
            f'<section class="org{" has-match" if coinc else ""}"><div class="org-h"><h3>{E(o["n"])}</h3>'
            f'{chip(o.get("t", ""))}{chip("Red AFE", "afe") if o.get("afe") else ""}'
            f'<a class="src" href="{E(o.get("j", ""))}" target="_blank" rel="noopener">Página de vacantes ↗</a></div><ul>{items}</ul></section>')

    hist = "".join(
        f'<tr><td>{E(c["fecha"])}</td><td>{c["revisadas"]}</td><td>{c["nuevas"]}</td><td>{c["nuevas_coinciden"]}</td>'
        f'<td>{c["cerradas"]}</td><td>{c["errores"]}</td></tr>' for c in reversed(estado["corridas"][-14:]))

    lista_mod = "".join(f'<li><a href="{E(o.get("j", ""))}" target="_blank" rel="noopener">{E(o["n"])}</a> <span class="muted">· {E(o.get("t", ""))}</span></li>' for o, e in modificadas)
    lista_rev = "".join(
        f'<tr><td><a href="{E(o.get("j", ""))}" target="_blank" rel="noopener">{E(o["n"])}</a></td>'
        f'<td>{E({"error": "Error", "bloqueada": "Bloqueada"}.get(e.get("estado"), "Carga con JavaScript"))}</td>'
        f'<td class="muted">{E(e.get("nota") or "Activa render_js en config.yaml para leerla")}</td></tr>' for o, e in revisar)

    perfil = cfg.get("perfil", {})
    kws = ", ".join(perfil.get("palabras_clave") or []) or "sin palabras clave (edita config.yaml)"
    base_msg = (f'<div class="note">Primera revisión de {res["linea_base"]} vacantes registradas como <b>línea base</b>: '
                f'no se cuentan como nuevas. Desde la próxima corrida verás solo lo que aparezca después de hoy.</div>'
                if res.get("linea_base") else "")

    page = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vigía de vacantes · {E(dia)}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#F5F1E9;--s:#fff;--s2:#FAFAF6;--ink:#1C1812;--mut:#7A7060;--b:#E2DDD3;--g:#2A6348;--gb:#E8F1EC;--p:#5C3D8F;--pb:#EEE9F7;--a:#8C5A18;--ab:#F5EDE0;--r:#8B1F1F;--rb:#F5E8E8}}
*{{box-sizing:border-box;margin:0;padding:0}}body{{background:var(--bg);color:var(--ink);font:15px/1.55 'DM Sans',sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:2.5rem 1.25rem 5rem}}
h1{{font:400 clamp(1.9rem,4vw,2.7rem)/1.1 'DM Serif Display',serif;letter-spacing:-.02em}}h1 em{{color:var(--mut)}}
h2{{font:400 1.45rem 'DM Serif Display',serif;margin:2.25rem 0 .9rem}}h3{{font:400 1.08rem 'DM Serif Display',serif}}
.sub{{color:var(--mut);margin:.5rem 0 1.5rem}}.muted{{color:var(--mut)}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:.75rem}}.kpi{{background:var(--s);border:1px solid var(--b);border-radius:14px;padding:.9rem 1rem}}
.kpi b{{display:block;font:400 1.9rem/1.1 'DM Serif Display',serif}}.kpi span{{font-size:12px;color:var(--mut)}}.kpi.hi b{{color:var(--g)}}
.note{{background:var(--ab);border:1px solid rgba(140,90,24,.25);color:var(--a);border-radius:12px;padding:.75rem 1rem;margin-top:1rem;font-size:14px}}
.bar{{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;margin:1.25rem 0 .5rem}}
#q{{flex:1;min-width:220px;border:1.5px solid var(--b);border-radius:10px;padding:.6rem .85rem;font:inherit;background:var(--s)}}
.bar label{{font-size:13.5px;display:flex;gap:.4rem;align-items:center;cursor:pointer}}
.org{{background:var(--s);border:1px solid var(--b);border-radius:16px;padding:1rem 1.2rem;margin-bottom:.75rem}}
.org.has-match{{border-color:rgba(42,99,72,.4)}}.org-h{{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;margin-bottom:.5rem}}
.org-h .src{{margin-left:auto;font-size:12.5px;color:var(--mut)}}.org ul{{list-style:none}}
.vac{{padding:.55rem 0;border-top:1px solid var(--b)}}.vac:first-child{{border-top:none}}.vac a{{color:var(--ink);font-weight:500;text-decoration:none}}.vac a:hover{{text-decoration:underline}}
.vac.match a{{color:var(--g)}}.meta{{font-size:12.5px;color:var(--mut);display:flex;gap:.35rem;flex-wrap:wrap;align-items:center;margin-top:.15rem}}
.chip{{display:inline-flex;font-size:11px;font-weight:500;padding:.08rem .55rem;border-radius:20px;background:var(--s2);border:1px solid var(--b);color:var(--mut)}}
.chip.ok{{background:var(--gb);color:var(--g);border-color:rgba(42,99,72,.2)}}.chip.loc{{background:var(--ab);color:var(--a);border-color:rgba(140,90,24,.25)}}.chip.afe{{background:var(--pb);color:var(--p);border-color:rgba(92,61,143,.25)}}
table{{width:100%;border-collapse:collapse;background:var(--s);border:1px solid var(--b);border-radius:14px;overflow:hidden;font-size:13.5px}}
th{{text-align:left;font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--mut);background:var(--s2);padding:.65rem .8rem}}td{{padding:.6rem .8rem;border-top:1px solid var(--b);vertical-align:top}}
td a{{color:var(--ink)}}details{{margin-top:.5rem}}summary{{cursor:pointer;color:var(--mut);font-size:14px}}
.cols{{columns:2;font-size:14px}}.cols a{{color:var(--ink)}}.cols li{{margin:0 0 .3rem 1rem}}
.empty{{background:var(--s);border:1px dashed var(--b);border-radius:16px;padding:2rem;text-align:center;color:var(--mut)}}
@media(max-width:720px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.cols{{columns:1}}.org-h .src{{margin-left:0}}}}
</style></head><body><div class="wrap">
<h1>Vigía de vacantes <em>· Radar Progresso</em></h1>
<p class="sub">Corrida del {E(hoy)} (hora de Bogotá) · Solo vacantes en <b>Colombia o remotas</b> · Perfil: {E(kws)}</p>
<div class="kpis">
<div class="kpi hi"><b>{res["nuevas_coinciden"]}</b><span>Nuevas que coinciden con el perfil</span></div>
<div class="kpi"><b>{res["nuevas"]}</b><span>Vacantes nuevas en total</span></div>
<div class="kpi"><b>{res.get("fuera_ubicacion", 0)}</b><span>Nuevas descartadas por estar fuera de Colombia o sin ubicación</span></div>
<div class="kpi"><b>{res["paginas_modificadas"]}</b><span>Páginas que cambiaron</span></div>
<div class="kpi"><b>{res["errores"] + res["bloqueadas"]}</b><span>Con error o bloqueadas</span></div>
</div>{base_msg}
<h2>Vacantes nuevas</h2>
<div class="bar"><input id="q" placeholder="Filtrar por cargo u organización…"><label><input type="checkbox" id="m"> Solo las que coinciden con el perfil</label></div>
<div id="list">{"".join(bloques) or '<div class="empty">No aparecieron vacantes nuevas en esta corrida.</div>'}</div>
<h2>Páginas que cambiaron sin enlaces detectables</h2>
<p class="muted" style="margin-bottom:.6rem">Su contenido cambió desde la corrida anterior, pero no publican cada vacante como enlace (suelen usar PDF o texto). Vale la pena abrirlas.</p>
{f'<ul class="cols">{lista_mod}</ul>' if lista_mod else '<div class="empty">Ninguna esta vez.</div>'}
<h2>Para revisar manualmente</h2>
<details{" open" if len(revisar) < 15 else ""}><summary>{len(revisar)} páginas no se pudieron leer completas · {omitidas} sin página o en redes sociales (no se rastrean)</summary>
{f'<table style="margin-top:.6rem"><tr><th>Organización</th><th>Motivo</th><th>Detalle</th></tr>{lista_rev}</table>' if lista_rev else ''}</details>
<h2>Historial de corridas</h2>
<table><tr><th>Fecha</th><th>Revisadas</th><th>Nuevas</th><th>Coinciden</th><th>Cerradas</th><th>Errores</th></tr>{hist}</table>
</div>
<script>
const q=document.getElementById('q'),m=document.getElementById('m');
function f(){{const t=q.value.toLowerCase().trim();document.querySelectorAll('.org').forEach(o=>{{let n=0;o.querySelectorAll('.vac').forEach(v=>{{const ok=(!t||v.dataset.q.includes(t))&&(!m.checked||v.classList.contains('match'));v.style.display=ok?'':'none';if(ok)n++}});o.style.display=n?'':'none'}})}}
q.addEventListener('input',f);m.addEventListener('change',f);
</script></body></html>"""
    with open(os.path.join(carpeta, "reporte.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    return {"nuevas": nuevas, "resumen": res}
