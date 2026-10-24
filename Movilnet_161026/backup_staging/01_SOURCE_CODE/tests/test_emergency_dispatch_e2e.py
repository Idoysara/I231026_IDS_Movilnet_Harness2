#!/usr/bin/env python3
"""
tests/test_emergency_dispatch_e2e.py — Suite de Pruebas Automatizadas de Emergencia 911
========================================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: Regla del 100% Pass)
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.emergency_dispatcher import EmergencyDispatcher, emergency_dispatcher
from core.fastpath_intent_interceptor import FastPathIntentInterceptor, fastpath_interceptor
from api.service import MovilnetAPIService


class TestEmergencyDispatchE2E(unittest.TestCase):
    """Pruebas E2E de compuerta prioritaria y universal de emergencia 911."""

    def setUp(self):
        self.interceptor = fastpath_interceptor
        self.api_service = MovilnetAPIService()

    def test_01_emergency_text_movilnet_subscriber(self):
        """Prueba 1: Entrada de texto de auxilio desde número Movilnet."""
        phone = "04169998877"
        text = "Por favor auxilio me estan robando en la parada del metro"
        
        fp_res = self.interceptor.intercept(text, phone)
        self.assertTrue(fp_res.can_intercept, "Debe ser interceptado por Fast-Path determinista")
        self.assertEqual(fp_res.intent_detected, "EMERGENCY_DISPATCH_911")
        self.assertEqual(fp_res.tokens_consumed, 0)
        self.assertIn("CENTRO DE EMERGENCIAS", fp_res.response_text)
        self.assertIn("911", fp_res.response_text)

    def test_02_emergency_text_competitor_no_marketing_leak(self):
        """Prueba 2: Entrada de auxilio desde competidor (Movistar/Digitel) sin fugas de marketing."""
        phones = ["04142554590", "04121112233"]
        for phone in phones:
            text = "Emergencia 911 necesitamos una ambulancia urgente"
            fp_res = self.interceptor.intercept(text, phone)
            
            self.assertTrue(fp_res.can_intercept)
            self.assertEqual(fp_res.intent_detected, "EMERGENCY_DISPATCH_911")
            self.assertEqual(fp_res.tokens_consumed, 0)
            
            # Verificar que no se filtre publicidad ni ofertas en emergencia
            self.assertNotIn("eSIM", fp_res.response_text.split("🌐")[0])
            self.assertNotIn("Bono", fp_res.response_text.split("🌐")[0])
            self.assertIn("CENTRO DE EMERGENCIAS", fp_res.response_text)

    def test_03_emergency_with_gps_coordinates(self):
        """Prueba 3: Procesamiento de coordenadas GPS válidas en Venezuela."""
        phone = "04245556677"
        lat, lon = 10.496123, -66.845456
        text = "Aquí está mi ubicación del accidente"

        fp_res = self.interceptor.intercept(text, phone, latitude=lat, longitude=lon)
        self.assertTrue(fp_res.can_intercept)
        self.assertEqual(fp_res.intent_detected, "EMERGENCY_DISPATCH_911")
        self.assertIn("REPORTE DE EMERGENCIA REGISTRADO", fp_res.response_text)
        self.assertIn("google.com/maps", fp_res.response_text)
        self.assertIn(f"{lat:.6f}, {lon:.6f}", fp_res.response_text)

    def test_04_e2e_api_service_endpoint(self):
        """Prueba 4: Enrutamiento integral a través del controlador REST MovilnetAPIService."""
        payload = {
            "text": "911 socorro me persiguen",
            "phone": "04142554590",
            "channel": "whatsapp"
        }
        status, resp = self.api_service.handle_customer_care_agent(payload)
        self.assertEqual(status, 200)
        self.assertIn("CENTRO DE EMERGENCIAS", resp["response"])
        self.assertEqual(resp["tokens_consumed"], 0)
        self.assertEqual(resp["metadata"]["fastpath_intent"], "EMERGENCY_DISPATCH_911")
        # Regla inviolable: enlace PWA universal
        self.assertIn("ui/pwa", resp["response"])

    def test_05_multi_turn_alert_then_location(self):
        """Prueba 5: Sesión multi-turno encadenada (primero auxilio, luego ubicación nativa)."""
        phone = "04267778899"
        
        # Turno 1: Texto de alerta
        r1 = self.interceptor.intercept("911 auxilio por favor", phone)
        self.assertEqual(r1.intent_detected, "EMERGENCY_DISPATCH_911")
        self.assertIn("CENTRO DE EMERGENCIAS", r1.response_text)

        # Turno 2: Ubicación sin texto de auxilio explícito (debe asociarse a la emergencia abierta)
        r2 = self.interceptor.intercept("[UBICACION_GPS: lat=10.24, lon=-67.59]", phone, latitude=10.24, longitude=-67.59)
        self.assertEqual(r2.intent_detected, "EMERGENCY_DISPATCH_911")
        self.assertIn("REPORTE DE EMERGENCIA REGISTRADO", r2.response_text)
        self.assertIn("10.240000, -67.590000", r2.response_text)


if __name__ == "__main__":
    unittest.main()
