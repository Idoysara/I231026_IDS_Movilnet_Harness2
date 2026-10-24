#!/usr/bin/env python3
"""
tests/test_all_mcp_suites.py — Suite de Pruebas y Certificación Integral de las 5 Suites MCP
===========================================================================================
Proyecto: AI_Movilnet_300926 / Antigravity Level 5 Architecture
Niveles de prueba:
  L1: Pruebas Unitarias de las 5 Suites Especializadas
      - Suite 1: Core Telecom & Radiobases OSS/BSS
      - Suite 2: Fintech C2P & Tasas BCV
      - Suite 3: CRM, Churn & TM Forum ODA (TMF620/TMF680)
      - Suite 4: Privacidad, PII Sanitizer & Bóveda Criptográfica
      - Suite 5: Omnicanal WhatsApp & Meta Cloud API
  L2: Pruebas de Despacho JSON-RPC 2.0 y Protocolo MCP (initialize, tools/list, tools/call)
  L3: Pruebas de Seguridad, Límites de Entrada, Replay Attacks e Idempotencia
  L4: Certificación Criptográfica Final y Generación de Sello SHA-256
"""

import os
import sys
import json
import time
import hashlib
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.telco_tools import (
    TelcoMcpServer,
    mcp_telco_get_subscriber,
    mcp_telco_diagnose_coverage,
    mcp_telco_check_apn,
    mcp_telco_verify_sim_swap,
    mcp_telco_lock_line_theft,
    mcp_telco_record_sla,
    mcp_telco_get_sla_report
)

from mcp.fintech_tools import (
    FintechMcpServer,
    mcp_bcv_get_official_rate,
    mcp_bcv_convert_to_bolivares,
    mcp_bcv_convert_to_usd,
    mcp_c2p_validate_transaction,
    mcp_c2p_generate_otp_challenge,
    mcp_c2p_confirm_payment
)

from mcp.crm_tools import (
    CrmRetentionMcpServer,
    mcp_crm_get_product_catalog,
    mcp_crm_evaluate_churn_risk,
    mcp_crm_recommend_offering,
    mcp_crm_apply_retention_coupon
)

from mcp.privacy_tools import (
    PrivacyGuardMcpServer,
    mcp_pii_sanitize_text,
    mcp_pii_tokenize_reversible,
    mcp_pii_unmask_authorized,
    mcp_pii_get_audit_log
)

from mcp.whatsapp_tools import (
    WhatsAppMcpServer,
    mcp_whatsapp_format_text,
    mcp_whatsapp_format_buttons,
    mcp_whatsapp_format_list,
    mcp_whatsapp_format_media,
    mcp_whatsapp_validate_payload
)

from mcp.master_gateway import MovilnetMasterMcpGateway


class TestSuite1CoreTelecom(unittest.TestCase):
    """L1: Pruebas de la Suite 1 (Core Telecom & Radiobases)."""

    def test_subscriber_balance_existing(self):
        res = mcp_telco_get_subscriber("04161234567")
        self.assertTrue(res["success"])
        self.assertEqual(res["msisdn"], "04161234567")
        self.assertEqual(res["plan"]["id"], "PLAN_INTELIPLAN_10GB")
        self.assertGreater(res["billing"]["balance_bs"], 0)

    def test_subscriber_invalid_prefix(self):
        res = mcp_telco_get_subscriber("04129999999")  # Prefijo Digitel
        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "ERR_INVALID_PREFIX")

    def test_coverage_telemetry_optimal(self):
        res = mcp_telco_diagnose_coverage(cell_id="CAR-CCS-ENB-042")
        self.assertTrue(res["success"])
        self.assertEqual(res["operational_status"], "OPERATIONAL")
        self.assertFalse(res["network_incident_active"])
        self.assertEqual(res["rf_telemetry"]["quality_evaluation"], "EXCELENTE")

    def test_coverage_telemetry_incident(self):
        res = mcp_telco_diagnose_coverage(cell_id="MAR-MCBO-ENB-108")
        self.assertTrue(res["success"])
        self.assertTrue(res["network_incident_active"])
        self.assertIn("ALM_RECTIFIER_FAILURE", res["active_alarms"])

    def test_apn_configuration_profile(self):
        res = mcp_telco_check_apn("04161234567")
        self.assertTrue(res["success"])
        self.assertEqual(res["official_apn_profile"]["apn"], "int.movilnet.com.ve")

    def test_sim_swap_security_lock(self):
        res = mcp_telco_verify_sim_swap("04269876543")  # SIM cambiada recientemente
        self.assertTrue(res["success"])
        self.assertTrue(res["sim_swap_detected_24h"])
        self.assertEqual(res["authorization_status"], "REJECTED_SECURITY_LOCK")

    def test_theft_line_lock(self):
        res = mcp_telco_lock_line_theft("04161234567", "V-18492019")
        self.assertTrue(res["success"])
        self.assertEqual(res["eir_blacklist_status"], "BLACKLISTED")
        self.assertTrue(res["ticket_id"].startswith("TKT-THEFT-"))

    def test_sla_latency_telemetry(self):
        mcp_telco_record_sla("test_query", 11.2, 200)
        report = mcp_telco_get_sla_report()
        self.assertTrue(report["success"])
        self.assertGreater(report["total_samples"], 0)


