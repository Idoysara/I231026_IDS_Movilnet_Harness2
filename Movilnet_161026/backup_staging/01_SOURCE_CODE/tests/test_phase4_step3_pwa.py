#!/usr/bin/env python3
"""
tests/test_phase4_step3_pwa.py — Suite Automatizada de Pruebas del Portal PWA Móvil
===================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Hito: Fase 4 — Paso 3: Portal PWA de Autoservicio Móvil del Abonado.
"""

import json
import math
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.service import MovilnetAPIService


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


class TestPhase4Step3Pwa(unittest.TestCase):
    """Batería de pruebas automatizadas para la PWA de Autoservicio Móvil del Abonado."""

    @classmethod
    def setUpClass(cls):
        cls.ui_dir = PROJECT_ROOT / "ui"
        cls.pwa_dir = cls.ui_dir / "pwa"
        cls.html_pwa = cls.pwa_dir / "index.html"
        cls.manifest = cls.pwa_dir / "manifest.json"
        cls.sw = cls.pwa_dir / "sw.js"
        cls.css_pwa = cls.pwa_dir / "css" / "pwa.css"
        cls.js_pwa = cls.pwa_dir / "js" / "pwa.js"
        cls.api_service = MovilnetAPIService()

    def test_01_pwa_files_existence(self):
        """Verifica la existencia física de los activos clave de la PWA."""
        self.assertTrue(self.html_pwa.is_file(), f"Falta index.html: {self.html_pwa}")
        self.assertTrue(self.manifest.is_file(), f"Falta manifest.json: {self.manifest}")
        self.assertTrue(self.sw.is_file(), f"Falta sw.js: {self.sw}")
        self.assertTrue(self.css_pwa.is_file(), f"Falta pwa.css: {self.css_pwa}")
        self.assertTrue(self.js_pwa.is_file(), f"Falta pwa.js: {self.js_pwa}")

    def test_02_w3c_manifest_compliance(self):
        """Valida que manifest.json cumpla con las especificaciones W3C PWA."""
        content = json.loads(self.manifest.read_text(encoding="utf-8"))

        self.assertIn("name", content)
        self.assertIn("short_name", content)
        self.assertEqual(content["short_name"], "Mi Movilnet")
        self.assertEqual(content["display"], "standalone")
        self.assertEqual(content["start_url"], "/ui/pwa/")
        self.assertEqual(content["theme_color"], "#002B49")
        self.assertEqual(content["background_color"], "#002B49")
        self.assertTrue(len(content["icons"]) >= 2)

    def test_03_service_worker_logic(self):
        """Valida que el Service Worker maneje eventos install, activate y fetch con offline fallback."""
        content = self.sw.read_text(encoding="utf-8")

        self.assertIn("addEventListener('install'", content)
        self.assertIn("addEventListener('activate'", content)
        self.assertIn("addEventListener('fetch'", content)
        self.assertIn("caches.open", content)
        self.assertIn("offline_mode", content)

    def test_04_html_mobile_ergonomics_and_a11y(self):
        """Verifica el marcado semántico HTML, viewport móvil, meta tags y accesibilidad."""
        content = self.html_pwa.read_text(encoding="utf-8")

        self.assertIn('<meta name="viewport"', content)
        self.assertIn('link rel="manifest"', content)
        self.assertIn('skip-link', content)
        self.assertIn('role="banner"', content)
        self.assertIn('role="main"', content)
        self.assertIn('role="navigation"', content)
        self.assertIn('id="pwa-balance-ves"', content)
        self.assertIn('id="pwa-c2p-form"', content)
        self.assertIn('id="pwa-chat-messages"', content)

    def test_05_css_touch_targets_and_wcag_contrast(self):
        """Verifica que los estilos móviles respeten tamaños táctiles >= 44px y contrastes de texto."""
        content = self.css_pwa.read_text(encoding="utf-8")

        self.assertIn("min-height: 48px", content, "Los inputs y botones deben ser >= 44px para WCAG 2.5.5")
        self.assertIn("min-height: 44px", content)
        self.assertIn(":focus-visible", content)

        # Contraste de texto primario (#0F172A) sobre fondo claro (#F4F6F9)
        contrast = calculate_contrast_ratio("#F4F6F9", "#0F172A")
        self.assertGreaterEqual(contrast, 7.0, f"Contraste debe ser >= 7:1 (Actual: {contrast:.2f})")

    def test_06_js_pwa_integration_and_c2p(self):
        """Verifica que el script pwa.js contenga la integración con OCS y C2P."""
        content = self.js_pwa.read_text(encoding="utf-8")

        self.assertIn("/api/v1/subscribers/balance", content)
        self.assertIn("/api/v1/payments/c2p", content)
        self.assertIn("registerServiceWorker", content)
        self.assertIn("loadSubscriberBalance", content)
        self.assertIn("handleC2PSubmit", content)

    def test_07_api_serving_pwa_assets(self):
        """Valida que el microservicio API despache todos los archivos de la PWA con Content-Type correcto."""
        status_html, headers_html, body_html = self.api_service.dispatch("GET", "/ui/pwa/index.html", {}, b"")
        self.assertEqual(status_html, 200)
        self.assertIn("text/html", headers_html["Content-Type"])

        status_man, headers_man, body_man = self.api_service.dispatch("GET", "/ui/pwa/manifest.json", {}, b"")
        self.assertEqual(status_man, 200)
        self.assertIn("application/json", headers_man["Content-Type"])

        status_sw, headers_sw, body_sw = self.api_service.dispatch("GET", "/ui/pwa/sw.js", {}, b"")
        self.assertEqual(status_sw, 200)
        self.assertIn("javascript", headers_sw["Content-Type"])

    def test_08_pwa_balance_query_mock_execution(self):
        """Verifica que el endpoint de saldo responda satisfactoriamente a las consultas de la PWA."""
        status, headers, body = self.api_service.dispatch("POST", "/api/v1/subscribers/balance", {}, json.dumps({
            "msisdn": "04160000001",
            "cid": "V-10000001"
        }).encode("utf-8"))
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["msisdn"], "04160000001")
        self.assertIn("balance_ves", data)
        self.assertIn("remaining_data_mb", data)


if __name__ == "__main__":
    unittest.main()
