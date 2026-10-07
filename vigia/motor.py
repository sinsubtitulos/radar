"""Orquesta una corrida: lee las organizaciones, compara con la corrida anterior y guarda el estado."""
from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

from .extraer import clave, norm
from .http import Bloqueada, Http
from .lectores import leer, leer_render
from . import ubicacion as ub
from .ficha import leer_ficha, ubicacion_desde_ficha

BOGOTA = timezone(timedelta(hours=-5))


def ahora() -> str:
    return datetime.now(BOGOTA).strftime("%Y-%m-%d %H:%M")


def cargar_json(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return defecto


def guardar_json(ruta, data):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def _patrones(lista):
    return [norm(x) for x in (lista or []) if str(x).strip()]


FILTRO_CORPORATIVO = [
    "fundacion", "social", "sociales", "comunidad", "comunidades", "comunitario", "comunitaria",
    "sostenibilidad", "sostenible", "ambiental", "medio ambiente", "responsabilidad social", "rse", "esg",
    "impacto", "relacionamiento", "voluntariado", "derechos humanos", "gestion social", "inversion social",
    # asuntos de sostenibilidad
    "cambio climatico", "climatico", "climatica", "accion climatica", "carbono", "huella de carbono",
    "descarbonizacion", "emisiones", "gases de efecto invernadero", "energia renovable", "energias renovables",
    "transicion energetica", "eficiencia energetica", "economia circular", "residuos", "reciclaje",
    "biodiversidad", "conservacion", "gestion ambiental", "recurso hidrico", "gestion hidrica",
    "reporte de sostenibilidad", "informe de sostenibilidad", "gri", "tcfd", "asg", "negocios sostenibles",
    "finanzas sostenibles", "bonos verdes", "taxonomia verde",
    "sustainability", "sustainable", "environmental", "climate", "carbon", "decarbonization", "net zero",
    "renewable", "renewables", "energy transition", "circular economy", "biodiversity", "conservation",
    "green finance",
]


# Para empresas cuyos cargos de interés son de impacto social o asuntos públicos (p. ej. Johnson & Johnson).
# Incluye equivalentes en inglés porque estos portales suelen publicar en ese idioma.
FILTRO_ASUNTOS_PUBLICOS = FILTRO_CORPORATIVO + [
    "impacto social", "asuntos publicos", "asuntos corporativos", "asuntos gubernamentales",
    "relaciones gubernamentales", "relaciones institucionales", "politica publica", "politicas publicas",
    "acceso al mercado", "equidad en salud", "salud publica", "salud global", "asociaciones con pacientes",
    "comunicaciones corporativas", "filantropia", "ciudadania corporativa",
    "foundation", "social impact", "community", "communities", "sustainability", "csr", "philanthropy",
    "public affairs", "corporate affairs", "government affairs", "government relations", "public policy",
    "health policy", "market access", "health equity", "global health", "public health", "patient advocacy",
    "patient engagement", "corporate communications", "external affairs", "stakeholder engagement", "citizenship",
]


def filtro_de(org: dict | None, cfg: dict) -> list[str]:
    """Palabras que debe tener el cargo para contarse, en organizaciones que publican en el portal de su empresa.
    "filtro" puede ser "corporativo", "asuntos_publicos" o una lista propia de palabras."""
    f = (org or {}).get("filtro")
    if not f:
        return []
    if f == "corporativo":
        f = cfg.get("filtro_corporativo") or FILTRO_CORPORATIVO
    elif f == "asuntos_publicos":
        f = cfg.get("filtro_asuntos_publicos") or FILTRO_ASUNTOS_PUBLICOS
    return [norm(x) for x in f if str(x).strip()]


def clasificar(v: dict, perfil: dict, org: dict | None = None, reglas=None, filtro: list[str] | None = None) -> dict:
    txt = norm(f"{v.get('titulo', '')} {v.get('lugar', '')}")
    inc = [str(x).strip() for x in (perfil.get("palabras_clave") or []) if str(x).strip()]
    exc = _patrones(perfil.get("excluir"))
    v["coincide"] = [p for p in inc if re.search(r"\b" + re.escape(norm(p)) + r"\b", txt)]
    v["excluida"] = any(re.search(r"\b" + re.escape(p) + r"\b", txt) for p in exc)
    if filtro:
        t2 = norm(f"{v.get('titulo', '')} {v.get('contexto', '')}")
        if not any(re.search(r"\b" + re.escape(p) + r"\b", t2) for p in filtro):
            v["excluida"] = True  # portal corporativo: el cargo no tiene relación con la fundación o lo social
    if reglas is not None:
        v["ubicacion"] = ub.clasificar(v, org or {}, reglas)
        v["fuera"] = not ub.permitida(v["ubicacion"], reglas)
    v.pop("contexto", None)  # solo se usa para leer el lugar; no se guarda
    return v


def correr(cfg: dict, orgs: list[dict], ruta_estado: str, log=print) -> dict:
    hoy = ahora()
    estado = cargar_json(ruta_estado, {"orgs": {}, "corridas": []})
    http = Http(cfg)
    perfil = cfg.get("perfil", {})
    reglas = ub.construir(cfg)

    if not cfg.get("incluir_agregadores", True):
        orgs = [o for o in orgs if o.get("t") != "Agregador"]

    resultados: dict[str, dict] = {}

    def tarea(o):
        try:
            return o["id"], leer(http, o, cfg)
        except Bloqueada as e:
            return o["id"], {"estado": "bloqueada", "nota": str(e)}
        except Exception as e:  # noqa: BLE001
            msg = str(e).split("\n")[0][:160]
            return o["id"], {"estado": "error", "nota": f"{type(e).__name__}: {msg}"}

    log(f"Revisando {len(orgs)} organizaciones…")
    with ThreadPoolExecutor(max_workers=cfg.get("concurrencia", 6)) as ex:
        futs = [ex.submit(tarea, o) for o in orgs]
        for i, f in enumerate(as_completed(futs), 1):
            oid, res = f.result()
            resultados[oid] = res
            if i % 25 == 0 or i == len(orgs):
                log(f"  {i}/{len(orgs)}")

    # Segunda pasada (en serie): páginas que cargan sus vacantes con JavaScript
    por_id = {o["id"]: o for o in orgs}
    pendientes_js = [oid for oid, r in resultados.items() if r.get("requiere_js")]
    if pendientes_js and cfg.get("render_js"):
        log(f"Abriendo {len(pendientes_js)} páginas con navegador (cargan con JavaScript)…")
        for oid in pendientes_js:
            try:
                resultados[oid] = leer_render(http, por_id[oid]["j"])
            except Exception as e:  # noqa: BLE001
                resultados[oid]["nota"] = f"No se pudo abrir con navegador: {type(e).__name__}"
    http.cerrar()

    # ── comparar con la corrida anterior ────────────────────────────────────
    resumen = {"fecha": hoy, "revisadas": 0, "ok": 0, "errores": 0, "omitidas": 0, "bloqueadas": 0,
               "nuevas": 0, "nuevas_coinciden": 0, "fuera_ubicacion": 0, "cerradas": 0, "linea_base": 0, "paginas_modificadas": 0}
    pendientes_ficha: list[tuple[str, str]] = []
    for oid, res in resultados.items():
        prev = estado["orgs"].get(oid)
        e = prev or {"vacantes": {}}
        # primera lectura exitosa, o cambió la forma de leer la página (p. ej. se activó render_js):
        # lo que aparezca queda como línea base y no se reporta como nuevo
        primera = not e.get("base_ok") or (res.get("metodo") and e.get("metodo_base") not in (None, res.get("metodo")))
        e["metodo_base"] = res.get("metodo") or e.get("metodo_base")
        e.update({"ultima_revision": hoy, "estado": res["estado"], "nota": res.get("nota", ""),
                  "metodo": res.get("metodo", e.get("metodo", "")), "requiere_js": bool(res.get("requiere_js"))})
        resumen["revisadas"] += 1
        if res["estado"] == "error":
            resumen["errores"] += 1
        elif res["estado"] == "omitida":
            resumen["omitidas"] += 1
        elif res["estado"] == "bloqueada":
            resumen["bloqueadas"] += 1
        if res["estado"] != "ok":
            estado["orgs"][oid] = e
            continue
        resumen["ok"] += 1

        # huella de la página: avisa si cambió aunque no se detecten enlaces
        h = res.get("huella")
        if h:
            if e.get("huella") and e["huella"] != h:
                e["huella_cambio"] = hoy
                resumen["paginas_modificadas"] += 1
            e["huella"] = h

        actuales = {}
        for v in res.get("vacantes", []):
            v = clasificar(dict(v), perfil, por_id.get(oid), reglas, filtro_de(por_id.get(oid), cfg))
            actuales[clave(v)] = v
        for k, v in actuales.items():
            if k in e["vacantes"]:
                old = e["vacantes"][k]
                campos = ["titulo", "url", "fecha", "coincide", "excluida"]
                if v.get("lugar"):
                    campos.append("lugar")
                # si la ubicación salió de abrir la ficha, no la borra una lectura del listado que no la trae
                if not (old.get("ficha") and v.get("ubicacion") == "sin_dato"):
                    campos += ["ubicacion", "fuera"]
                old.update({k2: v[k2] for k2 in campos if v.get(k2) is not None})
                old["ultima_vez"] = hoy
                old.pop("cerrada", None)
            else:
                v.update({"primera_vez": hoy, "ultima_vez": hoy, "linea_base": primera})
                e["vacantes"][k] = v
                if primera:
                    resumen["linea_base"] += 1
                elif v.get("ubicacion") == "sin_dato" and not v["excluida"] and cfg.get("abrir_fichas", True):
                    pendientes_ficha.append((oid, k))  # se decide después de abrir la ficha
                elif v.get("fuera"):
                    resumen["fuera_ubicacion"] += 1
                elif not v["excluida"]:
                    resumen["nuevas"] += 1
                    if v["coincide"]:
                        resumen["nuevas_coinciden"] += 1
        for k, v in e["vacantes"].items():
            if k not in actuales and not v.get("cerrada"):
                v["cerrada"] = hoy
                resumen["cerradas"] += 1
        # limpia vacantes cerradas hace más de 60 días
        limite = (datetime.now(BOGOTA) - timedelta(days=60)).strftime("%Y-%m-%d")
        e["vacantes"] = {k: v for k, v in e["vacantes"].items() if not v.get("cerrada") or v["cerrada"] >= limite}
        e["base_ok"] = True
        estado["orgs"][oid] = e

    # ── segunda mirada: abrir la ficha de las vacantes nuevas sin ubicación ──
    resumen["fichas_abiertas"] = resumen["fichas_rescatadas"] = 0
    if pendientes_ficha:
        maximo = cfg.get("maximo_fichas_por_corrida", 300)
        log(f"Abriendo {min(len(pendientes_ficha), maximo)} fichas de vacantes nuevas sin ubicación…")
        http2 = Http(cfg)

        def mirar(par):
            oid, k = par
            v = estado["orgs"][oid]["vacantes"][k]
            try:
                f = leer_ficha(http2, v.get("url", ""))
                return par, f, None
            except Exception as e:  # noqa: BLE001
                return par, None, e

        with ThreadPoolExecutor(max_workers=cfg.get("concurrencia", 6)) as ex:
            resultados_f = list(ex.map(mirar, pendientes_ficha[:maximo]))
        http2.cerrar()
        for (oid, k), f, err in resultados_f + [((o, k), None, None) for o, k in pendientes_ficha[maximo:]]:
            v = estado["orgs"][oid]["vacantes"][k]
            if f is not None:
                resumen["fichas_abiertas"] += 1
                u = ubicacion_desde_ficha(f, reglas)
                v["ficha"] = True
                if f.get("lugar"):
                    v["lugar"] = f["lugar"]
                if u != "sin_dato":
                    v["ubicacion"] = u
                    v["fuera"] = not ub.permitida(u, reglas)
                    if not v["fuera"]:
                        resumen["fichas_rescatadas"] += 1
                        clasificar(v, perfil)  # recalcula coincidencias con el lugar encontrado
            if v.get("fuera", True):
                resumen["fuera_ubicacion"] += 1
            else:
                resumen["nuevas"] += 1
                if v.get("coincide"):
                    resumen["nuevas_coinciden"] += 1
        log(f"  {resumen['fichas_rescatadas']} confirmadas en Colombia o remoto al abrir su ficha.")

    estado["corridas"] = (estado.get("corridas", []) + [resumen])[-90:]
    estado["ultima_corrida"] = hoy
    guardar_json(ruta_estado, estado)
    log(f"Listo: {resumen['nuevas']} vacantes nuevas ({resumen['nuevas_coinciden']} coinciden con el perfil), "
        f"{resumen['errores']} errores, {resumen['linea_base']} registradas como línea base.")
    return estado
