"""Filtro corporativo: en portales de empresa solo cuentan cargos de fundación, social o sostenibilidad."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vigia.motor import clasificar, filtro_de
from vigia import ubicacion as ub
org = {"id": "f", "n": "Fundación Grupo Argos", "j": "https://jobs.grupoargos.com/", "t": "Filantropía", "afe": True, "filtro": "corporativo"}
R = ub.construir({}); F = filtro_de(org, {})
casos = [("Analista de Gestión Social - Medellín", False), ("Coordinador de Sostenibilidad", False),
         ("Profesional Fundación Grupo Argos", False), ("Líder de relacionamiento con comunidades", False),
         ("Operario de planta", True), ("Vendedor TAT Bogotá", True), ("Ingeniero de mantenimiento", True)]
for t, excl in casos:
    v = clasificar({"titulo": t}, {}, org, R, F)
    print(f"{'OK ' if v['excluida'] == excl else 'MAL'} excluida={v['excluida']!s:5} {t}")
    assert v["excluida"] == excl
for t, excl in [("Especialista en Cambio Climático", False), ("Analista de Economía Circular y Residuos", False),
                ("Líder de Descarbonización", False), ("Profesional de Reporte de Sostenibilidad (GRI)", False),
                ("Sustainability Manager", False), ("Coordinador de Energías Renovables", False),
                ("Analista de Clima Organizacional", True), ("Jefe de Producción", True)]:
    v = clasificar({"titulo": t}, {}, org, R, F)
    print(f"{'OK ' if v['excluida'] == excl else 'MAL'} excluida={v['excluida']!s:5} {t}")
    assert v["excluida"] == excl
assert filtro_de({"filtro": None}, {}) == []
jnj = {"id": "johnson-johnson", "n": "Johnson & Johnson", "j": "https://www.careers.jnj.com/en/jobs/?country=Colombia", "t": "Salud", "pais": "CO", "filtro": "asuntos_publicos"}
FJ = filtro_de(jnj, {})
for t, excl in [("Public Affairs Manager - Colombia", False), ("Market Access Lead, Andean Region", False),
                ("Gerente de Asuntos Corporativos", False), ("Global Health Equity Specialist", False),
                ("Sales Representative - Oncology", True), ("Supply Chain Planner", True), ("Analista de Facturación", True)]:
    v = clasificar({"titulo": t}, {}, jnj, R, FJ)
    print(f"{'OK ' if v['excluida'] == excl else 'MAL'} excluida={v['excluida']!s:5} J&J: {t}")
    assert v["excluida"] == excl
print("Todo OK")
