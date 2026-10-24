#!/usr/bin/env python3
"""
tests/test_api_whatsapp_gateway_endpoints.py — Verificación de Endpoints REST del Gateway WhatsApp
================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)
"""

import unittest
import json
from api.service import MovilnetAPIService


class TestApiWhatsAppGatewayEndpoints(unittest.TestCase):
    """Pruebas de integración de endpoints REST para WhatsApp Enterprise sin teléfono físico."""

    def setUp(self):
        self.service = MovilnetAPIService()

    def test_01_meta_webhook_handshake_endpoint_success(self):
        """GET /api/v1/whatsapp/webhook responde con el challenge cuando el token coincide."""
        from core.whatsapp_enterprise_gateway import whatsapp_enterprise_gateway
        valid_token = whatsapp_enterprise_gateway.meta_adapter.verify_token
        path = f"/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.verify_token={valid_token}&hub.challenge=77441199"

        code, headers, body = self.service.dispatch(
            method="GET",
            path=path,
            headers={},
            body_bytes=b""
        )
        self.assertEqual(code, 200)
        self.assertEqual(body.decode("utf-8"), "77441199")
        self.assertIn("text/plain", headers.get("Content-Type", ""))

    def test_02_meta_webhook_handshake_endpoint_rejected(self):
        """GET /api/v1/whatsapp/webhook rechaza peticiones con token inválido (HTTP 403)."""
        path = "/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=INVALID_TOKEN&hub.challenge=77441199"
        code, headers, body = self.service.dispatch(
            method="GET",
            path=path,
            headers={},
            body_bytes=b""
        )
        self.assertEqual(code, 403)
        res = json.loads(body.decode("utf-8"))
        self.assertIn("error", res)

    def test_03_gateway_status_endpoint(self):
        """GET /api/v1/whatsapp/gateway-status retorna telemetría y estado de los proveedores."""
        code, headers, body = self.service.dispatch(
            method="GET",
            path="/api/v1/whatsapp/gateway-status",
            headers={},
            body_bytes=b""
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("current_mode", data)
        self.assertIn("meta_provider_health", data)
        self.assertIn("evolution_provider_health", data)
        self.assertFalse(data["meta_provider_health"]["requires_physical_phone"])

    def test_04_watchdog_status_endpoint(self):
        """GET /api/v1/whatsapp/watchdog-status ejecuta ciclo de heartbeat y retorna estado."""
        code, headers, body = self.service.dispatch(
            method="GET",
            path="/api/v1/whatsapp/watchdog-status",
            headers={},
            body_bytes=b""
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("connection_state", data)
        self.assertIn("sha256_seal", data)

    def test_05_gateway_mode_switch_endpoint(self):
        """POST /api/v1/whatsapp/gateway-mode cambia el modo activo en caliente."""
        req_body = json.dumps({"mode": "META_CLOUD_API"}).encode("utf-8")
        code, headers, body = self.service.dispatch(
            method="POST",
            path="/api/v1/whatsapp/gateway-mode",
            headers={"Content-Type": "application/json"},
            body_bytes=req_body
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["new_mode"], "META_CLOUD_API")

    def test_06_whatsapp_send_endpoint(self):
        """POST /api/v1/whatsapp/send despacha mensajes mediante el enrutador enterprise."""
        req_body = json.dumps({
            "to": "04142554590",
            "text": "Prueba de envío corporativo sin celular encendido"
        }).encode("utf-8")

        code, headers, body = self.service.dispatch(
            method="POST",
            path="/api/v1/whatsapp/send",
            headers={"Content-Type": "application/json"},
            body_bytes=req_body
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("status", data)
        self.assertIn("correlation_id", data)

    def test_07_whatsapp_auto_heal_endpoint(self):
        """POST /api/v1/whatsapp/auto-heal dispara ciclo de auto-curación bajo demanda."""
        code, headers, body = self.service.dispatch(
            method="POST",
            path="/api/v1/whatsapp/auto-heal",
            headers={},
            body_bytes=b"{}"
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "auto_heal_executed")
        self.assertIn("cycle_result", data)


if __name__ == "__main__":
    unittest.main()
