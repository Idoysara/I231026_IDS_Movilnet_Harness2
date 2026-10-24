"""
Módulo Autónomo de Despacho Multimodal — Suite de Pruebas: Cliente WhatsApp Resiliente
Gobernanza: Universal Best Practices Engineering Rule (Pilares IV, V, VI)
"""

import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from domain.enums import MediaType
from infrastructure.whatsapp_client import (
    WhatsAppMultimodalClient,
    CircuitBreaker,
    CircuitBreakerState,
    mask_phone_pii,
    ensure_pwa_link,
    OFFICIAL_PWA_URL
)


class FakeHttpResponse:
    def __init__(self, code: int = 200, data: dict = None):
        self.code = code
        self.bytes_data = json.dumps(data or {}).encode("utf-8")

    def getcode(self):
        return self.code

    def read(self):
        return self.bytes_data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestWhatsAppMultimodalClient(unittest.TestCase):
    """Pruebas unitarias para el cliente WhatsApp y Circuit Breaker."""

    def test_zero_pii_masking(self):
        """Verifica enmascaramiento estricto de números telefónicos (Pilar VI)."""
        self.assertEqual(mask_phone_pii("+584166251587"), "+58416***1587")
        self.assertEqual(mask_phone_pii("04121234567"), "041212***4567")
        self.assertEqual(mask_phone_pii("12345"), "12***")
        self.assertEqual(mask_phone_pii(""), "")

    def test_ensure_pwa_link(self):
        """Verifica la Regla Inviolable de Enlace PWA Universal."""
        text_without = "Estimado cliente, su saldo ha sido consultado."
        result = ensure_pwa_link(text_without)
        self.assertIn(OFFICIAL_PWA_URL, result)
        self.assertTrue(result.endswith(OFFICIAL_PWA_URL))

        # Ya contiene el enlace: no duplicar
        text_with = f"Consulta aquí: {OFFICIAL_PWA_URL}"
        result_same = ensure_pwa_link(text_with)
        self.assertEqual(result_same, text_with)
        self.assertEqual(result_same.count(OFFICIAL_PWA_URL), 1)

    def test_mock_dispatch_media_and_text(self):
        """Verifica despacho hermético en modo mock."""
        client = WhatsAppMultimodalClient(mode="mock")
        res_media = client.dispatch_media_message(
            phone_number="+584166251587",
            media_type=MediaType.DOCUMENT,
            media_url_or_path="vaults/recibo.pdf",
            caption="Tu recibo de recarga"
        )
        self.assertTrue(res_media["success"])
        self.assertEqual(res_media["mode"], "MOCK_DISPATCH")
        self.assertIn("wamid_mock", res_media["message_id"])

        res_text = client.dispatch_text_message(
            phone_number="+584166251587",
            text="Hola Movilnet"
        )
        self.assertTrue(res_text["success"])
        self.assertEqual(len(client.outbox_history), 2)

    def test_disabled_mode(self):
        """Verifica que en modo disabled no se realiza despacho."""
        client = WhatsAppMultimodalClient(mode="disabled")
        res = client.dispatch_text_message("+584166251587", "Hola")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "DISABLED")
        self.assertEqual(len(client.outbox_history), 1)

    def test_circuit_breaker_lifecycle(self):
        """Verifica ciclo CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
        cb = CircuitBreaker(failure_threshold=2, recovery_time_seconds=0.1)
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertTrue(cb.allow_request())

        # 1er fallo
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 1)

        # 2do fallo -> activa OPEN
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)
        self.assertFalse(cb.allow_request())

        # Esperar recuperación temporal
        import time
        time.sleep(0.12)
        # Siguiente petición transiciona a HALF_OPEN
        self.assertTrue(cb.allow_request())
        self.assertEqual(cb.state, CircuitBreakerState.HALF_OPEN)

        # Éxito en HALF_OPEN restablece a CLOSED
        cb.record_success()
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    def test_circuit_breaker_blocks_when_open(self):
        """Verifica rechazo inmediato cuando el circuito está abierto."""
        cb = CircuitBreaker(failure_threshold=1, recovery_time_seconds=60.0)
        cb.record_failure()  # Pasa a OPEN
        client = WhatsAppMultimodalClient(mode="webhook", circuit_breaker=cb)

        res = client.dispatch_text_message("+584166251587", "Hola")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "CIRCUIT_OPEN")

    def test_live_dispatch_success_with_requester(self):
        """Verifica despacho HTTP 200 con deserialización de message_id."""
        fake_response_data = {
            "messaging_product": "whatsapp",
            "messages": [{"id": "wamid_live_998877"}]
        }
        mock_req = lambda req, timeout: FakeHttpResponse(200, fake_response_data)

        client = WhatsAppMultimodalClient(
            mode="meta_cloud",
            api_url="https://graph.facebook.com/v20.0",
            phone_number_id="1002345678",
            http_requester=mock_req
        )

        res = client.dispatch_text_message("+584166251587", "Mensaje exitoso")
        self.assertTrue(res["success"])
        self.assertEqual(res["message_id"], "wamid_live_998877")
        self.assertEqual(res["status"], "DELIVERED")

    def test_exponential_backoff_recovery(self):
        """Verifica reintentos y recuperación ante error HTTP 500 transitorio."""
        call_count = {"val": 0}

        def mock_requester(req, timeout):
            call_count["val"] += 1
            if call_count["val"] < 3:
                raise urllib.error.HTTPError(
                    req.full_url, 500, "Internal Server Error", {}, io.BytesIO(b'{"error": "busy"}')
                )
            return FakeHttpResponse(200, {"messages": [{"id": "wamid_recovered"}]})

        client = WhatsAppMultimodalClient(
            mode="webhook",
            api_url="https://mock-gateway.movilnet.com.ve/webhook",
            max_retries=3,
            base_delay_seconds=0.01,
            http_requester=mock_requester
        )

        res = client.dispatch_text_message("+584166251587", "Prueba con retry")
        self.assertTrue(res["success"])
        self.assertEqual(res["message_id"], "wamid_recovered")
        self.assertEqual(call_count["val"], 3)

    def test_client_error_400_no_retry(self):
        """Verifica que errores 4xx no se reintentan y marcan fallo."""
        call_count = {"val": 0}

        def mock_requester(req, timeout):
            call_count["val"] += 1
            raise urllib.error.HTTPError(
                req.full_url, 400, "Bad Request", {}, io.BytesIO(b'{"error": "invalid parameter"}')
            )

        client = WhatsAppMultimodalClient(
            mode="webhook",
            api_url="https://mock-gateway.movilnet.com.ve/webhook",
            max_retries=3,
            base_delay_seconds=0.01,
            http_requester=mock_requester
        )

        res = client.dispatch_text_message("+584166251587", "Error cliente")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "CLIENT_ERROR")
        self.assertEqual(res["status_code"], 400)
        self.assertEqual(call_count["val"], 1, "No debió reintentar un error 400")

    def test_url_resolution(self):
        """Verifica que la URL se arme adecuadamente según el modo."""
        cli_meta = WhatsAppMultimodalClient(
            mode="meta_cloud",
            api_url="https://graph.facebook.com/v20.0",
            phone_number_id="PHONE_ID_123"
        )
        self.assertEqual(
            cli_meta._resolve_target_url(),
            "https://graph.facebook.com/v20.0/PHONE_ID_123/messages"
        )

        cli_stage = WhatsAppMultimodalClient(
            mode="webhook",
            api_url="http://127.0.0.1:8025/webhook-stage"
        )
        self.assertEqual(
            cli_stage._resolve_target_url(),
            "http://127.0.0.1:8025/webhook-stage"
        )


if __name__ == "__main__":
    unittest.main()
