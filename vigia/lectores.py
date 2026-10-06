"""Lectores por tipo de portal. Cada lector devuelve una lista de vacantes {titulo, url, lugar, fecha}.

Las plataformas de empleo conocidas (Workday, Greenhouse, etc.) publican sus vacantes en formato
estructurado; leerlas así es más preciso y más liviano que leer la página visible.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from .extraer import extraer_enlaces, huella_pagina, parece_js

NO_RASTREABLES = re.compile(r"(linkedin\.com|whatsapp|wa\.me|facebook\.com|instagram\.com|t\.me/)", re.I)


def tipo_portal(url: str) -> str:
    u = (url or "").lower()
    if not u:
        return "sin_enlace"
    if NO_RASTREABLES.search(u):
        return "red_social"
    for k, v in [("myworkdayjobs.com", "workday"), ("greenhouse.io", "greenhouse"), ("lever.co", "lever"),
                 ("apply.workable.com", "workable"), ("bamboohr.com", "bamboohr"), ("smartrecruiters.com", "smartrecruiters"),
                 ("recruitee.com", "recruitee"), ("jobs.personio", "personio"), ("breezy.hr", "breezy"),
                 ("reliefweb.int", "reliefweb")]:
        if k in u:
            return v
    return "html"


# ── Workday ──────────────────────────────────────────────────────────────────
def workday(http, url, cfg):
    p = urlparse(url)
    host = p.netloc
    tenant = host.split(".")[0]
    partes = [x for x in p.path.split("/") if x]
    partes = [x for x in partes if not re.fullmatch(r"[a-z]{2}(-[A-Z]{2})?", x)]  # quita en-US, es
    sitio = partes[0] if partes else "External"
    api = f"https://{host}/wday/cxs/{tenant}/{sitio}/jobs"
    maximo = cfg.get("maximo_por_portal", 200)
    out, vistos = [], set()

    def pagina(termino, offset):
        r = http.post(api, json={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": termino},
                      headers={"Accept": "application/json"})
        return r.json()

    def recorrer(termino, primera=None):
        offset, d = 0, primera
        while offset < maximo:
            d = d or pagina(termino, offset)
            for j in d.get("jobPostings", []):
                path = j.get("externalPath", "")
                if path and path not in vistos:
                    vistos.add(path)
                    out.append({"titulo": j.get("title", ""), "url": f"https://{host}/{sitio}{path}",
                                "lugar": j.get("locationsText", ""), "fecha": j.get("postedOn", "")})
            offset += 20
            if offset >= d.get("total", 0):
                break
            d = None

    # Portal pequeño: se traen todas. Portal grande: solo los términos configurados.
    todo = pagina("", 0)
    if todo.get("total", 0) <= maximo or not cfg.get("terminos_portales_grandes"):
        recorrer("", todo)
    else:
        for termino in cfg["terminos_portales_grandes"]:
            recorrer(termino)
    return out


# ── Greenhouse ───────────────────────────────────────────────────────────────
def greenhouse(http, url, cfg):
    token = [x for x in urlparse(url).path.split("/") if x][0]
    d = http.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs").json()
    return [{"titulo": j["title"], "url": j["absolute_url"], "lugar": (j.get("location") or {}).get("name", ""),
             "fecha": (j.get("updated_at") or "")[:10]} for j in d.get("jobs", [])]


# ── Lever ────────────────────────────────────────────────────────────────────
def lever(http, url, cfg):
    empresa = [x for x in urlparse(url).path.split("/") if x][0]
    d = http.get(f"https://api.lever.co/v0/postings/{empresa}?mode=json").json()
    return [{"titulo": j["text"], "url": j["hostedUrl"], "lugar": (j.get("categories") or {}).get("location", ""),
             "fecha": ""} for j in d]


# ── Workable ─────────────────────────────────────────────────────────────────
def workable(http, url, cfg):
    cuenta = [x for x in urlparse(url).path.split("/") if x][0]
    d = http.get(f"https://apply.workable.com/api/v1/widget/accounts/{cuenta}").json()
    return [{"titulo": j["title"], "url": j.get("url") or f"https://apply.workable.com/{cuenta}/j/{j.get('shortcode')}/",
             "lugar": ", ".join(x for x in [j.get("city"), j.get("country")] if x),
             "fecha": j.get("published_on", "")} for j in d.get("jobs", [])]


# ── BambooHR ─────────────────────────────────────────────────────────────────
def bamboohr(http, url, cfg):
    host = urlparse(url).netloc
    d = http.get(f"https://{host}/careers/list", headers={"Accept": "application/json"}).json()
    out = []
    for j in d.get("result", []):
        loc = j.get("location") or {}
        out.append({"titulo": j.get("jobOpeningName", ""), "url": f"https://{host}/careers/{j.get('id')}",
                    "lugar": ", ".join(x for x in [loc.get("city"), loc.get("state")] if x) if isinstance(loc, dict) else "",
                    "fecha": ""})
    return out


# ── SmartRecruiters ─────────────────────────────────────────────────────────
def smartrecruiters(http, url, cfg):
    emp = [x for x in urlparse(url).path.split("/") if x][0]
    d = http.get(f"https://api.smartrecruiters.com/v1/companies/{emp}/postings?limit=100").json()
    return [{"titulo": j["name"], "url": f"https://jobs.smartrecruiters.com/{emp}/{j['id']}",
             "lugar": (j.get("location") or {}).get("city", ""), "fecha": (j.get("releasedDate") or "")[:10]}
            for j in d.get("content", [])]


# ── Recruitee ───────────────────────────────────────────────────────────────
def recruitee(http, url, cfg):
    host = urlparse(url).netloc
    d = http.get(f"https://{host}/api/offers/").json()
    return [{"titulo": j["title"], "url": j.get("careers_url", ""), "lugar": j.get("location", ""),
             "fecha": (j.get("published_at") or "")[:10]} for j in d.get("offers", [])]


# ── Personio ────────────────────────────────────────────────────────────────
def personio(http, url, cfg):
    host = urlparse(url).netloc
    root = ET.fromstring(http.get(f"https://{host}/xml").content)
    out = []
    for pos in root.iter("position"):
        pid = pos.findtext("id", "")
        out.append({"titulo": pos.findtext("name", ""), "url": f"https://{host}/job/{pid}",
                    "lugar": pos.findtext("office", ""), "fecha": (pos.findtext("createdAt") or "")[:10]})
    return out


# ── Breezy ──────────────────────────────────────────────────────────────────
def breezy(http, url, cfg):
    host = urlparse(url).netloc
    d = http.get(f"https://{host}/json").json()
    return [{"titulo": j["name"], "url": j["url"],
             "lugar": (j.get("location") or {}).get("name", "") if isinstance(j.get("location"), dict) else "",
             "fecha": (j.get("published_date") or "")[:10]} for j in d]


# ── ReliefWeb (vía RSS de la búsqueda) ──────────────────────────────────────
def reliefweb(http, url, cfg):
    p = urlparse(url)
    rss = f"https://reliefweb.int/jobs/rss.xml?{p.query}" if p.query else "https://reliefweb.int/jobs/rss.xml"
    root = ET.fromstring(http.get(rss).content)
    return [{"titulo": it.findtext("title", ""), "url": it.findtext("link", ""), "lugar": "",
             "fecha": it.findtext("pubDate", "")[:16]} for it in root.iter("item")]


LECTORES = {f.__name__: f for f in [workday, greenhouse, lever, workable, bamboohr, smartrecruiters,
                                     recruitee, personio, breezy, reliefweb]}


def leer(http, org: dict, cfg: dict) -> dict:
    """Lee una organización. Devuelve {estado, vacantes, huella, metodo, nota}."""
    url = org.get("j", "")
    tipo = tipo_portal(url)
    if tipo == "sin_enlace":
        return {"estado": "omitida", "nota": "Sin página de vacantes en el radar", "metodo": tipo}
    if tipo == "red_social":
        return {"estado": "omitida", "nota": "Red social o grupo (no se rastrea; revisar manualmente)", "metodo": tipo}
    if tipo in LECTORES:
        try:
            return {"estado": "ok", "vacantes": LECTORES[tipo](http, url, cfg), "metodo": tipo}
        except Exception as e:  # si la plataforma cambió su formato, cae al detector genérico
            nota = f"Lector {tipo} falló ({type(e).__name__}); se usó el detector genérico"
            res = leer_html(http, url)
            res["nota"] = (nota + ". " + res.get("nota", "")).strip()
            return res
    return leer_html(http, url)


def leer_html(http, url: str) -> dict:
    r = http.get(url)
    ctype = r.headers.get("content-type", "")
    if "html" not in ctype and "xml" not in ctype:
        return {"estado": "ok", "vacantes": [], "metodo": "html", "nota": f"La página no es HTML ({ctype})"}
    html = r.text
    vac = extraer_enlaces(html, r.url)
    res = {"estado": "ok", "vacantes": vac, "huella": huella_pagina(html), "metodo": "html"}
    if not vac and parece_js(html):
        res["requiere_js"] = True
    return res


def leer_render(http, url: str) -> dict:
    html = http.render(url)
    return {"estado": "ok", "vacantes": extraer_enlaces(html, url), "huella": huella_pagina(html), "metodo": "html+js"}
