#!/usr/bin/env python3
"""
test_phase3_step2_fintech_c2p.py — Suite de Pruebas: Agente Nivel 2 (Fintech C2P)
================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Fase 3: Paso 2 — Pasarela Financiera C2P Pago Móvil, Validación de Tasas BCV & Facturación
Estándares: TM Forum ODA (TMF676 Payment Management, TMF678 Customer Bill Management,
            TMF622 Product Order) / Normativas SUDEBAN & BCV
"""

import sys
import json
import time
import uuid
import unittest
from pathlib import Path
from typing import Dict, Any, List

# Inclusión del directorio raíz
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.agents.agent_fintech_c2p import (
    FintechC2PAgent,
    C2PPaymentRequest,
    C2PPaymentResponse,
    PaymentStatus,
    SUDEBAN_CATALOG,
    DEFAULT_BCV_RATE
)
from api.agents.agent_customer_care import CustomerCareAgent, AgentMessage, IntentType
from api.service import MovilnetAPIService
from api.webhook_bridge import get_webhook_bridge
from db.repository import MovilnetRepository


class TestFintechC2PAgent(unittest.TestCase):
    """Batería de pruebas unitarias y de integración para el Agente Nivel 2 (Fintech C2P)."""

    @classmethod
    def setUpClass(cls):
        cls.repo = MovilnetRepository()
        cls.test_phone = "04169991122"
        cls.test_cid = "V-29991122"

        # Asegurar abonado de prueba en base de datos
        existing = cls.repo.get_subscriber_by_msisdn(cls.test_phone)
        if not existing:
            cls.repo.create_subscriber_with_line(
                cid=cls.test_cid,
                msisdn=cls.test_phone,
                plan_id="PLAN_10GB_4GMAX",
                balance_ves=100.00,
                quota_mb=10240
            )

        cls.agent = FintechC2PAgent(repo=cls.repo)
        cls.customer_care = CustomerCareAgent(repo=cls.repo)
        cls.service = MovilnetAPIService(repository=cls.repo)
        cls.webhook_bridge = get_webhook_bridge()

    def setUp(self):
        # Limpiar caché L1 del agente de atención antes de cada prueba
        self.customer_care.cache.clear()

    # ------------------------------------------------------------------------
    # 1. Pruebas de Procesamiento y Liquidación Atómica de Pago C2P
    # ------------------------------------------------------------------------

    def test_c2p_payment_success_atomic_settlement(self):
        """Verifica ciclo completo de recarga C2P exitosa y actualización atómica en OCS."""
        bal_before = float(self.repo.get_balance_and_quotas(self.test_phone)["balance_ves"])
        amount = 100.00
        ref_id = f"REF-TEST-{uuid.uuid4().hex[:8]}"

        req = C2PPaymentRequest(
            msisdn=self.test_phone,
            amount_ves=amount,
            bank_code="0102",  # Banco de Venezuela
            payer_cid=self.test_cid,
            otp_token="123456",
            reference_id=ref_id
        )
        resp = self.agent.process_payment(req)

        self.assertTrue(resp.success)
        self.assertEqual(resp.status, PaymentStatus.COMPLETED)
        self.assertEqual(resp.reference_id, ref_id)
        self.assertEqual(resp.amount_ves, amount)
        self.assertAlmostEqual(resp.new_balance_ves, bal_before + amount, places=2)
        self.assertIn("Comprobante de Pago Móvil C2P", resp.receipt_text)
        self.assertIn("Banco de Venezuela", resp.bank_name)
        self.assertFalse(resp.handoff_required)

        # Verificar persistencia en base de datos
        bal_after = float(self.repo.get_balance_and_quotas(self.test_phone)["balance_ves"])
        self.assertAlmostEqual(bal_after, bal_before + amount, places=2)
        self.assertTrue(self.repo.is_reference_duplicate(ref_id))

    def test_c2p_promotional_bonus_tiers(self):
        """Verifica acreditación de bonos de datos 4GMAX según tramos de recarga."""
        quotas_before = int(self.repo.get_balance_and_quotas(self.test_phone)["remaining_data_mb"])

        # Tramo 1: >= 150 Bs. -> 512 MB de bono
        req1 = C2PPaymentRequest(
            msisdn=self.test_phone,
            amount_ves=150.00,
            bank_code="0105",  # Mercantil
            payer_cid=self.test_cid,
            otp_token="123456",
            reference_id=f"REF-BONUS-150-{uuid.uuid4().hex[:6]}"
        )
        resp1 = self.agent.process_payment(req1)
        self.assertTrue(resp1.success)
        self.assertEqual(resp1.data_bonus_mb, 512)
        self.assertIn("+512 MB", resp1.receipt_text)

        quotas_after1 = int(self.repo.get_balance_and_quotas(self.test_phone)["remaining_data_mb"])
        self.assertEqual(quotas_after1, quotas_before + 512)

        # Tramo 2: >= 300 Bs. -> 1024 MB de bono
        req2 = C2PPaymentRequest(
            msisdn=self.test_phone,
            amount_ves=300.00,
            bank_code="0108",  # Provincial
            payer_cid=self.test_cid,
            otp_token="123456",
            reference_id=f"REF-BONUS-300-{uuid.uuid4().hex[:6]}"
        )
        resp2 = self.agent.process_payment(req2)
        self.assertEqual(resp2.data_bonus_mb, 1024)

        # Tramo 3: >= 500 Bs. -> 2048 MB de bono
        req3 = C2PPaymentRequest(
            msisdn=self.test_phone,
            amount_ves=500.00,
            bank_code="0134",  # Banesco
            payer_cid=self.test_cid,
            otp_token="123456",
            reference_id=f"REF-BONUS-500-{uuid.uuid4().hex[:6]}"
        )
        resp3 = self.agent.process_payment(req3)
        self.assertEqual(resp3.data_bonus_mb, 2048)

    # ------------------------------------------------------------------------
    # 2. Pruebas de Anti-Replay e Idempotencia (Zero Double-Spending)
    # ------------------------------------------------------------------------

    def test_c2p_duplicate_reference_rejection(self):
        """Verifica rechazo inmediato si la referencia bancaria ya fue conciliada."""
        ref_id = f"REF-DUP-ANTI-REPLAY-{uuid.uuid4().hex[:6]}"
        req = C2PPaymentRequest(
            msisdn=self.test_phone,
            amount_ves=75.00,
            bank_code="0102",
            payer_cid=self.test_cid,
            otp_token="123456",
            reference_id=ref_id
        )

        # Primer intento: Exitoso
        r1 = self.agent.process_payment(req)
        self.assertTrue(r1.success)
        self.assertEqual(r1.status, PaymentStatus.COMPLETED)

        # Segundo intento idéntico: Rechazado
        r2 = self.agent.process_payment(req)
        self.assertFalse(r2.success)
        self.assertEqual(r2.status, PaymentStatus.REJECTED_DUPLICATE)
        self.assertIn("ya fue conciliada", r2.receipt_text)
        self.assertLess(r2.latency_ms, 2.0, "La detección anti-replay debe ser en O(1) < 2.0ms")

    # ------------------------------------------------------------------------
    # 3. Pruebas de Validación Defensiva y Parámetros SUDEBAN
    # ------------------------------------------------------------------------

    def test_c2p_invalid_phone_rejection(self):
        """Verifica rechazo si el teléfono no es prefijo Movilnet (0416/0426)."""
        req = C2PPaymentRequest(
            msisdn="04121234567",  # Digitel
            amount_ves=50.00,
            bank_code="0102",
            payer_cid=self.test_cid,
            otp_token="123456"
        )
        resp = self.agent.process_payment(req)
        self.assertFalse(resp.success)
        self.assertEqual(resp.status, PaymentStatus.FAILED)
        self.assertIn("prefijo oficial de Movilnet", resp.receipt_text)

    def test_c2p_unregistered_subscriber(self):
        """Verifica rechazo si la línea Movilnet no existe en la base de datos."""
        req = C2PPaymentRequest(
            msisdn="04160000000",
            amount_ves=50.00,
            bank_code="0102",
            payer_cid=self.test_cid,
            otp_token="123456"
        )
        resp = self.agent.process_payment(req)
        self.assertFalse(resp.success)
        self.assertEqual(resp.status, PaymentStatus.REJECTED_INVALID_SUBSCRIBER)
        self.assertIn("no se encuentra registrada", resp.receipt_text)

    def test_c2p_invalid_bank_code(self):
        """Verifica rechazo si el código de banco no existe en el catálogo SUDEBAN."""
        req = C2PPaymentRequest(
            msisdn=self.test_phone,
            amount_ves=50.00,
            bank_code="9999",  # Inválido
            payer_cid=self.test_cid,
            otp_token="123456"
        )
        resp = self.agent.process_payment(req)
        self.assertFalse(resp.success)
        self.assertEqual(resp.status, PaymentStatus.REJECTED_INVALID_BANK)
        self.assertIn("SUDEBAN", resp.receipt_text)

    def test_c2p_invalid_amount_zero_or_negative(self):
        """Verifica rechazo si el monto es <= 0.00 Bs."""
        for bad_amount in [0.0, -25.50]:
            req = C2PPaymentRequest(
                msisdn=self.test_phone,
                amount_ves=bad_amount,
                bank_code="0102",
                payer_cid=self.test_cid,
                otp_token="123456"
            )
            resp = self.agent.process_payment(req)
            self.assertFalse(resp.success)
            self.assertEqual(resp.status, PaymentStatus.REJECTED_INVALID_AMOUNT)

    def test_c2p_invalid_otp_format(self):
        """Verifica rechazo si el token OTP no tiene longitud estándar (6-8 dígitos)."""
        for bad_otp in ["123", "abc", "", "1234567890"]:
            req = C2PPaymentRequest(
                msisdn=self.test_phone,
                amount_ves=50.00,
                bank_code="0102",
                payer_cid=self.test_cid,
                otp_token=bad_otp
            )
            resp = self.agent.process_payment(req)
            self.assertFalse(resp.success)
            self.assertEqual(resp.status, PaymentStatus.REJECTED_INVALID_OTP)

    # ------------------------------------------------------------------------
    # 4. Pruebas de Detección de Fraude & Handoff Swarm L5 (Hacia Agente N3)
    # ------------------------------------------------------------------------

    def test_c2p_fraud_detection_and_emergency_handoff(self):
        """Verifica detección de montos anómalos exorbitantes y escalado a Agente N3."""
        req = C2PPaymentRequest(
            msisdn=self.test_phone,
            amount_ves=100000.00,  # Excede umbral máximo de 50.000 Bs
            bank_code="0102",
            payer_cid=self.test_cid,
            otp_token="123456"
        )
        resp = self.agent.process_payment(req)

        self.assertFalse(resp.success)
        self.assertEqual(resp.status, PaymentStatus.REJECTED_FRAUD_ALERT)
        self.assertTrue(resp.handoff_required)
        self.assertEqual(resp.target_agent, "agent_emergency_eir")
        self.assertIn("Alerta de Seguridad Transaccional", resp.receipt_text)
        self.assertGreaterEqual(resp.metadata.get("risk_score", 0), 0.80)

    # ------------------------------------------------------------------------
    # 5. Pruebas de Conversión y Tasa Oficial BCV
    # ------------------------------------------------------------------------

    def test_c2p_bcv_rate_conversion(self):
        """Verifica cálculo formal del equivalente en USD según tasa oficial BCV."""
        rate = self.agent.get_official_bcv_rate()
        self.assertGreater(rate, 0.0)

        amount_ves = 184.25
        req = C2PPaymentRequest(
            msisdn=self.test_phone,
            amount_ves=amount_ves,
            bank_code="0102",
            payer_cid=self.test_cid,
            otp_token="123456"
        )
        resp = self.agent.process_payment(req)
        expected_usd = round(amount_ves / rate, 2)

        self.assertTrue(resp.success)
        self.assertAlmostEqual(resp.amount_usd_equiv, expected_usd, places=2)
        self.assertEqual(resp.bcv_rate_applied, rate)

    # ------------------------------------------------------------------------
    # 6. Pruebas de Invalidación de Caché L1 en Agente N1
    # ------------------------------------------------------------------------

    def test_cache_invalidation_after_payment(self):
        """Verifica que tras pagar, el Caché L1 del Agente N1 se invalida para ver el nuevo saldo."""
        # 1. Agente N1 consulta saldo y lo mete en L1 Cache
        m1 = AgentMessage(text="saldo", msisdn=self.test_phone)
        r1 = self.customer_care.process_message(m1)
        old_bal = r1.metadata["balance_ves"]

        # 2. Agente N2 procesa recarga de 50 Bs
        req = C2PPaymentRequest(
            msisdn=self.test_phone,
            amount_ves=50.00,
            bank_code="0102",
            payer_cid=self.test_cid,
            otp_token="123456"
        )
        r2 = self.agent.process_payment(req)
        self.assertTrue(r2.success)

        # 3. Invalidar caché manualmente si no se pasó por API service
        self.customer_care.cache.invalidate(f"sub_ctx_{self.test_phone}")

        # 4. Agente N1 consulta saldo nuevamente y obtiene el saldo incrementado
        r3 = self.customer_care.process_message(m1)
        new_bal = r3.metadata["balance_ves"]
        self.assertAlmostEqual(new_bal, old_bal + 50.00, places=2)

    # ------------------------------------------------------------------------
    # 7. Pruebas de Integración con REST API & OpenAPI 3.1.0
    # ------------------------------------------------------------------------

    def test_rest_api_fintech_c2p_process_success(self):
        """Verifica endpoint POST /api/v1/agents/fintech-c2p/process vía dispatch REST."""
        ref_id = f"REF-API-C2P-{uuid.uuid4().hex[:6]}"
        body = {
            "msisdn": self.test_phone,
            "amount_ves": 80.00,
            "bank_code": "0102",
            "payer_cid": self.test_cid,
            "otp_token": "123456",
            "reference_id": ref_id,
            "channel": "web"
        }
        status, headers, resp_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/agents/fintech-c2p/process",
            headers={"Content-Type": "application/json"},
            body_bytes=json.dumps(body).encode("utf-8")
        )
        self.assertEqual(status, 200)
        data = json.loads(resp_bytes.decode("utf-8"))
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["reference_id"], ref_id)
        self.assertEqual(data["amount_ves"], 80.00)

    def test_rest_api_fintech_c2p_duplicate_reference_409(self):
        """Verifica retorno de HTTP 409 Conflict si la referencia bancaria está duplicada."""
        ref_id = f"REF-DUP-API-{uuid.uuid4().hex[:6]}"
        body = {
            "msisdn": self.test_phone,
            "amount_ves": 40.00,
            "bank_code": "0102",
            "payer_cid": self.test_cid,
            "otp_token": "123456",
            "reference_id": ref_id
        }
        # Primer llamado: 200 OK
        status1, _, _ = self.service.dispatch("POST", "/api/v1/agents/fintech-c2p/process", {}, json.dumps(body).encode("utf-8"))
        self.assertEqual(status1, 200)

        # Segundo llamado: 409 Conflict
        status2, _, resp2 = self.service.dispatch("POST", "/api/v1/agents/fintech-c2p/process", {}, json.dumps(body).encode("utf-8"))
        self.assertEqual(status2, 409)
        data2 = json.loads(resp2.decode("utf-8"))
        self.assertFalse(data2["success"])
        self.assertEqual(data2["status"], "REJECTED_DUPLICATE")

    def test_rest_api_fintech_c2p_missing_fields_400(self):
        """Verifica rechazo con HTTP 400 si faltan campos obligatorios."""
        bad_body = {"msisdn": self.test_phone}
        status, _, resp = self.service.dispatch("POST", "/api/v1/agents/fintech-c2p/process", {}, json.dumps(bad_body).encode("utf-8"))
        self.assertEqual(status, 400)
        data = json.loads(resp.decode("utf-8"))
        self.assertEqual(data["code"], "ERR_MISSING_FINTECH_FIELDS")

    # ------------------------------------------------------------------------
    # 8. Pruebas de Integración con Webhook Bridge Omnicanal
    # ------------------------------------------------------------------------

    def test_webhook_bridge_c2p_callback_integration(self):
        """Verifica que el puente de webhooks ejecute el pago a través del Agente Nivel 2."""
        ref_id = f"REF-WH-C2P-{uuid.uuid4().hex[:6]}"
        c2p_payload = {
            "reference_id": ref_id,
            "msisdn": self.test_phone,
            "bank_code": "0102",
            "amount_ves": 120.00,
            "payer_cid": self.test_cid,
            "otp_token": "123456"
        }
        status, resp = self.webhook_bridge.process_inbound_event(
            headers={"X-Movilnet-Event-Type": "c2p.callback"},
            body_bytes=json.dumps(c2p_payload).encode("utf-8"),
            skip_hmac_check=True
        )
        self.assertEqual(status, 200)
        res = resp["processing_result"]
        self.assertEqual(res["reconciliation"], "COMPLETED")
        self.assertEqual(res["reference_id"], ref_id)
        self.assertIn("agent_c2p_response", res)
        self.assertEqual(res["agent_c2p_response"]["status"], "COMPLETED")

    # ------------------------------------------------------------------------
    # 9. Benchmark de Latencia y Rendimiento Telco (Carrier-Grade SLA)
    # ------------------------------------------------------------------------

    def test_sre_fintech_latency_benchmark(self):
        """Evalúa transacciones consecutivas C2P garantizando P95 dentro del SLA Carrier-Grade (< 30ms)."""
        # Calentamiento previo (Warm-up)
        for w in range(2):
            req_w = C2PPaymentRequest(
                msisdn=self.test_phone,
                amount_ves=5.0,
                bank_code="0102",
                payer_cid=self.test_cid,
                otp_token="123456",
                reference_id=f"REF-WARM-{w}-{uuid.uuid4().hex[:6]}"
            )
            self.agent.process_payment(req_w)

        latencies = []
        for i in range(25):
            req = C2PPaymentRequest(
                msisdn=self.test_phone,
                amount_ves=10.00 + i,
                bank_code="0102",
                payer_cid=self.test_cid,
                otp_token="123456",
                reference_id=f"REF-BENCH-{i}-{uuid.uuid4().hex[:6]}"
            )
            t0 = time.perf_counter()
            resp = self.agent.process_payment(req)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)
            self.assertTrue(resp.success)

        latencies.sort()
        avg_lat = sum(latencies) / len(latencies)
        p95_lat = latencies[int(len(latencies) * 0.95)]

        print(f"\n   ⚡ Latencia Agente N2 (Fintech C2P): Promedio={avg_lat:.3f}ms | P95={p95_lat:.3f}ms | Min={latencies[0]:.3f}ms")
        self.assertLess(avg_lat, 20.0, "La latencia promedio de liquidación C2P debe ser inferior a 20.0ms")
        self.assertLess(p95_lat, 35.0, "La latencia P95 de liquidación C2P debe estar dentro del SLA Carrier-Grade (< 35ms)")



if __name__ == "__main__":
    unittest.main()
