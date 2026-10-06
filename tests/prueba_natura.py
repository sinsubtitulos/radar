"""Caso real (estructura de natura.org.co, sep-2026): tarjetas de WordPress donde el enlace envuelve título, resumen y fecha."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vigia.extraer import extraer_enlaces
HTML = open(os.path.join(os.path.dirname(__file__), "natura_convocatorias.html"), encoding="utf-8").read()
vs = extraer_enlaces(HTML, "https://natura.org.co/category/convocatorias/convocatorias/")
for v in vs: print(" ", v["titulo"], "→", v["url"])
titulos = [v["titulo"] for v in vs]
assert "Convocatoria Especialista en hidrología" in titulos
assert "Convocatoria Especialista en geotecnia" in titulos
assert any("Supervisor HSE" in t for t in titulos)
assert not any("cacaoteras" in t for t in titulos)   # noticia, no vacante
assert not any(t in ("Convocatorias", "Voluntariados", "Equipo de trabajo") for t in titulos)
print("OK:", len(vs), "vacantes detectadas")
