"""Detector genérico: encuentra enlaces que parecen vacantes o convocatorias en una página HTML."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

from bs4 import BeautifulSoup


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


# Palabras que indican un cargo o una convocatoria (texto ya normalizado sin tildes)
CARGO = re.compile(
    r"\b(coordinador|coordinadora|coordinacion|oficial|asesor|asesora|consultor|consultora|consultoria|"
    r"especialista|analista|director|directora|direccion|gerente|jefe|jefa|lider|profesional|tecnico|tecnica|"
    r"asistente|auxiliar|administrador|administradora|contador|contadora|promotor|promotora|facilitador|facilitadora|"
    r"psicologo|psicologa|abogado|abogada|ingeniero|ingeniera|investigador|investigadora|docente|enfermero|enfermera|medico|"
    r"monitor|monitora|gestor|gestora|ejecutivo|ejecutiva|representante|delegado|delegada|"
    r"pasante|pasantia|practicante|voluntario|voluntaria|"
    r"manager|officer|coordinator|specialist|advisor|adviser|consultant|consultancy|director|analyst|associate|"
    r"assistant|lead|head of|intern|internship|fellow|fellowship|researcher|expert|engineer|representative|"
    r"terminos de referencia|tdr|convocatoria|vacante|vacancy|position|job opening|call for|expresion de interes)\b"
)
# Pistas en la dirección del enlace
URL_PISTA = re.compile(
    r"(/jobs?/|/job-|/vacante|/vacancy|/vacancies/|/convocatoria|/oferta|/empleo/|/position|/posting|/opportunit|"
    r"/careers?/[^/]+|/trabaj|/consultor|/tdr|/terminos|jobid=|job_id=|requisition|/apply/|\.pdf$)", re.I)
# Textos de navegación que nunca son vacantes
RUIDO = re.compile(
    r"^(inicio|home|contacto|contact|nosotros|about|quienes somos|blog|noticias|news|prensa|donar|donate|dona|"
    r"suscribete|subscribe|iniciar sesion|login|log in|sign in|registr|politica|privacy|privacidad|terminos y condiciones|"
    r"cookies|mapa del sitio|ver mas|leer mas|read more|mas informacion|more|siguiente|anterior|next|previous|"
    r"trabaja con nosotros|work with us|careers|empleo|vacantes|convocatorias|oportunidades|jobs|join us|"
    r"facebook|twitter|instagram|linkedin|youtube|tiktok|whatsapp|x)$")
REDES = re.compile(r"(facebook|twitter|x\.com|instagram|linkedin|youtube|tiktok|wa\.me|whatsapp|mailto:|tel:)", re.I)
RASTREO = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "ref", "source"}


def limpiar_url(u: str) -> str:
    p = urlparse(u)
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in RASTREO]
    return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/") or "/", "", urlencode(q), ""))


def texto_visible(soup: BeautifulSoup) -> str:
    for t in soup(["script", "style", "noscript", "header", "footer", "nav", "svg", "form"]):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def huella_pagina(html: str) -> str:
    """Huella del contenido principal, sin fechas ni números que cambian solos."""
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body or soup
    txt = norm(texto_visible(main))
    txt = re.sub(r"\d+", "#", txt)
    return hashlib.sha1(txt.encode()).hexdigest()[:16]


def parece_js(html: str) -> bool:
    """La página casi no trae texto: probablemente carga las vacantes con JavaScript."""
    soup = BeautifulSoup(html, "lxml")
    n_scripts = len(soup.find_all("script"))
    txt = texto_visible(soup)
    return len(txt) < 600 or (n_scripts > 15 and len(txt) < 1500)


def extraer_enlaces(html: str, url_base: str) -> list[dict]:
    """Devuelve [{titulo, url}] de los enlaces con pinta de vacante."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["header", "footer", "nav", "script", "style", "noscript"]):
        t.decompose()
    base_host = urlparse(url_base).netloc.lower().removeprefix("www.")
    pagina = limpiar_url(url_base)
    vistos, out = set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:")) or REDES.search(href):
            continue
        url = limpiar_url(urljoin(url_base, href))
        if url == pagina or not url.startswith("http"):
            continue
        # si el enlace envuelve una tarjeta (título + resumen + fecha), usa el título de la tarjeta
        h_in = a.find(["h1", "h2", "h3", "h4", "h5", "h6"]) or a.find(class_=re.compile(r"title|titulo", re.I))
        titulo = (re.sub(r"\s+", " ", h_in.get_text(" ")).strip() if h_in and h_in.get_text(strip=True)
                  else re.sub(r"\s+", " ", a.get_text(" ")).strip() or (a.get("title") or "").strip())
        # si el enlace es genérico ("Ver más", "Descargar"), usa el título del bloque que lo contiene
        if len(titulo) < 6 or RUIDO.match(norm(titulo)) or norm(titulo) in {"descargar", "download", "aplicar", "apply", "postular", "ver", "aqui", "click aqui", "ver convocatoria", "ver vacante"}:
            bloque = a.find_parent(["article", "li", "tr", "div"])
            h = bloque.find(["h1", "h2", "h3", "h4", "h5", "strong"]) if bloque else None
            if h and h.get_text(strip=True):
                titulo = re.sub(r"\s+", " ", h.get_text(" ")).strip()
        nt = norm(titulo)
        if not (6 <= len(titulo) <= 220) or RUIDO.match(nt):
            continue
        host = urlparse(url).netloc.lower().removeprefix("www.")
        puntos = 0
        if CARGO.search(nt):
            puntos += 2
        if URL_PISTA.search(url):
            puntos += 1
        if host == base_host or host.endswith("." + base_host):
            puntos += 0.5
        if puntos < 2:  # exige palabra de cargo, o pista de URL + mismo sitio + algo más
            continue
        if url in vistos:
            continue
        vistos.add(url)
        out.append({"titulo": titulo[:200], "url": url})
    return out


def clave(v: dict) -> str:
    return hashlib.sha1((v.get("url") or norm(v.get("titulo", ""))).encode()).hexdigest()[:16]
