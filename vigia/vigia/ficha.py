"""Segunda mirada: abre la página de una vacante nueva sin ubicación y busca dónde es el cargo."""
from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup

from .extraer import norm, texto_visible

# Etiquetas típicas del campo de ubicación en una ficha de vacante
ETIQUETA = re.compile(
    r"(?:ubicacion|lugar de trabajo|lugar de ejecucion|lugar|sede|ciudad|municipio|pais|location|locations|"
    r"duty station|place of work|work location|based in|country|city|region|modalidad)"
    r"\s*(?:del cargo|de trabajo|de la vacante)?\s*[:\-–]\s*(.{2,90}?)(?=\s{2,}|\s[A-Z][a-z]+:|\.|\||$)",
    re.I)


def leer_ficha(http, url: str, max_chars: int = 200_000) -> dict:
    """Devuelve {"lugar": texto de la etiqueta de ubicación o "", "texto": inicio del contenido principal}."""
    if re.search(r"\.(pdf|docx?|xlsx?)(\?|$)", url, re.I):
        return {"lugar": "", "texto": ""}
    r = http.get(url)
    if "html" not in r.headers.get("content-type", "html"):
        return {"lugar": "", "texto": ""}
    soup = BeautifulSoup(r.text[:max_chars], "lxml")
    main = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"}) or soup.body or soup
    txt = texto_visible(main)
    # 1) campos estructurados (schema.org JobPosting)
    lugares = []
    for s in soup.find_all("script", type="application/ld+json"):
        t = s.string or ""
        for m in re.finditer(r'"(?:addressLocality|addressRegion|addressCountry|jobLocationType)"\s*:\s*"([^"]{2,60})"', t):
            lugares.append(m.group(1))
    # 2) etiquetas en el texto ("Ubicación: Bogotá", "Duty station: Nairobi")
    plano = unicodedata.normalize("NFKD", txt[:6000]).encode("ascii", "ignore").decode()
    for m in ETIQUETA.finditer(plano):
        lugares.append(m.group(1).strip())
        if len(lugares) >= 4:
            break
    return {"lugar": " · ".join(dict.fromkeys(lugares))[:160], "texto": txt[:1500]}


def ubicacion_desde_ficha(ficha: dict, reglas) -> str:
    """Clasifica con prioridad al campo de ubicación; si no hay, usa el inicio del texto solo cuando es inequívoco."""
    col, rem, otr = reglas[0], reglas[1], reglas[2]
    lugar = norm(ficha.get("lugar", ""))
    if lugar:
        if rem.search(lugar) or "telecommut" in lugar:
            return "remoto" if not (otr.search(lugar) and not col.search(lugar)) else "otro"
        if col.search(lugar):
            return "colombia"
        # la ficha trae un lugar explícito que no es Colombia ni remoto: es en otro sitio
        return "otro"
    texto = norm(ficha.get("texto", "")).replace("remote sensing", " ")
    c, r, o = bool(col.search(texto)), bool(rem.search(texto)), bool(otr.search(texto))
    if c and not o:
        return "colombia"
    if r and not o and not c:
        return "remoto"
    if o and not c and not r:
        return "otro"
    return "sin_dato"