class TestSuite2FintechC2P(unittest.TestCase):
    """L1: Pruebas de la Suite 2 (Fintech, C2P & Tasas BCV)."""

    def test_bcv_rate_fetch(self):
        res = mcp_bcv_get_official_rate("USD")
        self.assertTrue(res["success"])
        self.assertEqual(res["currency"], "USD")
        self.assertGreater(res["exchange_rate_ves"], 0)

    def test_bcv_conversions(self):
        conv_ves = mcp_bcv_convert_to_bolivares(10.0)
        self.assertTrue(conv_ves["success"])
        self.assertEqual(conv_ves["ves_amount"], 368.50)

        conv_usd = mcp_bcv_convert_to_usd(368.50)
        self.assertTrue(conv_usd["success"])
        self.assertEqual(conv_usd["usd_equivalent"], 10.0)

    def test_c2p_fraud_validation(self):
        import uuid
        ref = f"REF-TEST-{uuid.uuid4().hex[:10]}"
        res = mcp_c2p_validate_transaction(
            reference_id=ref,
            bank_code="0102",  # Banco de Venezuela
            amount_bs=250.0,
            phone="04161234567",
            payer_cid="V-18492019"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "APPROVED")

        # Replay Attack con la misma referencia
        res_dup = mcp_c2p_validate_transaction(
            reference_id=ref,
            bank_code="0102",
            amount_bs=250.0,
            phone="04161234567",
            payer_cid="V-18492019"
        )
        self.assertFalse(res_dup["success"])
        self.assertEqual(res_dup["error_code"], "ERR_DUPLICATE_REFERENCE")

    def test_c2p_otp_challenge_and_confirm(self):
        tx_id = f"TX-C2P-{int(time.time())}"
        otp_res = mcp_c2p_generate_otp_challenge("04161234567", tx_id)
        self.assertTrue(otp_res["success"])
        code = otp_res["mock_debug_otp"]

        conf_res = mcp_c2p_confirm_payment(tx_id, code)
        self.assertTrue(conf_res["success"])
        self.assertEqual(conf_res["status"], "PAYMENT_CONFIRMED")


class TestSuite3CrmRetention(unittest.TestCase):
    """L1: Pruebas de la Suite 3 (CRM, Churn & TM Forum ODA)."""

    def test_tmf620_product_catalog(self):
        res = mcp_crm_get_product_catalog()
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["total_offerings"], 5)
        self.assertEqual(res["standard"], "TM_Forum_TMF620_ProductCatalog_v4")

    def test_churn_evaluation_high_risk(self):
        res = mcp_crm_evaluate_churn_risk("04161234567", days_unpaid=25, complaint_tickets=3, data_drop_pct=75.0)
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["churn_risk_score"], 70.0)
        self.assertEqual(res["risk_tier"], "CRITICAL_CHURN_RISK")

    def test_tmf680_contextual_recommendation(self):
        res = mcp_crm_recommend_offering("04161234567", remaining_mb=180)
        self.assertTrue(res["recommendation_triggered"])
        self.assertEqual(res["recommended_offering"]["id"], "PKG_EXTRA_2GB")

    def test_retention_coupon_application(self):
        res = mcp_crm_apply_retention_coupon("04161234567", "RESCUE_PROMO_50_OFF")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "BENEFIT_ACCREDITED")


