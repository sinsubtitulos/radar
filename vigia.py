#!/usr/bin/env python3
"""Vigía de vacantes · Radar Progresso

Uso:
  python vigia.py                    # revisa todas las organizaciones del radar
  python vigia.py --solo fhi-360,unicef-colombia   # solo algunas (ids del radar)
  python vigia.py --categoria ONU --limite 20      # pruebas rápidas
"""
import argparse
import json
import os
import sys

import yaml

from vigia import aviso, motor, reportes

AQUI = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description="Detecta vacantes nuevas en las páginas del Radar Progresso.")
    ap.add_argument("--config", default=os.path.join(AQUI, "config.yaml"))
    ap.add_argument("--orgs", default=os.path.join(AQUI, "organizaciones.json"))
    ap.add_argument("--estado", default=os.path.join(AQUI, "datos", "estado.json"))
    ap.add_argument("--salida", default=os.path.join(AQUI, "salida"))
    ap.add_argument("--solo", help="ids separados por coma")
    ap.add_argument("--categoria", help="solo una categoría del radar (ej.: ONU, Filantropía)")
    ap.add_argument("--limite", type=int, help="máximo de organizaciones (para pruebas)")
    ap.add_argument("--sin-correo", action="store_true")
    a = ap.parse_args()

    with open(a.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    with open(a.orgs, encoding="utf-8") as f:
        orgs = json.load(f)
    orgs += cfg.get("organizaciones_extra") or []

    sel = orgs
    if a.solo:
        ids = {x.strip() for x in a.solo.split(",")}
        sel = [o for o in sel if o["id"] in ids]
    if a.categoria:
        sel = [o for o in sel if o.get("t", "").lower() == a.categoria.lower()]
    if a.limite:
        sel = sel[: a.limite]
    if not sel:
        sys.exit("No hay organizaciones que coincidan con el filtro.")

    estado = motor.correr(cfg, sel, a.estado)
    out = reportes.generar(estado, orgs, a.salida, cfg)
    print(f"Reporte: {os.path.join(a.salida, 'reporte.html')}")
    if not a.sin_correo:
        try:
            aviso.enviar(out["nuevas"], out["resumen"], cfg)
        except Exception as e:  # el correo nunca debe romper la corrida
            print(f"No se pudo enviar el correo: {e}")


if __name__ == "__main__":
    main()
