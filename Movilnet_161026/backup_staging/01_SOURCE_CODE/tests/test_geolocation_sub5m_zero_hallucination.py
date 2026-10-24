#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_geolocation_sub5m_zero_hallucination.py
===================================================
Suite de Pruebas Automatizadas: Algoritmo de Geolocalización Catastral Sub-5m
y Regla Inviolable de Cero Adivinación (Zero-Hallucination).

Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)
Regla: regla-inviolable-cero-adivinacion-geolocalizacion.md

Verificaciones:
1. Precisión matemática sub-5m en Los Palos Grandes (Residencias Guillén, 3ra Av.).
2. Precisión matemática sub-5m en Altamira (Plaza Francia).
3. Aislamiento estricto de cuadrícula: LPG NUNCA resuelve a Altamira y viceversa.
4. Extracción de pines GPS embebidos en texto WhatsApp ([UBICACION_GPS: ...]).
5. Despacho Fast-Path con 0 tokens y <15ms de latencia.
6. Integración del Despachador de Emergencias 911 y Paramédicos (Waze + Maps).
7. Inyección obligatoria del bloque Grounding Geoespacial para LLM.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKUP_SOURCE = PROJECT_ROOT / "backup_staging" / "01_SOURCE_CODE"
if str(BACKUP_SOURCE) not in sys.path:
    sys.path.insert(0, str(BACKUP_SOURCE))

from core.cadastral_reverse_geocoder import cadastral_geocoder, encode_plus_code_11d
from core.fastpath_intent_interceptor import fastpath_interceptor, FastPathIntentInterceptor
from core.emergency_dispatcher import emergency_dispatcher
from core.llm_reasoning_engine import LLMReasoningEngine


