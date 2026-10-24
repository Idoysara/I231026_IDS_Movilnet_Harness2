#!/usr/bin/env python3
"""
tests/test_whatsapp_enterprise_gateway.py — Suite de Verificación de Pasarela WhatsApp Empresarial
==================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)
"""

import unittest
import json
import time
import hmac
import hashlib
from core.whatsapp_enterprise_gateway import (
    WhatsAppGatewayMode,
    WhatsAppDeliveryStatus,
    WhatsAppOutgoingMessage,
    WhatsAppDispatchResult,
    MetaCloudApiAdapter,
    EvolutionBaileysAdapter,
    WhatsAppEnterpriseRouter
)
from scripts.whatsapp_keepalive_watchdog import WhatsAppKeepaliveWatchdog


class TestWhatsAppEnterpriseGateway(unittest.TestCase):
    """Verificación integral de la arquitectura WhatsApp sin dependencia de teléfono físico."""

    def setUp(self):
        self.meta_adapter = MetaCloudApiAdapter(
            phone_number_id="10004241533712",
            access_token="TEST_META_TOKEN_PROD",
            verify_token="MOVILNET_TEST_VERIFY_TOKEN",
            app_secret="test_secret_key_123"
        )
        self.evolution_adapter = EvolutionBaileysAdapter(
            server_url="http://evolution:8080",
            instance_name="Viki LPGTEC",
            api_key="test_evo_key"
        )
        self.router = WhatsAppEnterpriseRouter(
            mode=WhatsAppGatewayMode.HYBRID_AUTO_FAILOVER,
            meta_adapter=self.meta_adapter,
            evolution_adapter=self.evolution_adapter
        )

    def test_01_outgoing_message_e164_sanitization(self):
        """Valida que formatos 0414..., 414... y con @s.whatsapp.net se normalicen a 58414..."""
        m1 = WhatsAppOutgoingMessage(recipient_phone="0414-2554590", text_content="Hola Ids")
        self.assertEqual(m1.recipient_phone, "584142554590")

        m2 = WhatsAppOutgoingMessage(recipient_phone="584241533712@s.whatsapp.net", text_content="Mensaje bot")
        self.assertEqual(m2.recipient_phone, "584241533712")

        m3 = WhatsAppOutgoingMessage(recipient_phone="4161234567", text_content="Mensaje corto")
        self.assertEqual(m3.recipient_phone, "584161234567")

    def test_02_invariant_rejection_guards(self):
        """Valida el rechazo inmediato de entradas malformadas o vacías."""
        with self.assertRaises(ValueError):
            WhatsAppOutgoingMessage(recipient_phone="123", text_content="Texto")

        with self.assertRaises(ValueError):
            WhatsAppOutgoingMessage(recipient_phone="04142554590", text_content="   ")

    def test_03_meta_cloud_api_payload_builder(self):
        """Verifica la serialización exacta requerida por la API oficial de Meta (CERO Celular)."""
        msg = WhatsAppOutgoingMessage(recipient_phone="04142554590", text_content="Prueba Meta")
        payload = self.meta_adapter.build_meta_payload(msg)

        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["recipient_type"], "individual")
        self.assertEqual(payload["to"], "584142554590")
        self.assertEqual(payload["type"], "text")
        self.assertFalse(payload["text"]["preview_url"])
        self.assertEqual(payload["text"]["body"], "Prueba Meta")

    def test_04_meta_webhook_handshake_verification(self):
        """Valida el desafío GET hub.challenge enviado por Meta para autorizar el webhook."""
        # Intento exitoso
        ok, challenge = self.meta_adapter.verify_webhook_handshake({
            "hub.mode": ["subscribe"],
            "hub.verify_token": ["MOVILNET_TEST_VERIFY_TOKEN"],
            "hub.challenge": ["CHALLENGE_CODE_98765"]
        })
        self.assertTrue(ok)
        self.assertEqual(challenge, "CHALLENGE_CODE_98765")

        # Intento con token fraudulento
        bad_ok, _ = self.meta_adapter.verify_webhook_handshake({
            "hub.mode": ["subscribe"],
            "hub.verify_token": ["BAD_TOKEN"],
            "hub.challenge": ["123"]
        })
        self.assertFalse(bad_ok)

    def test_05_meta_webhook_hmac_sha256_signature(self):
        """Valida la verificación criptográfica anti-suplantación en eventos POST de Meta."""
        raw_body = json.dumps({"entry": [{"id": "123"}]}).encode("utf-8")
        valid_sig = "sha256=" + hmac.new(b"test_secret_key_123", raw_body, hashlib.sha256).hexdigest()

        # Firma válida
        is_valid = self.meta_adapter.verify_webhook_signature(
            {"X-Hub-Signature-256": valid_sig},
            raw_body
        )
        self.assertTrue(is_valid)

        # Firma manipulada
        is_invalid = self.meta_adapter.verify_webhook_signature(
            {"X-Hub-Signature-256": "sha256=ffffffffffffffffffffffffff"},
            raw_body
        )
        self.assertFalse(is_invalid)

    def test_06_meta_inbound_event_parser(self):
        """Valida la extracción estructurada de mensajes entrantes desde el JSON oficial de Meta."""
        sample_meta_event = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "10004241533712",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "584241533712", "phone_number_id": "10004241533712"},
                        "contacts": [{"profile": {"name": "Ids Movistar"}, "wa_id": "584142554590"}],
                        "messages": [{
                            "from": "584142554590",
                            "id": "wamid.HBgLNTg0MTQyNTU0NTkwFQIAEhgWM0VCMEY4RjMyMjM1QkIyMjA5MEZCNwA=",
                            "timestamp": "1728905300",
                            "text": {"body": "Consultar saldo"},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        raw_bytes = json.dumps(sample_meta_event).encode("utf-8")
        inbound = self.meta_adapter.parse_inbound_event(raw_bytes)

        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.provider, WhatsAppGatewayMode.META_CLOUD_API)
        self.assertEqual(inbound.sender_phone, "584142554590")
        self.assertEqual(inbound.sender_name, "Ids Movistar")
        self.assertEqual(inbound.text_body, "Consultar saldo")

    def test_07_evolution_baileys_payload_builder(self):
        """Valida que el adaptador Evolution genere linkPreview: false para evitar recortes."""
        msg = WhatsAppOutgoingMessage(recipient_phone="04142554590", text_content="Texto con link https://movilnet.com.ve")
        payload = self.evolution_adapter.build_evolution_payload(msg)

        self.assertEqual(payload["number"], "584142554590")
        self.assertFalse(payload["options"]["linkPreview"])
        self.assertEqual(payload["options"]["presence"], "composing")
        self.assertGreaterEqual(payload["options"]["delay"], 850)

    def test_08_router_mode_switching_and_telemetry(self):
        """Valida conmutación entre modos y precisión de telemetría consolidada."""
        msg = WhatsAppOutgoingMessage(recipient_phone="04142554590", text_content="Reporte de saldo")

        # Despacho en modo META_CLOUD_API
        self.router.set_mode(WhatsAppGatewayMode.META_CLOUD_API)
        self.assertEqual(self.router.mode, WhatsAppGatewayMode.META_CLOUD_API)
        res = self.router.dispatch(msg)

        self.assertIn(res.status, [WhatsAppDeliveryStatus.SERVER_ACK, WhatsAppDeliveryStatus.DELIVERY_ACK])
        self.assertEqual(res.provider_used, WhatsAppGatewayMode.META_CLOUD_API)

        # Verificar reporte de telemetría
        report = self.router.get_telemetry_report()
        self.assertEqual(report["current_mode"], "META_CLOUD_API")
        self.assertEqual(report["total_dispatches"], 1)
        self.assertEqual(report["successful_dispatches"], 1)
        self.assertTrue(len(report["sha256_seal"]) > 10)

    def test_09_watchdog_keepalive_cycle(self):
        """Valida que el watchdog ejecute ciclos de heartbeat y genere sello criptográfico."""
        wd = WhatsAppKeepaliveWatchdog(stuck_threshold_sec=5.0)
        cycle = wd.execute_heartbeat_cycle()

        self.assertIsNotNone(cycle)
        self.assertTrue(cycle.is_socket_responsive)
        self.assertTrue(len(cycle.sha256_seal) == 64)


if __name__ == "__main__":
    unittest.main()
