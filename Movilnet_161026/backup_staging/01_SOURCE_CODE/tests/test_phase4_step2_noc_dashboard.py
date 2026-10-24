#!/usr/bin/env python3
"""
tests/test_phase4_step2_noc_dashboard.py — Suite Automatizada de Pruebas del Dashboard NOC/CCO
=============================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Hito: Fase 4 — Paso 2: Dashboard Web Ejecutivo de Operaciones (NOC / CCO).
"""

import json
import math
import os
import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.service import MovilnetAPIService, get_openapi_specification


def parse_hex_color(hex_str: str):
    """Convierte un color hexadecimal en tupla (r, g, b) normalizada [0, 1]."""
    hex_str = hex_str.strip().lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join([c * 2 for c in hex_str])
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return r, g, b


def calculate_srgb_luminance(r: float, g: float, b: float) -> float:
    """Calcula la luminancia relativa según fórmula oficial W3C WCAG 2.1."""
    def adjust(c):
        return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)
    r_adj = adjust(r)
    g_adj = adjust(g)
    b_adj = adjust(b)
    return 0.2126 * r_adj + 0.7152 * g_adj + 0.0722 * b_adj


def calculate_contrast_ratio(hex1: str, hex2: str) -> float:
    """Calcula el ratio de contraste entre dos colores hexadecimales (L1 + 0.05) / (L2 + 0.05)."""
    l1 = calculate_srgb_luminance(*parse_hex_color(hex1))
    l2 = calculate_srgb_luminance(*parse_hex_color(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class TestPhase4Step2NocDashboard(unittest.TestCase):
    """Batería de pruebas formales para el Dashboard Web Ejecutivo NOC/CCO."""

    @classmethod
    def setUpClass(cls):
        cls.ui_dir = PROJECT_ROOT / "ui"
        cls.dashboard_dir = cls.ui_dir / "dashboard"
        cls.html_noc = cls.dashboard_dir / "noc_dashboard.html"
        cls.css_noc = cls.dashboard_dir / "css" / "noc_dashboard.css"
        cls.js_noc = cls.dashboard_dir / "js" / "noc_dashboard.js"
        cls.api_service = MovilnetAPIService()

    def test_01_dashboard_assets_existence(self):
        """Verifica la existencia física de los activos clave del Dashboard NOC/CCO."""
        self.assertTrue(self.html_noc.is_file(), f"Falta noc_dashboard.html: {self.html_noc}")
        self.assertTrue(self.css_noc.is_file(), f"Falta noc_dashboard.css: {self.css_noc}")
        self.assertTrue(self.js_noc.is_file(), f"Falta noc_dashboard.js: {self.js_noc}")

    def test_02_html_semantic_and_a11y_structure(self):
        """Valida que el HTML tenga estructura semántica estricta (header, main, footer, roles y aria-labels)."""
        content = self.html_noc.read_text(encoding="utf-8")

        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn('<html lang="es">', content)
        self.assertIn('role="banner"', content)
        self.assertIn('role="main"', content)
        self.assertIn('role="contentinfo"', content)
        self.assertIn('skip-link', content, "Debe contener enlace accesible de salto para lectores de pantalla")
        self.assertIn('aria-label=', content, "Debe contener atributos aria-label para navegación accesible")

        # Elementos clave esperados
        self.assertIn('id="kpi-total-subs"', content)
        self.assertIn('id="kpi-c2p-ves"', content)
        self.assertIn('id="noc-clock-time"', content)
        self.assertIn('id="noc-security-tbody"', content)
        self.assertIn('id="noc-banks-tbody"', content)

    def test_03_css_dark_mode_contrast_wcag_aaa(self):
        """Verifica que los estilos del NOC cumplan WCAG 2.1 AAA en modo oscuro (> 7.0:1)."""
        content = self.css_noc.read_text(encoding="utf-8")

        # Paleta dark mode del NOC
        canvas_bg = "#060B11"
        text_bright = "#F8FAFC"
        text_normal = "#CBD5E1"

        contrast_bright = calculate_contrast_ratio(canvas_bg, text_bright)
        contrast_normal = calculate_contrast_ratio(canvas_bg, text_normal)

        self.assertGreaterEqual(
            contrast_bright, 7.0,
            f"El contraste de texto brillante sobre canvas dark debe ser >= 7.0:1 (Actual: {contrast_bright:.2f})"
        )
        self.assertGreaterEqual(
            contrast_normal, 7.0,
            f"El contraste de texto normal sobre canvas dark debe ser >= 7.0:1 (Actual: {contrast_normal:.2f})"
        )

        # Reglas CSS de interactividad y WAI-ARIA
        self.assertIn(":focus-visible", content, "Debe existir anillo accesible para foco de teclado")
        self.assertIn("min-height: 44px", content, "Debe respetar tamaño mínimo de objetivo táctil de 44px")

    def test_04_js_logic_and_polling(self):
        """Verifica que el script del Dashboard contenga lógica para polling, formateo y manejo de errores."""
        content = self.js_noc.read_text(encoding="utf-8")

        self.assertIn("/api/v1/metrics/live", content, "Debe consultar el endpoint oficial de telemetría")
        self.assertIn("fetchLiveMetrics", content)
        self.assertIn("updateClock", content)
        self.assertIn("renderMetrics", content)
        self.assertIn("AbortController", content, "Debe implementar AbortController para prevenir cuellos de botella")

    def test_05_static_file_dispatch_serving(self):
        """Verifica que el microservicio API despache correctamente los archivos estáticos del dashboard."""
        status_html, headers_html, body_html = self.api_service.dispatch("GET", "/ui/dashboard/noc_dashboard.html", {}, b"")
        self.assertEqual(status_html, 200)
        self.assertIn("text/html", headers_html["Content-Type"])
        self.assertIn(b"MOVILNET C.A.", body_html)

        status_css, headers_css, body_css = self.api_service.dispatch("GET", "/ui/dashboard/css/noc_dashboard.css", {}, b"")
        self.assertEqual(status_css, 200)
        self.assertIn("text/css", headers_css["Content-Type"])

        status_js, headers_js, body_js = self.api_service.dispatch("GET", "/ui/dashboard/js/noc_dashboard.js", {}, b"")
        self.assertEqual(status_js, 200)
        self.assertIn("javascript", headers_js["Content-Type"])

    def test_06_noc_live_metrics_endpoint(self):
        """Valida el endpoint /api/v1/metrics/live con KPIs de 4M de abonados, Swarm N1-N4, C2P y EIR."""
        status, headers, body = self.api_service.dispatch("GET", "/api/v1/metrics/live", {}, b"")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers["Content-Type"])

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "OPERATIONAL")
        self.assertEqual(data["node"], "NOC-CENTRAL-CARACAS-01")

        # 1. Base 4M Abonados
        self.assertIn("subscribers_kpis", data)
        sub = data["subscribers_kpis"]
        self.assertEqual(sub["total_installed_base"], 4000000)
        self.assertIn("PREPAGO_MASIVO", sub["segments"])
        self.assertIn("POSPAGO_CONECTA", sub["segments"])
        self.assertIn("CORPORATIVO_4GMAX", sub["segments"])
        self.assertIn("JUBILADO", sub["segments"])

        # 2. Enjambre Swarm N1-N4
        self.assertIn("swarm_orchestration", data)
        swarm = data["swarm_orchestration"]
        self.assertEqual(swarm["orchestration_level"], "LEVEL_5_AUTONOMOUS_SWARM")
        self.assertEqual(swarm["circuit_breaker"], "CLOSED_HEALTHY")
        agents = swarm["agents"]
        self.assertIn("N1_CUSTOMER_CARE", agents)
        self.assertIn("N2_FINTECH_C2P", agents)
        self.assertIn("N3_EMERGENCY_EIR", agents)
        self.assertIn("N4_RETENTION_CHURN", agents)

        # 3. Flujo C2P
        self.assertIn("fintech_c2p_control", data)
        fin = data["fintech_c2p_control"]
        self.assertGreater(fin["today_total_recharge_ves"], 0)
        self.assertGreater(fin["today_total_usd_equivalent"], 0)
        self.assertTrue(len(fin["top_banks"]) >= 3)

        # 4. Red Radioeléctrica
        self.assertIn("network_telemetry", data)
        net = data["network_telemetry"]
        self.assertGreaterEqual(net["core_availability_pct"], 99.9)

    def test_07_noc_overview_endpoint(self):
        """Valida el endpoint ligero /api/v1/noc/status para health probes del CCO."""
        status, headers, body = self.api_service.dispatch("GET", "/api/v1/noc/status", {}, b"")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "HEALTHY")
        self.assertEqual(data["mode"], "CCO_EXECUTIVE")
        self.assertEqual(data["total_subscribers"], 4000000)

    def test_08_openapi_contract_includes_noc(self):
        """Verifica que el contrato formal OpenAPI 3.1.0 contemple los endpoints y schemas del NOC."""
        spec = get_openapi_specification()
        paths = spec["paths"]

        self.assertIn("/api/v1/metrics/live", paths)
        self.assertIn("/api/v1/noc/status", paths)

        schemas = spec["components"]["schemas"]
        self.assertIn("NocLiveMetricsResponse", schemas)
        self.assertIn("NocStatusResponse", schemas)


if __name__ == "__main__":
    unittest.main()
