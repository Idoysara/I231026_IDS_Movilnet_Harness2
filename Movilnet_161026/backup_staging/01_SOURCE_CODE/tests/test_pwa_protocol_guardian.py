#!/usr/bin/env python3
"""
tests/test_pwa_protocol_guardian.py — Suite Automatizada del Guardián del Protocolo PWA
======================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: 100% Pass)
Protocolo Maestro Decagonal (Fase 6: Testing Integral & Fase 7: Pureza AST)
"""

import os
import sys
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pwa_protocol_guardian import PWAProtocolGuardian, run_self_verification
from mcp.pwa_protocol_mcp import (
    mcp_pwa_protocol_audit,
    mcp_pwa_verify_zero_token,
    mcp_pwa_self_test,
    mcp_pwa_sw_bump
)
from core.phone_migration_orchestrator import PhoneMigrationOrchestrator


class TestPWAProtocolGuardian(unittest.TestCase):
    """Batería de pruebas automatizadas del protocolo PWA y su servidor MCP."""

    @classmethod
    def setUpClass(cls):
        cls.guardian = PWAProtocolGuardian(root_dir=PROJECT_ROOT)

    def test_01_detect_active_bot_phone(self):
        """Verifica que el guardián detecte el número activo oficial del bot."""
        bot = self.guardian.detect_active_bot_phone()
        self.assertIsNotNone(bot)
        self.assertIn(bot.international_digits, ["584241533712", "584166251587"])
        self.assertTrue(bot.whatsapp_jid.endswith("@s.whatsapp.net"))

    def test_02_extract_sw_version(self):
        """Verifica la extracción de versión del Service Worker desde sw.js."""
        ver_num, cache_name = self.guardian.extract_sw_version()
        self.assertGreaterEqual(ver_num, 1)
        self.assertIn("network-first", cache_name)
        self.assertIn(f"v{ver_num}", cache_name)

    def test_03_contrast_ratio_wcag(self):
        """Verifica el cálculo formal de luminancia y ratio de contraste según W3C WCAG 2.1."""
        ratio = self.guardian._calculate_contrast_ratio("#0B1C30", "#FF6600")
        self.assertGreaterEqual(ratio, 3.0)  # Mínimo AA para UI
        self.assertAlmostEqual(ratio, 5.85, delta=0.2)

    def test_04_session_token_hmac_sha256(self):
        """Verifica que los tokens de sesión sean deterministas, de 16 caracteres hex y Cero-PII."""
        token = self.guardian._generate_sample_session_token("04142554590")
        self.assertEqual(len(token), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in token))

    def test_05_audit_pwa_protocol_full_pass(self):
        """Verifica que la auditoría de 14 puntos del protocolo PWA pase al 100%."""
        report = self.guardian.audit_pwa_protocol()
        self.assertTrue(report.is_synchronized, "El protocolo PWA debe estar 100% sincronizado")
        self.assertEqual(report.failed_checks, 0, "No debe existir ningún fallo en la auditoría PWA")
        self.assertGreaterEqual(report.total_checks, 14)
        self.assertEqual(report.passed_checks, report.total_checks)
        self.assertEqual(len(report.sha256_seal), 64)

    def test_06_verify_zero_token_pipeline(self):
        """Verifica que el pipeline PWA opere con 0 tokens y latencia sub-15ms."""
        res = self.guardian.verify_zero_token_pipeline("04160000001")
        self.assertTrue(res.get("success"), f"Falla en verificación zero-token: {res}")
        self.assertTrue(res.get("zero_token_compliance"))
        self.assertTrue(res.get("fast_path_sub_15ms"))
        cases = res.get("cases", [])
        self.assertGreaterEqual(len(cases), 3)
        for c in cases:
            self.assertEqual(c["tokens_consumed"], 0)
            self.assertLess(c["latency_ms"], 15.0)

    def test_07_mcp_pwa_protocol_tools(self):
        """Verifica que las herramientas del Servidor MCP retornen estructura válida."""
        audit_res = mcp_pwa_protocol_audit()
        self.assertEqual(audit_res.get("service"), "pwa_protocol_mcp")
        self.assertEqual(audit_res.get("status"), "operational")
        self.assertTrue(audit_res["audit_report"]["is_synchronized"])

        zero_res = mcp_pwa_verify_zero_token()
        self.assertTrue(zero_res["result"]["success"])

        test_res = mcp_pwa_self_test()
        self.assertTrue(test_res["success"])

    def test_08_self_verification_runner(self):
        """Verifica la ejecución del auto-test matemático formal del módulo."""
        passed = run_self_verification()
        self.assertTrue(passed)

    def test_09_orchestrator_layer_detection(self):
        """Verifica que el orquestador identifique la capa UI_FRONTEND de la PWA."""
        orch = PhoneMigrationOrchestrator(root_dir=PROJECT_ROOT)
        plan = orch.analyze_plan("0424-1533712", "0416-6251587")
        self.assertGreater(len(plan.components), 0)
        pwa_components = [c for c in plan.components if c.layer == "UI_FRONTEND"]
        self.assertGreaterEqual(len(pwa_components), 3)
        target_ids = [c.target_id for c in pwa_components]
        self.assertIn("ui/pwa_stitch/simulador.html", target_ids)
        self.assertIn("ui/pwa_stitch/index.html", target_ids)

    def test_10_prospect_and_chat_routes(self):
        """Verifica que las rutas /prospect y /chat sirvan la PWA Stitch con HTTP 200."""
        from api.service import MovilnetAPIService
        srv = MovilnetAPIService()
        status, headers, body = srv.dispatch("GET", "/prospect?carrier=movistar&token=425545904gmax", {}, b"")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertGreater(len(body), 50000)

    def test_11_pwa_exclusive_return_channel_and_zero_whatsapp_leakage(self):
        """
        Verifica que:
        1. Las interacciones PWA retornen 100% por el canal de respuesta HTTP (Data PWA).
        2. Cero fugas hacia WhatsApp o n8n cuando el canal es PWA.
        3. El número del bot sea exclusivamente el aprobado (0424-1533712 / MOVI).
        4. Erradicación total de WdWU8G9EggQDMack y 0416-6251587.
        """
        from api.service import MovilnetAPIService
        from core.n8n_webhook_resolver import dispatch_to_n8n_with_retry, APPROVED_BOT_PHONE, APPROVED_BOT_NAME
        srv = MovilnetAPIService()

        # 1. PWA message handling
        pwa_req = {
            "text": "Hola deseo consultar mis planes",
            "phone": "04142554590",
            "channel": "pwa_mobile",
            "is_pwa": True
        }
        status, payload = srv.handle_customer_care_agent(pwa_req)
        self.assertEqual(status, 200)
        self.assertEqual(payload.get("channel"), "pwa_mobile")
        self.assertEqual(payload.get("mode"), "DATA_PWA_EXCLUSIVE")
        self.assertEqual(payload.get("bot_phone"), APPROVED_BOT_PHONE)
        self.assertEqual(payload.get("bot_name"), APPROVED_BOT_NAME)
        self.assertIn("reply", payload)
        self.assertGreater(len(payload["reply"]), 10)

        # 2. PWA payload isolation in n8n resolver
        n8n_pwa_payload = {
            "channel": "pwa_mobile",
            "phone": "04142554590",
            "text": "Prueba de aislamiento PWA"
        }
        res = dispatch_to_n8n_with_retry(n8n_pwa_payload)
        self.assertTrue(res.get("skipped_by_pwa_isolation"))
        self.assertEqual(res.get("mode"), "DATA_PWA_EXCLUSIVE")

        # 3. Legacy phone eradication in resolver
        legacy_payload = {
            "event": "messages.upsert",
            "sender": "584166251587@s.whatsapp.net",
            "channel": "whatsapp"
        }
        dispatch_to_n8n_with_retry(legacy_payload)
        self.assertEqual(legacy_payload["sender"], "584241533712@s.whatsapp.net")


if __name__ == "__main__":
    unittest.main()

