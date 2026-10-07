"""Prueba sin red: simula los sitios y corre el vigía dos veces para verificar que detecta lo nuevo."""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vigia import motor, reportes
from vigia.extraer import extraer_enlaces

class R:
    def __init__(self, url, body, ctype="text/html"):
        self.url, self.text, self.headers = url, body if isinstance(body, str) else json.dumps(body), {"content-type": ctype}
        self.content = self.text.encode()
    def json(self): return json.loads(self.text)

ESCENA = {}
class FakeHttp:
    def __init__(self, cfg): pass
    def get(self, url, **kw):
        if url not in ESCENA: raise ConnectionError("sin respuesta simulada para " + url)
        b = ESCENA[url]
        if isinstance(b, Exception): raise b
        return R(url, b, "application/json" if not isinstance(b, str) else ("text/xml" if b.startswith("<?xml") else "text/html"))
    def post(self, url, **kw):
        return R(url, ESCENA[url + "#" + kw["json"]["searchText"]], "application/json")
    def render(self, url): return ESCENA[url + "#js"]
    def cerrar(self): pass
motor.Http = FakeHttp

HTML1 = """<html><body><header><a href="/">Inicio</a><a href="/contacto">Contacto</a></header><main>
<h1>Convocatorias laborales</h1>
<div class="item"><h3>Coordinador(a) de Proyectos – Bogotá</h3><a href="/convocatorias/coordinador-proyectos.pdf">Descargar</a></div>
<div class="item"><h3>Oficial de Monitoreo y Evaluación (MEAL)</h3><a href="/convocatorias/oficial-meal?utm_source=x">Ver convocatoria</a></div>
<p>Texto institucional sobre la fundación y su misión en Colombia desde 1990. """ + "Lorem ipsum " * 80 + """</p>
<a href="/noticias/nuestro-director-en-foro">Leer más</a><a href="https://facebook.com/x">Facebook</a>
</main><footer><a href="/politica">Política de privacidad</a></footer></body></html>"""
HTML2 = HTML1.replace('<p>Texto', '<div class="item"><h3>Pasante de comunicaciones</h3><a href="/convocatorias/pasante">Ver</a></div><div class="item"><h4>Especialista en Sostenibilidad y ESG</h4><a href="/convocatorias/especialista-esg">Postular</a></div><p>Texto')
HTML1 = HTML1  # misma página base
PDFS1 = "<html><body><main><h1>Trabaja con nosotros</h1><p>Actualmente no hay procesos abiertos. " + "Información general. " * 60 + "</p></main></body></html>"
PDFS2 = PDFS1.replace("no hay procesos abiertos", "está abierto el proceso para auxiliar contable, envía tu hoja de vida al correo")
JSPAGE = "<html><head>" + "<script src='a.js'></script>" * 20 + "</head><body><div id='app'></div></body></html>"

def escena(n):
    ESCENA.clear()
    ESCENA["https://fundacion-a.org/trabaja"] = HTML1 if n == 1 else HTML2
    ESCENA["https://fundacion-b.org/empleo"] = PDFS1 if n == 1 else PDFS2
    ESCENA["https://spa.org/jobs"] = JSPAGE
    gh = {"jobs": [{"title": "Program Officer, LAC", "absolute_url": "https://job-boards.greenhouse.io/demo/jobs/1", "location": {"name": "Bogotá, Colombia"}, "updated_at": "2026-10-01"}]}
    if n == 2:
        gh["jobs"].append({"title": "Data Analyst", "absolute_url": "https://job-boards.greenhouse.io/demo/jobs/2", "location": {"name": "Nairobi"}, "updated_at": "2026-10-05"})
    ESCENA["https://boards-api.greenhouse.io/v1/boards/demo/jobs"] = gh
    api = "https://demo.wd1.myworkdayjobs.com/wday/cxs/demo/External/jobs"
    wd = [{"title": "Country Director - Colombia", "externalPath": "/job/Bogota/Country-Director_R1", "locationsText": "Bogotá", "postedOn": "Posted Today"}]
    if n == 2: wd = wd[1:]  # se cerró
    ESCENA[api + "#"] = {"total": 5000, "jobPostings": []}  # portal grande
    for t in ["Colombia", "Remote"]:
        ESCENA[api + "#" + t] = {"total": len(wd) if t == "Colombia" else 0, "jobPostings": wd if t == "Colombia" else []}
    bamboo = {"result": [{"id": 7, "jobOpeningName": "Gerente de Programas Colombia", "location": {"city": "Bogotá", "state": ""}}]}
    if n == 2: bamboo["result"].append({"id": 9, "jobOpeningName": "Coordinadora regional América Latina (remoto)", "location": {"city": "Remoto"}})
    ESCENA["https://demo.bamboohr.com/careers/list"] = bamboo
    ESCENA["https://caida.org/vacantes"] = ConnectionError("timeout simulado")
    lista = '<li><a href="https://intl.org/jobs/1">Finance Officer</a></li>'
    if n == 2:
        lista += '<li><a href="https://intl.org/jobs/2">Program Manager</a></li><li><a href="https://intl.org/jobs/3">Logistics Officer</a></li>'
    ESCENA["https://intl.org/jobs"] = "<html><body><main><h1>Jobs</h1><ul>" + lista + "</ul>" + "Texto " * 150 + "</main></body></html>"
    ESCENA["https://intl.org/jobs/2"] = "<html><body><main><h1>Program Manager</h1><p>Duty station: Bogotá, Colombia</p></main></body></html>"
    ESCENA["https://intl.org/jobs/3"] = "<html><body><main><h1>Logistics Officer</h1><p>Duty station: Juba, South Sudan</p></main></body></html>"

