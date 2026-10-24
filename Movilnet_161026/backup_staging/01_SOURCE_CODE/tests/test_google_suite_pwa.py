#!/usr/bin/env python3
"""
tests/test_google_suite_pwa.py — Pruebas de Integración Google Suite ↔ PWA ↔ n8n
================================================================================
Verifica el ciclo completo de despacho desde la PWA hacia los servicios de
Google Suite (Gmail, Google Calendar, Google Drive) mediante los nodos de n8n.
"""

import json
import unittest
from api.service import MovilnetAPIService
from api.agents.agent_customer_care import IntentType


class TestGoogleSuitePWAIntegration(unittest.TestCase):
    """Pruebas funcionales de los flujos de Google Suite y autoservicio PWA."""

    def setUp(self):
        self.service = MovilnetAPIService()
        self.test_phone = "04160000001"

    def test_pwa_static_html_served(self):
        """Verifica que la PWA se sirva con código 200 y contenga los selectores."""
        status, headers, body = self.service.dispatch(
            "GET",
            "/ui/pwa/index.html",
            {},
            b""
        )
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn(b"pwa-phone-select", body)
        self.assertIn(b"Sugerencias de prueba", body)

    def test_pwa_static_js_served(self):
        """Verifica que el archivo pwa.js se sirva correctamente con helpers de prueba."""
        status, headers, body = self.service.dispatch(
            "GET",
            "/ui/pwa/js/pwa.js",
            {},
            b""
        )
        self.assertEqual(status, 200)
        self.assertIn(b"switchPwaSubscriber", body)
        self.assertIn(b"sendQuickPrompt", body)

    def test_gmail_receipt_flow(self):
        """Verifica el despacho de recibo digital a Gmail mediante n8n."""
        payload = {
            "text": "Quiero recibir mi recibo o factura por correo a cliente.prueba@gmail.com",
            "msisdn": self.test_phone,
            "channel": "whatsapp"
        }
        status, headers, body = self.service.dispatch(
            "POST",
            "/api/v1/agents/customer-care/process",
            {"Content-Type": "application/json"},
            json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(status, 200)
        res = json.loads(body.decode("utf-8"))
        self.assertEqual(res.get("intent"), IntentType.GOOGLE_SUITE_DISPATCH.value)
        self.assertIn("cliente.prueba@gmail.com", res.get("response_text", ""))
        self.assertIn("Gmail Send Receipt", res.get("response_text", ""))
        self.assertIn("FAST_PATH", res.get("execution_mode", ""))
        self.assertTrue(len(res.get("interactive_options", [])) > 0)

    def test_calendar_booking_flow(self):
        """Verifica agendamiento de cita en Google Calendar mediante n8n."""
        payload = {
            "text": "Agenda una cita en el calendario para visitar la oficina El Rosal",
            "msisdn": self.test_phone,
            "channel": "pwa-app-window"
        }
        status, headers, body = self.service.dispatch(
            "POST",
            "/api/v1/agents/customer-care/process",
            {"Content-Type": "application/json"},
            json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(status, 200)
        res = json.loads(body.decode("utf-8"))
        self.assertEqual(res.get("intent"), IntentType.GOOGLE_SUITE_DISPATCH.value)
        self.assertIn("Google Calendar Create", res.get("response_text", ""))
        self.assertIn("El Rosal", res.get("response_text", ""))

    def test_drive_backup_flow(self):
        """Verifica respaldo digital en Google Drive mediante n8n."""
        payload = {
            "text": "Guarda mi contrato digital en Google Drive",
            "msisdn": self.test_phone,
            "channel": "web"
        }
        status, headers, body = self.service.dispatch(
            "POST",
            "/api/v1/agents/customer-care/process",
            {"Content-Type": "application/json"},
            json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(status, 200)
        res = json.loads(body.decode("utf-8"))
        self.assertEqual(res.get("intent"), IntentType.GOOGLE_SUITE_DISPATCH.value)
        self.assertIn("Drive Upload Document", res.get("response_text", ""))
        self.assertIn("Google Drive", res.get("response_text", ""))


if __name__ == "__main__":
    unittest.main()
