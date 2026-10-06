"""Aviso opcional por correo cuando aparecen vacantes nuevas (configurado con variables de entorno)."""
from __future__ import annotations

import html
import os
import smtplib
from email.message import EmailMessage


def enviar(nuevas: list, resumen: dict, cfg: dict, log=print):
    host, usuario, clave = os.getenv("SMTP_HOST"), os.getenv("SMTP_USUARIO"), os.getenv("SMTP_CLAVE")
    para = os.getenv("CORREO_DESTINO") or cfg.get("correo_destino")
    if not (host and usuario and clave and para):
        return False
    if not nuevas and not cfg.get("correo_aunque_no_haya_nuevas", False):
        log("Sin vacantes nuevas: no se envía correo.")
        return False
    coinc = [x for x in nuevas if x[1].get("coincide")]
    otras = [x for x in nuevas if not x[1].get("coincide")]

    def items(lista):
        return "".join(
            f'<li><a href="{html.escape(v.get("url", ""))}">{html.escape(v["titulo"])}</a> · '
            f'<b>{html.escape(o["n"])}</b>{" · " + html.escape(v["lugar"]) if v.get("lugar") else ""}</li>'
            for o, v in lista[:60])

    url_reporte = cfg.get("url_reporte", "")
    cuerpo = f"""<div style="font-family:Arial,sans-serif;font-size:14px;color:#1C1812">
<h2 style="font-family:Georgia,serif;font-weight:normal">Vigía de vacantes · {html.escape(resumen['fecha'])}</h2>
<p><b>{resumen['nuevas_coinciden']}</b> vacantes nuevas coinciden con el perfil y <b>{resumen['nuevas']}</b> son nuevas en total.
{resumen['paginas_modificadas']} páginas cambiaron sin enlaces detectables.</p>
{'<h3>Coinciden con el perfil</h3><ul>' + items(coinc) + '</ul>' if coinc else ''}
{'<h3>Otras vacantes nuevas</h3><ul>' + items(otras) + '</ul>' if otras else ''}
{f'<p><a href="{html.escape(url_reporte)}">Ver el reporte completo</a></p>' if url_reporte else '<p>El reporte completo está en salida/reporte.html.</p>'}
</div>"""
    msg = EmailMessage()
    msg["Subject"] = f"Radar Progresso: {resumen['nuevas_coinciden']} vacantes nuevas para tu perfil ({resumen['nuevas']} en total)"
    msg["From"] = usuario
    msg["To"] = para
    msg.set_content("Abre este correo en un cliente que muestre HTML.")
    msg.add_alternative(cuerpo, subtype="html")
    puerto = int(os.getenv("SMTP_PUERTO", "587"))
    with smtplib.SMTP(host, puerto, timeout=30) as s:
        s.starttls()
        s.login(usuario, clave)
        s.send_message(msg)
    log(f"Correo enviado a {para}.")
    return True
