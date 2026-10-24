#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core_router.py — Router de Dominio Core, Documentación, Salud y UI Estática
=============================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
Enruta peticiones de healthcheck, status operativo, especificación OpenAPI 3.1.0,
interfaz Swagger UI y entrega de activos estáticos de la PWA 4GMAX.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.transport.static_streamer import serve_static_file
from api.openapi_contract import get_openapi_specification
from api.routers.base_router import BaseDomainRouter, RouteResult, cors_headers, json_response
from api.service_constants import SERVICE_NAME, SERVICE_VERSION


def get_swagger_ui_html() -> str:
    """Genera interfaz visual interactiva para explorar la API sin dependencias externas."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>{SERVICE_NAME} — Documentación Interactiva</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
  <style>
    body {{ margin: 0; background: #fafafa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    .topbar {{ background: #003366 !important; padding: 10px 0; color: white; text-align: center; }}
    .topbar h1 {{ margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.5px; }}
    .topbar p {{ margin: 3px 0 0 0; font-size: 13px; opacity: 0.85; }}
  </style>
</head>
<body>
  <div class="topbar">
    <h1>MOVILNET C.A. — CORE API REST TM FORUM ODA</h1>
    <p>Especificación Oficial OpenAPI 3.1.0 | v{SERVICE_VERSION} | Entorno Activo</p>
  </div>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function() {{
      SwaggerUIBundle({{
        url: '/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout"
      }});
    }};
  </script>
</body>
</html>"""


class CoreRouter(BaseDomainRouter):
    """Router para endpoints base del sistema (Health, Status, OpenAPI, Docs y PWA UI)."""

    CORE_GET_ROUTES = {
        "/openapi.json",
        "/api/v1/openapi.json",
        "/docs",
        "/health",
        "/api/v1/health",
        "/status",
        "/api/v1/status",
        "/",
        "/index.html",
        "/prospect",
        "/chat",
        "/pwa",
        "/app",
        "/stitch",
        "/simulador",
        "/simulador.html",
        "/celular",
        "/celular.html",
        "/mockup",
        "/sos",
        "/sos.html",
    }

    def match(self, method: str, clean_path: str) -> bool:
        if method == "OPTIONS" and clean_path in ["/status", "/api/v1/status"]:
            return True
        if method in ("GET", "HEAD"):
            if clean_path in self.CORE_GET_ROUTES:
                return True
            if clean_path == "/ui" or clean_path.startswith("/ui/"):
                return True
        return False

    def handle(
        self,
        method: str,
        path: str,
        clean_path: str,
        headers: Dict[str, str],
        body_bytes: bytes,
        service: Any
    ) -> RouteResult:
        # Pre-flight CORS OPTIONS
        if method == "OPTIONS":
            return 204, cors_headers(), b""

        # OpenAPI Spec
        if clean_path in ["/openapi.json", "/api/v1/openapi.json"]:
            return json_response(200, get_openapi_specification())

        # Swagger UI HTML
        if clean_path == "/docs":
            html = get_swagger_ui_html().encode("utf-8")
            hdrs = cors_headers("text/html; charset=utf-8")
            return 200, hdrs, html

        # UI Simulador / Celular
        if clean_path in ["/simulador", "/simulador.html", "/celular", "/celular.html", "/mockup"]:
            return serve_static_file("/ui/pwa_stitch/simulador.html")

        # UI SOS Alta Precisión (<5m)
        if clean_path in ["/sos", "/sos.html"]:
            return serve_static_file("/ui/pwa_stitch/sos.html")

        # UI PWA Stitch para Prospectos y Chat
        if clean_path in ["/prospect", "/chat", "/stitch"]:
            return serve_static_file("/ui/pwa_stitch/index.html")

        # UI PWA Principal
        if clean_path in ["/", "/index.html", "/pwa", "/app"]:
            return serve_static_file("/ui/pwa/index.html")

        # Activos Estáticos /ui/*
        if clean_path == "/ui" or clean_path.startswith("/ui/"):
            return serve_static_file(clean_path)

        # Health
        if clean_path in ["/health", "/api/v1/health"]:
            status_code, payload = service.handle_health()
            return json_response(status_code, payload)

        # Status
        if clean_path in ["/status", "/api/v1/status"]:
            status_code, payload = service.handle_status()
            return json_response(status_code, payload)

        return 404, cors_headers(), b'{"code":"ERR_NOT_FOUND","message":"Ruta Core no encontrada"}'


# ============================================================================
# CLI DE AUTO-VERIFICACIÓN
# ============================================================================

def run_self_tests() -> int:
    """Ejecuta suite de pruebas unitarias para CoreRouter."""
    print("🧪 Verificando core_router.py...")
    router = CoreRouter()

    # 1. Match verificación
    assert router.match("GET", "/health") is True
    assert router.match("GET", "/docs") is True
    assert router.match("GET", "/openapi.json") is True
    assert router.match("GET", "/ui/pwa_stitch/index.html") is True
    assert router.match("OPTIONS", "/api/v1/status") is True
    assert router.match("POST", "/health") is False

    # 2. Despacho /docs
    status, hdrs, body = router.handle("GET", "/docs", "/docs", {}, b"", None)
    assert status == 200
    assert "text/html" in hdrs["Content-Type"]
    assert b"SwaggerUIBundle" in body

    # 3. Despacho /openapi.json
    status, hdrs, body = router.handle("GET", "/openapi.json", "/openapi.json", {}, b"", None)
    assert status == 200
    assert b"Movilnet Telco & FinTech Core API" in body

    # 4. Despacho OPTIONS /api/v1/status
    status, hdrs, body = router.handle("OPTIONS", "/api/v1/status", "/api/v1/status", {}, b"", None)
    assert status == 204
    assert body == b""

    # 5. Mock service para /health
    class MockService:
        def handle_health(self):
            return 200, {"status": "healthy", "service": "TEST"}
        def handle_status(self):
            return 200, {"status": "ok"}

    mock_srv = MockService()
    status, _, body = router.handle("GET", "/health", "/health", {}, b"", mock_srv)
    assert status == 200
    assert b"healthy" in body

    print("✅ [TEST PASS] core_router: 5/5 pruebas aprobadas (100%).")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Core Domain Router")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación")
    args = parser.parse_args()

    if args.test:
        sys.exit(run_self_tests())
    else:
        print("Uso: python3 -m api.routers.core_router --test")


if __name__ == "__main__":
    main()
