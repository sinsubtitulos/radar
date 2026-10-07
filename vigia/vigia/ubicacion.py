"""Clasifica la ubicación de una vacante: Colombia, remoto, otro lugar o sin dato."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .extraer import norm

COLOMBIA = [
    # país y gentilicios
    "colombia", "colombian", "colombiano", "colombiana",
    # las 32 capitales de departamento + Bogotá (Armenia, Florencia y Pasto llevan su departamento al lado,
    # porque también son un país, una ciudad italiana y una palabra común)
    "bogota", "medellin", "cali", "barranquilla", "cartagena", "cucuta", "bucaramanga", "pereira", "santa marta",
    "ibague", "villavicencio", "manizales", "neiva", "valledupar", "monteria", "popayan", "sincelejo", "tunja",
    "riohacha", "quibdo", "yopal", "mocoa", "leticia", "arauca", "san andres", "inirida", "mitu", "puerto carreno",
    "san jose del guaviare", "armenia quindio", "armenia, quindio", "armenia (quindio)", "florencia caqueta",
    "florencia, caqueta", "florencia (caqueta)", "pasto narino", "pasto, narino", "pasto (narino)", "ciudad de pasto",
    "san juan de pasto",
    # departamentos y regiones sin doble sentido
    "antioquia", "atlantico", "cauca", "valle del cauca", "narino", "putumayo", "guaviare", "caqueta", "la guajira",
    "norte de santander", "santander", "huila", "tolima", "boyaca", "cundinamarca", "risaralda", "caldas", "quindio",
    "vichada", "vaupes", "guainia", "casanare", "choco", "uraba", "catatumbo", "magdalena medio", "bajo cauca",
    "montes de maria", "sierra nevada de santa marta", "eje cafetero", "pacifico colombiano", "caribe colombiano",
    # municipios sin doble sentido
    "soacha", "envigado", "itagui", "rionegro", "marinilla", "carmen de viboral", "yarumal", "caucasia", "el bagre",
    "ituango", "dabeiba", "frontino", "santa rosa de osos", "apartado antioquia", "chigorodo", "necocli",
    "tulua", "jamundi", "yumbo", "buenaventura", "palmira valle", "guacari",
    "barrancabermeja", "piedecuesta", "floridablanca", "giron santander", "san gil",
    "ocana", "tibu", "el tarra", "sardinata", "teorama", "hacari", "villa del rosario", "chinacota",
    "zipaquira", "fusagasuga", "facatativa", "girardot", "mosquera cundinamarca", "funza",
    "duitama", "sogamoso", "chiquinquira", "puerto boyaca",
    "maicao", "uribia", "manaure", "san juan del cesar", "aguachica", "magangue", "mompox", "mompos",
    "el carmen de bolivar", "turbaco", "sabanalarga", "malambo", "zona bananera",
    "tierralta", "montelibano", "planeta rica", "lorica",
    "tumaco", "ipiales", "tuquerres", "guapi", "timbiqui", "lopez de micay", "istmina", "riosucio choco",
    "puerto asis", "orito", "puerto leguizamo", "valle del guamuez", "san vicente del caguan", "puerto gaitan",
    "saravena", "arauquita", "la dorada", "chaparral tolima", "pitalito", "garzon huila",
]
REMOTO = [
    "remoto", "remota", "remote", "home based", "home-based", "homebased", "teletrabajo", "trabajo en casa",
    "desde casa", "work from home", "wfh", "anywhere", "modalidad virtual", "100% virtual", "telework", "teletrabajable",
]
# Lugares que, si aparecen sin mención a Colombia ni a remoto, indican que la vacante es en otro sitio
OTROS = [
    "peru", "lima", "ecuador", "quito", "guayaquil", "venezuela", "caracas", "bolivia", "potosi",
    "tarija", "chuquisaca", "mexico", "ciudad de mexico", "guatemala", "honduras", "tegucigalpa", "el salvador",
    "san salvador", "nicaragua", "managua", "costa rica", "panama", "argentina", "buenos aires",
    "chile", "brasil", "brazil", "sao paulo", "paraguay", "asuncion", "uruguay", "montevideo", "haiti",
    "republica dominicana", "dominican republic", "cuba", "puerto rico", "jamaica",
    "espana", "spain", "madrid", "barcelona", "a coruna", "francia", "france", "paris", "uk", "united kingdom",
    "london", "londres", "germany", "alemania", "berlin", "netherlands", "the hague", "geneva", "ginebra",
    "switzerland", "brussels", "bruselas", "italy", "rome", "roma", "usa", "united states", "us", "u s", "washington",
    "new york", "nueva york", "florida", "canada", "toronto", "ottawa", "kenya", "nairobi", "uganda", "ethiopia",
    "nigeria", "south sudan", "sudan", "somalia", "congo", "dr congo", "malawi", "sierra leone", "liberia",
    "mozambique", "tanzania", "rwanda", "senegal", "dakar", "jordan", "syria", "lebanon", "iraq", "yemen",
    "afghanistan", "pakistan", "bangladesh", "india", "nepal", "philippines", "indonesia", "myanmar", "ukraine",
    "kyiv", "bangkok", "thailand", "turkey", "egypt", "cairo", "amman", "beirut",
    "italia", "florencia", "florence", "suiza", "suecia", "sweden", "stockholm", "noruega", "norway", "oslo",
    "dinamarca", "denmark", "copenhagen", "holanda", "paises bajos", "belgica", "belgium", "reino unido",
    "estados unidos", "eeuu", "eua", "armenia", "yerevan", "portugal", "lisboa", "lisbon", "irlanda", "ireland",
    "dublin", "austria", "vienna", "viena", "japon", "japan", "china", "australia", "sudafrica", "south africa",
]


REGION = re.compile(r"\b(latam|latin america|america latina|latinoamerica|lac|americas|las americas|global|worldwide|anywhere|south america|sudamerica)\b")


def _rx(lista):
    return re.compile(r"\b(" + "|".join(re.escape(x) for x in sorted(lista, key=len, reverse=True)) + r")\b")


def construir(cfg: dict):
    u = cfg.get("ubicacion") or {}
    col = _rx(COLOMBIA + [norm(x) for x in u.get("terminos_colombia_extra") or []])
    rem = _rx(REMOTO + [norm(x) for x in u.get("terminos_remoto_extra") or []])
    otr = _rx(OTROS)
    permitidas = set(u.get("permitidas") or ["colombia", "remoto"])
    asumir = u.get("asumir_colombia_en_organizaciones_colombianas", True)
    return col, rem, otr, permitidas, asumir


ATS = ("lever.co", "greenhouse.io", "workable.com", "bamboohr.com", "myworkdayjobs.com", "breezy.hr",
       "personio", "smartrecruiters.com", "recruitee.com", "teamtailor.com")


def es_org_colombiana(org: dict) -> bool:
    """Organización cuya página de vacantes publica solo cargos en Colombia.
    Se asume para la Red AFE, la categoría Filantropía, los sitios .co y las páginas de vacantes cuya
    dirección incluye «colombia» (p. ej. carecolombiaong.org, colombia.unfpa.org); para otras se puede marcar
    a mano con "pais": "CO" en organizaciones.json. Las oficinas de país que publican en el portal
    global de su organización (p. ej. UNICEF Colombia) NO se asumen colombianas."""
    if org.get("pais"):
        return str(org["pais"]).upper() in ("CO", "COL", "COLOMBIA")
    if org.get("afe") or org.get("t") == "Filantropía":
        return True
    p = urlparse((org.get("j") or "").lower())
    host = p.netloc
    if any(a in host for a in ATS):
        return False
    return (host.endswith(".co") or host.startswith("co.") or "colombia" in host or "/colombia" in p.path
            or any(x in host for x in (".com.co", ".org.co", ".gov.co", ".edu.co", ".net.co")))


def clasificar(v: dict, org: dict, reglas) -> str:
    """Devuelve 'colombia', 'remoto', 'colombia_supuesta', 'otro' o 'sin_dato'."""
    col, rem, otr, _, asumir = reglas
    lugar = norm(v.get("lugar", ""))
    texto = norm(f"{v.get('titulo', '')} {v.get('lugar', '')} {v.get('contexto', '')}")
    texto = texto.replace("remote sensing", " ")
    if rem.search(texto):
        # "Remote - US" o "remoto desde España": remoto pero restringido a otro país
        if otr.search(texto) and not col.search(texto) and not REGION.search(texto):
            return "otro"
        return "remoto"
    if col.search(texto):
        return "colombia"
    if otr.search(lugar) or otr.search(texto):
        return "otro"
    if lugar:  # la plataforma dio un lugar que no es Colombia ni remoto
        return "otro"
    if asumir and es_org_colombiana(org):
        return "colombia_supuesta"
    return "sin_dato"


def permitida(ubic: str, reglas) -> bool:
    permitidas = reglas[3]
    if ubic == "colombia_supuesta":
        return "colombia" in permitidas
    return ubic in permitidas
