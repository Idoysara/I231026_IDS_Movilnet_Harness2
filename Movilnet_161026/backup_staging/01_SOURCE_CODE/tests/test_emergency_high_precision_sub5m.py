#!/usr/bin/env python3
"""
tests/test_emergency_high_precision_sub5m.py — Suite de Verificación de Localización SOS Sub-5 Metros (<5m)
=============================================================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: 100% Pass)
Propósito:
1. Validar la precisión matemática del algoritmo Open Location Code (Plus Code 11D ~3.5m).
2. Certificar el enrutamiento y despacho geospacial de alta precisión (<5m) GNSS multi-constelación.
3. Probar la compuerta universal sin sesgo de operadora (0416, 0414, 0412, 0212).
4. Verificar los endpoints REST HTTP `POST /api/v1/emergency/sos` y `GET /sos`.
"""

import sys
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.emergency_dispatcher import EmergencyDispatcher, encode_plus_code_11d, emergency_dispatcher
from api.service import MovilnetAPIService


class TestEmergencyHighPrecisionSub5m(unittest.TestCase):
    """Suite de pruebas de geolocalización de emergencia de alta precisión (<5m)."""

    def setUp(self):
        self.dispatcher = emergency_dispatcher
        self.service = MovilnetAPIService()

    def test_01_plus_code_11d_algorithm_accuracy(self):
        """Prueba 1: Precisión submétrica del algoritmo Open Location Code 11D."""
        # Coordenadas Caracas Altamira/Los Palos Grandes
        lat, lon = 10.50207805633545, -66.84334564208984
        code = encode_plus_code_11d(lat, lon)

        self.assertEqual(len(code), 12, "El Plus Code 11D debe tener 12 caracteres (11 alfanuméricos + '+' separador)")
        self.assertEqual(code[8], "+", "El 9no caracter debe ser el separador '+'")
        self.assertEqual(code, "772MG524+RMH", "El Plus Code debe coincidir con la micro-cuadrícula de 3.5m")

    def test_02_process_high_precision_emergency_sub5m(self):
        """Prueba 2: Despacho de auxilio con margen GNSS reportado <= 5.0m."""
        phone = "04142554590"
        lat, lon = 10.502078, -66.843345
        acc = 2.1  # 2.1 metros de margen de error

        res = self.dispatcher.process_high_precision_emergency(
            phone=phone,
            lat=lat,
            lon=lon,
            accuracy_meters=acc,
            altitude_meters=938.5,
            heading_degrees=120.0,
            source_channel="PWA_SOS_HIGH_ACCURACY"
        )

        self.assertEqual(res["status"], "LOCALIZADO")
        self.assertTrue(res["is_sub_5m"])
        self.assertTrue(res["is_venezuela"])
        self.assertEqual(res["plus_code"], "772MG524+RMH")
        self.assertIn("772MG524+RMH", res["response_text"])
        self.assertIn("ALTA PRECISIÓN SATELITAL GNSS (<5m)", res["response_text"])
        self.assertIn("google.com/maps", res["maps_url"])
        self.assertIn("waze.com/ul", res["waze_url"])
        self.assertIn("Salud Chacao", res["response_text"])

    def test_03_universal_carrier_equality(self):
        """Prueba 3: Universalidad total en auxilio SOS para todas las operadoras."""
        carriers_test = [
            ("04161112233", "Movilnet 4GMAX"),
            ("04142554590", "Movistar Venezuela"),
            ("04128889900", "Digitel 4G LTE"),
            ("02129537685", "CANTV / Telefonía Fija Gran Caracas (0212)")
        ]

        for phone, expected_label in carriers_test:
            res = self.dispatcher.process_high_precision_emergency(
                phone=phone,
                lat=10.496000,
                lon=-66.845000,
                accuracy_meters=3.5,
                source_channel="PWA_SOS_TEST"
            )
            self.assertEqual(res["status"], "LOCALIZADO")
            self.assertEqual(res["carrier"], expected_label)
            # Cero fugas de mercadeo
            self.assertNotIn("eSIM", res["response_text"])
            self.assertNotIn("Bono", res["response_text"])
            self.assertNotIn("Freemium", res["response_text"])

    def test_04_http_rest_endpoint_sos_post(self):
        """Prueba 4: Endpoint REST POST /api/v1/emergency/sos."""
        payload = {
            "phone": "04245554433",
            "latitude": 10.502078,
            "longitude": -66.843345,
            "accuracy_meters": 1.8,
            "altitude_meters": 940.0,
            "heading_degrees": 90.0,
            "source_channel": "PWA_SOS_HIGH_ACCURACY"
        }

        code, hdrs, body = self.service.dispatch(
            method="POST",
            path="/api/v1/emergency/sos",
            headers={"Content-Type": "application/json"},
            body_bytes=json.dumps(payload).encode("utf-8")
        )

        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "LOCALIZADO")
        self.assertTrue(data["is_sub_5m"])
        self.assertEqual(data["plus_code"], "772MG524+RMH")
        self.assertIn("maps_url", data)
        self.assertIn("waze_url", data)

    def test_05_http_rest_endpoint_sos_get_ui(self):
        """Prueba 5: Endpoint GET /sos sirviendo la interfaz PWA de alta precisión."""
        code, hdrs, body = self.service.dispatch(
            method="GET",
            path="/sos",
            headers={},
            body_bytes=b""
        )
        self.assertEqual(code, 200)
        self.assertIn("text/html", hdrs.get("Content-Type", ""))
        html = body.decode("utf-8")
        self.assertIn("enableHighAccuracy: true", html)
        self.assertIn("watchPosition", html)
        self.assertIn("computePlusCode11D", html)

    def test_06_territorial_boundary_guard(self):
        """Prueba 6: Rechazo y alerta preventiva de coordenadas fuera de Venezuela."""
        madrid_lat, madrid_lon = 40.4168, -3.7038
        res = self.dispatcher.process_high_precision_emergency(
            phone="04169998877",
            lat=madrid_lat,
            lon=madrid_lon,
            accuracy_meters=2.0
        )
        self.assertEqual(res["status"], "RECIBIDO")
        self.assertFalse(res["is_venezuela"])
        self.assertIn("FUERA DEL TERRITORIO NACIONAL", res["response_text"])


if __name__ == "__main__":
    unittest.main()
