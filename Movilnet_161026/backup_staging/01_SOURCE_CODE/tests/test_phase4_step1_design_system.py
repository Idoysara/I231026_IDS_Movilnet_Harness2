#!/usr/bin/env python3
"""
tests/test_phase4_step1_design_system.py — Suite Automatizada de Pruebas del Sistema de Diseño UI/UX/IX/AX
========================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Hito: Fase 4 — Paso 1: Sistema de Diseño Corporativo Movilnet, Design Tokens y Prototipado Accesible (WCAG 2.1 AAA).
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


class TestPhase4Step1DesignSystem(unittest.TestCase):
    """Batería de pruebas formales para el Sistema de Diseño Movilnet (WCAG 2.1 AAA)."""

    @classmethod
    def setUpClass(cls):
        cls.ui_dir = PROJECT_ROOT / "ui"
        cls.tokens_file = cls.ui_dir / "tokens" / "design_tokens.json"
        cls.css_tokens = cls.ui_dir / "css" / "movilnet_tokens.css"
        cls.css_components = cls.ui_dir / "css" / "movilnet_components.css"
        cls.js_ui = cls.ui_dir / "js" / "movilnet_ui.js"
        cls.html_index = cls.ui_dir / "index.html"
        cls.api_service = MovilnetAPIService()

    def test_01_design_tokens_json_structure(self):
        """Verifica la existencia, validez y estructura formal del archivo design_tokens.json."""
        self.assertTrue(self.tokens_file.is_file(), f"Falta archivo de tokens: {self.tokens_file}")
        with open(self.tokens_file, "r", encoding="utf-8") as f:
            tokens = json.load(f)

        self.assertIn("name", tokens)
        self.assertIn("metadata", tokens)
        self.assertEqual(tokens["metadata"]["wcag_compliance"], "WCAG 2.1 Level AAA")
        self.assertIn("color", tokens)
        self.assertIn("brand", tokens["color"])

        brand = tokens["color"]["brand"]
        self.assertEqual(brand["primary"]["value"].upper(), "#002B49")
        self.assertEqual(brand["accent"]["value"].upper(), "#FF6A13")
        self.assertEqual(brand["secondary"]["value"].upper(), "#00558C")
        self.assertEqual(brand["cyan"]["value"].upper(), "#00A3E0")

        self.assertIn("accessibility_a11y", tokens)
        self.assertEqual(tokens["accessibility_a11y"]["minimum_tap_target"]["value"], "44px")

    def test_02_wcag_aaa_contrast_ratios(self):
        """Valida matemáticamente que los ratios de contraste superen el estándar WCAG 2.1 AAA (> 7.0:1)."""
        # 1. Azul Movilnet sobre Blanco
        contrast_blue_white = calculate_contrast_ratio("#002B49", "#FFFFFF")
        self.assertGreaterEqual(
            contrast_blue_white, 7.0,
            f"El contraste de #002B49 sobre #FFFFFF debe ser >= 7.0:1 (Actual: {contrast_blue_white:.2f})"
        )

        # 2. Fondo Dark NOC (#0A1118) contra Texto Primario (#F8FAFC)
        contrast_dark_text = calculate_contrast_ratio("#0A1118", "#F8FAFC")
        self.assertGreaterEqual(
            contrast_dark_text, 7.0,
            f"El contraste de #F8FAFC sobre #0A1118 debe ser >= 7.0:1 (Actual: {contrast_dark_text:.2f})"
        )

        # 3. Azul 4GMAX (#00558C) sobre Blanco (#FFFFFF)
        contrast_4gmax_white = calculate_contrast_ratio("#00558C", "#FFFFFF")
        self.assertGreaterEqual(
            contrast_4gmax_white, 7.0,
            f"El contraste de #00558C sobre #FFFFFF debe ser >= 7.0:1 (Actual: {contrast_4gmax_white:.2f})"
        )

    def test_03_css_files_and_standards(self):
        """Verifica la existencia y reglas mandatorias de accesibilidad en los archivos CSS."""
        self.assertTrue(self.css_tokens.is_file(), "Falta movilnet_tokens.css")
        self.assertTrue(self.css_components.is_file(), "Falta movilnet_components.css")

        tokens_css_content = self.css_tokens.read_text(encoding="utf-8")
        components_css_content = self.css_components.read_text(encoding="utf-8")

        # Variables CSS requeridas
        self.assertIn("--mov-blue-primary: #002B49;", tokens_css_content)
        self.assertIn("--mov-orange-accent: #FF6A13;", tokens_css_content)
        self.assertIn("--min-tap-target: 44px;", tokens_css_content)
        self.assertIn("prefers-reduced-motion", tokens_css_content)

        # Componentes requeridos
        self.assertIn(":focus-visible", components_css_content)
        self.assertIn(".mov-btn", components_css_content)
        self.assertIn(".mov-modal-dialog", components_css_content)
        self.assertIn(".mov-skeleton", components_css_content)

    def test_04_html_aria_accessibility_compliance(self):
        """Verifica que index.html cumpla con estándares de semántica HTML5 y WAI-ARIA."""
        self.assertTrue(self.html_index.is_file(), "Falta ui/index.html")
        html_content = self.html_index.read_text(encoding="utf-8")

        self.assertIn('lang="es"', html_content)
        self.assertIn('role="banner"', html_content)
        self.assertIn('role="main"', html_content)
        self.assertIn('role="tablist"', html_content)
        self.assertIn('role="tab"', html_content)
        self.assertIn('role="tabpanel"', html_content)
        self.assertIn('role="dialog"', html_content)
        self.assertIn('aria-modal="true"', html_content)
        self.assertIn('role="progressbar"', html_content)
        self.assertIn('aria-valuenow', html_content)

    def test_05_js_ui_logic_and_luhn10(self):
        """Verifica la existencia y funciones críticas en movilnet_ui.js."""
        self.assertTrue(self.js_ui.is_file(), "Falta ui/js/movilnet_ui.js")
        js_content = self.js_ui.read_text(encoding="utf-8")

        self.assertIn("isValidImeiLuhn", js_content)
        self.assertIn("setTheme", js_content)
        self.assertIn("openModal", js_content)
        self.assertIn("closeModal", js_content)
        self.assertIn("America/Caracas", js_content)

    def test_06_service_api_ui_dispatch(self):
        """Verifica que el microservicio API REST sirva los recursos del sistema de diseño correctamente."""
        # 1. GET /ui -> Debe devolver index.html
        status, headers, body = self.api_service.dispatch("GET", "/ui", {}, b"")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(b"Movilnet Design System", body)

        # 2. GET /ui/tokens/design_tokens.json
        status, headers, body = self.api_service.dispatch("GET", "/ui/tokens/design_tokens.json", {}, b"")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        parsed = json.loads(body.decode("utf-8"))
        self.assertIn("metadata", parsed)

        # 3. GET /ui/css/movilnet_tokens.css
        status, headers, body = self.api_service.dispatch("GET", "/ui/css/movilnet_tokens.css", {}, b"")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/css; charset=utf-8")
        self.assertIn(b"--mov-blue-primary", body)

        # 4. GET /ui/js/movilnet_ui.js
        status, headers, body = self.api_service.dispatch("GET", "/ui/js/movilnet_ui.js", {}, b"")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/javascript; charset=utf-8")

        # 5. Path Traversal Protection
        status, headers, body = self.api_service.dispatch("GET", "/ui/../../etc/passwd", {}, b"")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