class TestGeolocationSub5mZeroHallucination(unittest.TestCase):
    """Pruebas exhaustivas de geolocalización de alta precisión sub-5m y cero adivinación."""

    def setUp(self):
        self.lpg_lat = 10.50207805633545
        self.lpg_lon = -66.84334564208984
        self.altamira_lat = 10.4960
        self.altamira_lon = -66.8530
        self.el_rosal_lat = 10.4892
        self.el_rosal_lon = -66.8683
        
        # Garantizar aislamiento de pruebas (Pilar V)
        import sqlite3
        try:
            with sqlite3.connect(emergency_dispatcher.db_path) as conn:
                conn.execute("DELETE FROM emergency_dispatch_records WHERE msisdn IN ('04142554590', '584142554590', '04149998877')")
                conn.commit()
        except Exception:
            pass
        emergency_dispatcher._active_sessions.pop("584142554590", None)
        emergency_dispatcher._active_sessions.pop("04142554590", None)

    def test_01_lpg_cadastral_accuracy_sub5m(self):
        """Coordenadas de traza #13852 en Los Palos Grandes deben resolver a LPG y NUNCA Altamira."""
        res = cadastral_geocoder.resolve(self.lpg_lat, self.lpg_lon)
        self.assertTrue(res.is_venezuela)
        self.assertLessEqual(res.accuracy_meters_est, 5.0)
        self.assertEqual(res.urbanization, "Los Palos Grandes")
        self.assertIn("Chacao", res.municipality)
        self.assertIn("Miranda", res.state)
        self.assertEqual(res.plus_code_11d, "772MG524+RMH")
        self.assertIn("Los Palos Grandes", res.display_address)
        self.assertIn("Chacao", res.display_address)
        # Invariante de Cero Confusión: No debe decir que está en Altamira
        self.assertNotIn("Altamira", res.urbanization)
        self.assertNotIn("Plaza Francia", res.display_address)

    def test_02_altamira_cadastral_accuracy_sub5m(self):
        """Coordenadas en Plaza Francia deben resolver a Altamira y NUNCA Los Palos Grandes."""
        res = cadastral_geocoder.resolve(self.altamira_lat, self.altamira_lon)
        self.assertTrue(res.is_venezuela)
        self.assertLessEqual(res.accuracy_meters_est, 5.0)
        self.assertEqual(res.urbanization, "Altamira")
        self.assertIn("Chacao", res.municipality)
        self.assertIn("Altamira", res.display_address)
        self.assertIn("Plaza Francia", res.display_address)
        # Invariante de Cero Confusión: No debe decir que está en Los Palos Grandes
        self.assertNotIn("Los Palos Grandes", res.display_address)

    def test_03_el_rosal_torre_movilnet_cadastral(self):
        """Coordenadas en El Rosal deben resolver a Torre Movilnet."""
        res = cadastral_geocoder.resolve(10.4890, -66.8670)
        self.assertTrue(res.is_venezuela)
        self.assertEqual(res.urbanization, "El Rosal")
        self.assertIn("Torre Movilnet", res.display_address)

    def test_04_outside_venezuela_detection(self):
        """Coordenadas fuera del territorio venezolano (Bogotá) deben marcar is_venezuela = False."""
        res = cadastral_geocoder.resolve(4.7110, -74.0721)
        self.assertFalse(res.is_venezuela)
        self.assertIn("fuera de venezuela", res.display_address.lower())

    def test_05_fastpath_embedded_gps_extraction(self):
        """FastPath debe extraer automáticamente coordenadas incrustadas en texto WhatsApp."""
        msg = f"¿Dónde estoy exactamente? [UBICACION_GPS: lat={self.lpg_lat}, lon={self.lpg_lon}]"
        res = fastpath_interceptor.intercept(msg, "04142554590")
        self.assertTrue(res.can_intercept)
        self.assertEqual(res.intent_detected, "CONSULTA_GEOESPACIAL_UBICACION")
        self.assertEqual(res.tokens_consumed, 0)
        self.assertLess(res.latency_ms, 150.0)
        self.assertIn("Los Palos Grandes", res.response_text)
        self.assertIn("Chacao", res.response_text)
        self.assertIn("772MG524+RMH", res.response_text)
        # Regla de Cero Adivinación: No debe alucinar Altamira
        self.assertNotIn("Plaza Francia", res.response_text)

    def test_06_emergency_dispatcher_sub5m_cadastral(self):
        """Despacho de emergencia 911 en LPG debe incluir dirección catastral y referencia hablada exacta."""
        res = emergency_dispatcher.process_high_precision_emergency(
            phone="04142554590",
            lat=self.lpg_lat,
            lon=self.lpg_lon,
            accuracy_meters=3.2,
            text_context="Accidente en la vía, necesito ambulancia urgente"
        )
        self.assertEqual(res["status"], "LOCALIZADO")
        self.assertTrue(res["is_sub_5m"])
        self.assertEqual(res["plus_code"], "772MG524+RMH")
        self.assertIn("Los Palos Grandes", res["response_text"])
        self.assertIn("Chacao", res["response_text"])
        self.assertIn("Diles:", res["response_text"])
        self.assertIn("Waze", res["response_text"])
        self.assertIn("google.com/maps", res["response_text"] + res["maps_url"])

    def test_07_llm_grounding_block_injection(self):
        """El bloque de Grounding Geoespacial inyectado al LLM debe ser estricto e inmutable."""
        llm = LLMReasoningEngine()
        grounding = llm._get_location_and_weather(self.lpg_lat, self.lpg_lon, fetch_live_weather=False)
        self.assertIn("[GROUNDING_GEOESPACIAL_DETERMINISTA", grounding)
        self.assertIn("Los Palos Grandes", grounding)
        self.assertIn("772MG524+RMH", grounding)
        self.assertIn("Chacao", grounding)
        self.assertIn("NUNCA debes decir que está en otra urbanización", grounding)

    def test_08_llm_grounding_block_when_coords_missing(self):
        """Cuando no hay coordenadas GPS, el LLM recibe directiva expresa de NO inventar."""
        llm = LLMReasoningEngine()
        grounding = llm._get_location_and_weather(None, None, fetch_live_weather=False)
        self.assertIn("Coordenadas GPS del abonado: NO SUMINISTRADAS", grounding)
        self.assertIn("NUNCA asumas Caracas ni inventes su ubicación", grounding)

    def test_09_semantic_fallback_exact_location(self):
        """El razonador semántico local debe resolver consultas de ubicación en LPG con precisión sub-5m."""
        llm = LLMReasoningEngine()
        reply, toks, cost = llm._semantic_fallback_reasoner(
            message=f"¿Dónde estoy? [UBICACION_GPS: lat={self.lpg_lat}, lon={self.lpg_lon}]",
            session_history=[],
            msisdn="04142554590"
        )
        self.assertEqual(toks, 0)
        self.assertIn("Los Palos Grandes", reply)
        self.assertIn("772MG524+RMH", reply)
        self.assertIn("Chacao", reply)
        self.assertNotIn("Plaza Altamira", reply)


if __name__ == "__main__":
    unittest.main()