ORGS = [
    {"id": "fundacion-a", "n": "Fundación A", "j": "https://fundacion-a.org/trabaja", "t": "Filantropía", "afe": True},
    {"id": "fundacion-b", "n": "Fundación B", "j": "https://fundacion-b.org/empleo", "t": "Desarrollo Comunitario"},
    {"id": "spa", "n": "Org con JavaScript", "j": "https://spa.org/jobs", "t": "Humanitario"},
    {"id": "gh", "n": "Demo Greenhouse", "j": "https://job-boards.greenhouse.io/demo", "t": "Evaluación"},
    {"id": "wd", "n": "Demo Workday", "j": "https://demo.wd1.myworkdayjobs.com/en-US/External", "t": "ONU"},
    {"id": "bb", "n": "Demo BambooHR", "j": "https://demo.bamboohr.com/careers", "t": "Sostenibilidad"},
    {"id": "caida", "n": "Sitio caído", "j": "https://caida.org/vacantes", "t": "Salud"},
    {"id": "li", "n": "Solo LinkedIn", "j": "https://www.linkedin.com/company/x/jobs/", "t": "Cooperación"},
    {"id": "nada", "n": "Sin enlace", "j": "", "t": "Filantropía"},
    {"id": "intl", "n": "ONG internacional", "j": "https://intl.org/jobs", "t": "Humanitario"},
]
CFG = {"perfil": {"palabras_clave": ["Colombia", "remoto", "América Latina", "LAC", "ESG", "MEAL", "coordinador", "coordinadora"],
                  "excluir": ["pasante"]}, "terminos_portales_grandes": ["Colombia", "Remote"], "concurrencia": 4}

tmp = os.path.join(os.path.dirname(__file__), "_tmp")
shutil.rmtree(tmp, ignore_errors=True)
est = os.path.join(tmp, "estado.json")

print("== Extracción genérica (página 1) ==")
for v in extraer_enlaces(HTML1, "https://fundacion-a.org/trabaja"): print("  ", v)

escena(1); e1 = motor.correr(CFG, ORGS, est, log=lambda *a: None); o1 = reportes.generar(e1, ORGS, tmp, CFG)
print("\n== Corrida 1 ==", {k: e1["corridas"][-1][k] for k in ("ok", "errores", "omitidas", "linea_base", "nuevas")})
escena(2); e2 = motor.correr(CFG, ORGS, est, log=lambda *a: None); o2 = reportes.generar(e2, ORGS, tmp, CFG)
r = e2["corridas"][-1]
print("== Corrida 2 ==", {k: r[k] for k in ("ok", "errores", "nuevas", "nuevas_coinciden", "fuera_ubicacion", "fichas_abiertas", "fichas_rescatadas", "cerradas", "paginas_modificadas")})
for o, v in o2["nuevas"]: print("   NUEVA:", o["n"], "|", v["titulo"], "| coincide:", v["coincide"])
for oid, e in e2["orgs"].items(): print(f"   {oid:12} {e['estado']:9} {e.get('metodo',''):10} js={e.get('requiere_js')} nota={e.get('nota','')[:60]}")

assert r["nuevas"] == 3, r                       # ESG (org. colombiana), Coordinadora remota y Program Manager (ficha: Bogotá)
assert r["fuera_ubicacion"] == 2, r              # Data Analyst en Nairobi y Logistics Officer (ficha: Juba)
assert r["fichas_abiertas"] == 2 and r["fichas_rescatadas"] == 1, r
assert r["nuevas_coinciden"] == 3, r
assert r["cerradas"] == 1, r                     # Country Director
assert r["paginas_modificadas"] >= 1, r          # Fundación B cambió sin enlaces
assert e2["orgs"]["spa"]["requiere_js"] is True
assert e2["orgs"]["caida"]["estado"] == "error"
rad = json.load(open(os.path.join(tmp, "radar_vacantes.json")))
assert rad["orgs"]["fundacion-a"]["nuevas"][0]["t"].startswith("Especialista")
print("\nTodo OK. Archivos en", tmp, os.listdir(tmp))
