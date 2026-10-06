"""Cliente HTTP respetuoso: robots.txt, pausa por dominio, reintentos y render opcional con navegador."""
from __future__ import annotations

import threading
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

UA = "ProgressoRadarVigia/1.0 (+monitoreo de vacantes publicas; contacto en config.yaml)"


class Bloqueada(Exception):
    """La página no se puede rastrear (robots.txt o red social)."""


class Http:
    def __init__(self, cfg: dict):
        self.timeout = cfg.get("timeout_segundos", 25)
        self.pausa = cfg.get("pausa_por_dominio_segundos", 2.0)
        self.respetar_robots = cfg.get("respetar_robots_txt", True)
        contacto = cfg.get("contacto", "")
        self.ua = UA.replace("contacto en config.yaml", contacto) if contacto else UA
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": self.ua,
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        })
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._ultimo: dict[str, float] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._glock = threading.Lock()
        self._render = None  # navegador perezoso
        self.render_js = cfg.get("render_js", False)

    # ── cortesía ─────────────────────────────────────────────────────────────
    def _lock(self, host: str) -> threading.Lock:
        with self._glock:
            return self._locks.setdefault(host, threading.Lock())

    def _esperar(self, host: str):
        dt = time.time() - self._ultimo.get(host, 0)
        if dt < self.pausa:
            time.sleep(self.pausa - dt)
        self._ultimo[host] = time.time()

    def permitido(self, url: str) -> bool:
        if not self.respetar_robots:
            return True
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.s.get(base + "/robots.txt", timeout=10)
                if r.status_code == 200 and "text" in r.headers.get("content-type", "text"):
                    rp.parse(r.text.splitlines())
                else:  # sin robots.txt => permitido
                    rp = None
            except requests.RequestException:
                rp = None
            self._robots[base] = rp
        rp = self._robots[base]
        return True if rp is None else rp.can_fetch(self.ua, url)

    # ── peticiones ───────────────────────────────────────────────────────────
    def get(self, url: str, **kw) -> requests.Response:
        return self._req("GET", url, **kw)

    def post(self, url: str, **kw) -> requests.Response:
        return self._req("POST", url, **kw)

    def _req(self, method: str, url: str, **kw) -> requests.Response:
        if not self.permitido(url):
            raise Bloqueada("robots.txt no permite rastrear esta página")
        host = urlparse(url).netloc
        ultimo_error = None
        for intento in range(3):
            with self._lock(host):
                self._esperar(host)
                try:
                    r = self.s.request(method, url, timeout=self.timeout, **kw)
                except requests.RequestException as e:
                    ultimo_error = e
                    r = None
            if r is not None:
                if r.status_code in (429, 502, 503, 504) and intento < 2:
                    time.sleep(5 * (intento + 1))
                    continue
                r.raise_for_status()
                return r
            time.sleep(3 * (intento + 1))
        raise ultimo_error  # type: ignore[misc]

    # ── render con navegador (páginas que cargan vacantes con JavaScript) ───
    def render(self, url: str) -> str:
        if not self.permitido(url):
            raise Bloqueada("robots.txt no permite rastrear esta página")
        if self._render is None:
            from playwright.sync_api import sync_playwright  # opcional
            self._pw = sync_playwright().start()
            self._render = self._pw.chromium.launch()
        host = urlparse(url).netloc
        with self._lock(host):
            self._esperar(host)
            ctx = self._render.new_context(user_agent=self.ua, locale="es-CO")
            page = ctx.new_page()
            try:
                page.goto(url, timeout=self.timeout * 1000, wait_until="networkidle")
            except Exception:
                pass  # usamos lo que alcanzó a cargar
            html = page.content()
            ctx.close()
        return html

    def cerrar(self):
        if self._render is not None:
            self._render.close()
            self._pw.stop()
