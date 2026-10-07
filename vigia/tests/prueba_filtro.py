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
assert filtro_de({"filtro": None}, {}) == []
print("Todo OK")
