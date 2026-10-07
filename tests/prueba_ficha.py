"""Segunda mirada: la ficha de la vacante dice dónde es el cargo."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vigia import ubicacion as ub
from vigia.ficha import leer_ficha, ubicacion_desde_ficha

class R:
    def __init__(s, t): s.text, s.headers = t, {"content-type": "text/html"}
class H:
    def __init__(s, pages): s.p = pages
    def get(s, url, **k): return R(s.p[url])

P = {
 "a": "<html><body><header>Oficinas: Nairobi, Bogotá, Ginebra</header><main><h1>Program Officer</h1><p>Duty Station: Bogota, Colombia</p><p>The officer will support programmes in Kenya.</p></main><footer>Geneva HQ</footer></body></html>",
 "b": "<html><body><main><h1>Oficial de Proyectos</h1><ul><li>Ubicación: Quito, Ecuador</li><li>Tipo de contrato: fijo</li></ul></main></body></html>",
 "c": "<html><body><main><h1>Consultor/a</h1><p>Modalidad: Remoto</p></main></body></html>",
 "d": '<html><head><script type="application/ld+json">{"@type":"JobPosting","jobLocation":{"address":{"addressLocality":"Medellín","addressCountry":"CO"}}}</script></head><body><main><h1>Coordinador</h1></main></body></html>',
 "e": "<html><body><main><h1>Finance Manager</h1><p>We are looking for a finance manager to join our team.</p></main></body></html>",
 "f": "<html><body><main><h1>Especialista MEL</h1><p>Lugar de trabajo: Tumaco (Nariño), con desplazamientos.</p></main></body></html>",
 "g": "<html><body><main><h1>Oficial</h1><p>Location: Armenia (Yerevan)</p></main></body></html>",
}
esperado = {"a": "colombia", "b": "otro", "c": "remoto", "d": "colombia", "e": "sin_dato", "f": "colombia", "g": "otro"}
reglas = ub.construir({})
h = H(P)
for k, exp in esperado.items():
    f = leer_ficha(h, k)
    u = ubicacion_desde_ficha(f, reglas)
    print(f"{'OK ' if u == exp else 'MAL'} {k} {u:10} lugar='{f['lugar']}'")
    assert u == exp, (k, u, f)
assert leer_ficha(h, "https://x.org/tdr.pdf") == {"lugar": "", "texto": ""}
# municipios y capitales ambiguas
casos = [("Docente - Armenia, Quindío", "colombia"), ("Oficial de país - Armenia", "otro"),
         ("Técnico de campo en Pasto, Nariño", "colombia"), ("Manejo de pasto y ganadería", "sin_dato"),
         ("Pasante en Florencia, Italia", "otro"), ("Asesor Caucasia y El Bagre", "colombia"),
         ("Líder técnico - Fundación Pacífico", "sin_dato"), ("Coordinador Barrancabermeja", "colombia")]
intl = {"n": "X", "j": "https://x.org/jobs", "t": "Humanitario"}
for t, exp in casos:
    u = ub.clasificar({"titulo": t}, intl, reglas)
    print(f"{'OK ' if u == exp else 'MAL'} {u:10} {t}")
    assert u == exp, (t, u)
print("Todo OK")