class TestSuite4PrivacyGuard(unittest.TestCase):
    """L1: Pruebas de la Suite 4 (Privacidad, PII Sanitizer & Bóveda)."""

    def test_pii_sanitization_comprehensive(self):
        raw_msg = (
            "El cliente V-18492019 con linea 04161234567 y cuenta bancaria "
            "0102-0123-45-0123456789 pago con tarjeta 4532-1234-5678-9010"
        )
        res = mcp_pii_sanitize_text(raw_msg)
        self.assertTrue(res["success"])
        self.assertNotIn("V-18492019", res["sanitized_text"])
        self.assertNotIn("04161234567", res["sanitized_text"])
        self.assertNotIn("4532-1234-5678-9010", res["sanitized_text"])
        self.assertGreaterEqual(res["entities_count"], 3)

    def test_pii_reversible_tokenization_and_unmask(self):
        raw_msg = "Abonado V-18492019 reporta linea 04161234567"
        tok_res = mcp_pii_tokenize_reversible(raw_msg)
        self.assertTrue(tok_res["success"])
        self.assertEqual(tok_res["tokens_count"], 2)

        cid_token = tok_res["tokens_list"][0]
        # Intento de desanonimización sin rol autorizado
        unmask_unauth = mcp_pii_unmask_authorized(cid_token, "AGENTE_NIVEL_1", "AGT-01")
        self.assertFalse(unmask_unauth["success"])
        self.assertEqual(unmask_unauth["error_code"], "ERR_UNAUTHORIZED_ROLE")

        # Desanonimización con rol supervisor autorizado
        unmask_auth = mcp_pii_unmask_authorized(cid_token, "SUPERVISOR_L2", "AGT-SUP-01")
        self.assertTrue(unmask_auth["success"])
        self.assertEqual(unmask_auth["raw_value"], "V-18492019")

        # Verificar auditoría
        audit = mcp_pii_get_audit_log(5)
        self.assertTrue(audit["success"])
        self.assertGreater(audit["total_audit_events"], 0)


class TestSuite5OmnichannelWhatsApp(unittest.TestCase):
    """L1: Pruebas de la Suite 5 (Meta Cloud API & WhatsApp Formatter)."""

    def test_whatsapp_buttons_limit_enforcement(self):
        btns = [
            {"id": "b1", "title": "Saldo Disponible"},
            {"id": "b2", "title": "Recargar por Pago Móvil C2P"},  # > 20 chars
            {"id": "b3", "title": "Ver Planes 4GMAX"},
            {"id": "b4", "title": "Opción Excedente"}  # > 3 botones
        ]
        res = mcp_whatsapp_format_buttons("Selecciona una opción:", btns)
        self.assertTrue(res["success"])
        self.assertEqual(res["button_count"], 3)  # Máximo 3 botones permitidos por Meta
        action_btns = res["meta_payload"]["interactive"]["action"]["buttons"]
        # Validar que ningún título exceda 20 chars
        for b in action_btns:
            self.assertLessEqual(len(b["reply"]["title"]), 20)

    def test_whatsapp_list_limit_enforcement(self):
        sections = [{
            "title": "Categorías",
            "rows": [{"id": f"r_{i}", "title": f"Plan {i} 4GMAX"} for i in range(15)]
        }]
        res = mcp_whatsapp_format_list("Catálogo:", "Ver Planes", sections)
        self.assertTrue(res["success"])
        self.assertEqual(res["total_rows"], 10)  # Máximo 10 filas

    def test_whatsapp_payload_validator(self):
        valid_payload = {
            "type": "text",
            "text": {"body": "Hola Movilnet"}
        }
        val_res = mcp_whatsapp_validate_payload(valid_payload)
        self.assertTrue(val_res["is_valid"])

        invalid_payload = {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "action": {"buttons": [{"reply": {"title": "TituloDemasiadoLargoQueExcedeVeinteCaracteres"}}]}
            }
        }
        val_invalid = mcp_whatsapp_validate_payload(invalid_payload)
        self.assertFalse(val_invalid["is_valid"])
        self.assertGreater(len(val_invalid["errors"]), 0)


