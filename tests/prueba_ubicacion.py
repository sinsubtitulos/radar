"""Filtro de ubicación: solo Colombia o remoto."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vigia import ubicacion as ub
from vigia.extraer import extraer_enlaces
R = ub.construir({})
intl = {"id": "x", "n": "Ayuda en Acción", "j": "https://empleoayudaenaccion.talentclue.com/es/x", "t": "Desarrollo Económico"}
col = {"id": "y", "n": "Fundación Corona", "j": "https://www.fundacioncorona.org/trabaja", "t": "Filantropía", "afe": True}
co_tld = {"id": "z", "n": "Alianza Educativa", "j": "https://alianzaeducativa.edu.co/postulate/", "t": "Educación"}
casos = [
    ({"titulo": "Coordinador(a) de Proyectos - Línea de Educación (Lima)"}, intl, "otro"),
    ({"titulo": "Orientador/a Vocacional - A Coruña"}, intl, "otro"),
    ({"titulo": "Técnico de campo – Norte de Santander"}, intl, "colombia"),
    ({"titulo": "Program Officer", "lugar": "Bogotá, Colombia"}, intl, "colombia"),
    ({"titulo": "Data Analyst", "lugar": "Nairobi"}, intl, "otro"),
    ({"titulo": "Senior Manager", "lugar": "2 Locations"}, intl, "otro"),
    ({"titulo": "Regional Advisor (Remote, LATAM)"}, intl, "remoto"),
    ({"titulo": "Head of People & Culture"}, intl, "sin_dato"),
    ({"titulo": "Gerente de proyectos"}, col, "colombia_supuesta"),
    ({"titulo": "Docente de matemáticas"}, co_tld, "colombia_supuesta"),
    ({"titulo": "Oficial de construcción de la paz"}, co_tld, "colombia_supuesta"),
    ({"titulo": "Business Analyst (Remote - US)"}, intl, "otro"),
    ({"titulo": "Remote Sensing Data Engineer"}, intl, "sin_dato"),
    ({"titulo": "Program Lead (Remote, Latin America)"}, intl, "remoto"),
    ({"titulo": "KREASI Grant Finance Coordinator"}, {"n": "Save the Children Colombia", "j": "https://www.savethechildren.net/careers/apply", "t": "Niñez"}, "sin_dato"),
    ({"titulo": "Coordinación de Alianzas con el Sector Privado"}, {"n": "CARE Colombia", "j": "https://carecolombiaong.org/vacantes/", "t": "Humanitario"}, "colombia_supuesta"),
    ({"titulo": "Knowledge Officer"}, {"n": "UNICEF Colombia", "j": "https://jobs.unicef.org/cw/en-us/listing/", "t": "ONU"}, "sin_dato"),
    ({"titulo": "Consultor/a", "contexto": "Consultor/a · Modalidad: teletrabajo · Cierre 20/10"}, intl, "remoto"),
]
for v, o, esperado in casos:
    r = ub.clasificar(v, o, R)
    print(f"{'OK ' if r == esperado else 'MAL'} {r:18} {v['titulo']}")
    assert r == esperado
assert ub.permitida("colombia_supuesta", R) and ub.permitida("remoto", R) and not ub.permitida("sin_dato", R)
# contexto desde HTML
h = """<html><body><main><ul><li><a href="/jobs/1">Especialista en monitoreo</a> <span>Ubicación: Cúcuta</span></li>
<li><a href="/jobs/2">Especialista en monitoreo</a> <span>Ubicación: Quito, Ecuador</span></li></ul></main></body></html>"""
vs = extraer_enlaces(h, "https://org.int/jobs")
r = [ub.clasificar(v, intl, R) for v in vs]
print(r); assert r == ["colombia", "otro"]
print("Todo OK")