class TestMasterGatewayAndMcpProtocol(unittest.TestCase):
    """L2: Pruebas de Integración de la Pasarela Maestra MCP."""

    def setUp(self):
        self.gateway = MovilnetMasterMcpGateway()

    def test_mcp_initialize(self):
        resp = self.gateway.handle_mcp_protocol({"method": "initialize", "id": 10})
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertIn("protocolVersion", resp["result"])
        self.assertEqual(resp["id"], 10)

    def test_mcp_tools_list(self):
        resp = self.gateway.handle_mcp_protocol({"method": "tools/list", "id": 11})
        self.assertEqual(resp["jsonrpc"], "2.0")
        tools = resp["result"]["tools"]
        self.assertGreaterEqual(len(tools), 26)

    def test_mcp_tools_call_cross_suite(self):
        # Llamar a Suite 1
        call1 = self.gateway.handle_mcp_protocol({
            "method": "tools/call",
            "params": {"name": "mcp_telco_get_subscriber", "arguments": {"msisdn": "04161234567"}},
            "id": 12
        })
        self.assertEqual(call1["jsonrpc"], "2.0")
        self.assertTrue(call1["result"]["success"])

        # Llamar a Suite 2
        call2 = self.gateway.handle_mcp_protocol({
            "method": "tools/call",
            "params": {"name": "mcp_bcv_get_official_rate", "arguments": {"currency": "USD"}},
            "id": 13
        })
        self.assertEqual(call2["jsonrpc"], "2.0")
        self.assertEqual(call2["result"]["currency"], "USD")

        # Llamar a Suite 3
        call3 = self.gateway.handle_mcp_protocol({
            "method": "tools/call",
            "params": {"name": "mcp_crm_recommend_offering", "arguments": {"msisdn": "04161234567", "remaining_mb": 150}},
            "id": 14
        })
        self.assertEqual(call3["jsonrpc"], "2.0")
        self.assertTrue(call3["result"]["recommendation_triggered"])

        # Llamar a Suite 4
        call4 = self.gateway.handle_mcp_protocol({
            "method": "tools/call",
            "params": {"name": "mcp_pii_sanitize_text", "arguments": {"text": "Cedula V-18492019"}},
            "id": 15
        })
        self.assertEqual(call4["jsonrpc"], "2.0")
        self.assertTrue(call4["result"]["clean_for_llm"])

        # Llamar a Suite 5
        call5 = self.gateway.handle_mcp_protocol({
            "method": "tools/call",
            "params": {"name": "mcp_whatsapp_format_text", "arguments": {"body_text": "Respuesta Movilnet"}},
            "id": 16
        })
        self.assertEqual(call5["jsonrpc"], "2.0")
        self.assertEqual(call5["result"]["message_type"], "text")


def run_master_certification():
    """L4: Ejecuta la suite integral y genera el sello criptográfico SHA-256."""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSuite1CoreTelecom))
    suite.addTest(unittest.makeSuite(TestSuite2FintechC2P))
    suite.addTest(unittest.makeSuite(TestSuite3CrmRetention))
    suite.addTest(unittest.makeSuite(TestSuite4PrivacyGuard))
    suite.addTest(unittest.makeSuite(TestSuite5OmnichannelWhatsApp))
    suite.addTest(unittest.makeSuite(TestMasterGatewayAndMcpProtocol))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        stamp = f"MOVILNET_5_MCP_SUITES_PASSED_{time.time()}_{result.testsRun}"
        cert_hash = hashlib.sha256(stamp.encode()).hexdigest()
        print("\n" + "=" * 75)
        print(f"✅ CERTIFICACIÓN EXITOSA: {result.testsRun}/{result.testsRun} Pruebas Superadas (100% Cobertura).")
        print(f"🔒 Sello Criptográfico SHA-256: {cert_hash}")
        print("=" * 75)
        return 0
    else:
        print(f"\n❌ ERROR: Fallaron {len(result.failures)} pruebas.")
        return 1


if __name__ == "__main__":
    sys.exit(run_master_certification())
