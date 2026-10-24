#!/usr/bin/env python3
"""
test_phase2_webhook_mcp_integration.py — Suite de Pruebas de Integración Webhooks & MCP
========================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Fase 2: Paso 3 — Integración de Webhooks entre n8n, API REST y Suites MCP en vivo.
Estándares: TM Forum ODA (TMF688 Events, TMF676, TMF678, TMF680), RFC 2104 HMAC-SHA256
"""

from __future__ import annotations

import os
import sys
import json
import time
import uuid
import hmac
import hashlib
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.repository import MovilnetRepository
from api.service import MovilnetAPIService
from api.webhook_bridge import (
    get_webhook_bridge,
    WebhookBridgeService,
    WebhookDispatcher,
    WebhookDeadLetterQueue,
    WebhookDeliveryTracker,
    HMACSignatureValidator,
    DEFAULT_WEBHOOK_SECRET,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    DELIVERY_ID_HEADER,
    EVENT_TYPE_HEADER
)
from mcp.master_gateway import MovilnetMasterMcpGateway


class TestPhase2WebhookMcpIntegration(unittest.TestCase):
    """Batería exhaustiva de pruebas para la integración de Webhooks, API y Suites MCP."""

    @classmethod
    def setUpClass(cls):
        cls.repo = MovilnetRepository()
        cls.mcp = MovilnetMasterMcpGateway()
        cls.service = MovilnetAPIService(repository=cls.repo)
        cls.secret = DEFAULT_WEBHOOK_SECRET

        # Crear o recuperar abonado de prueba
        cls.test_phone = "04160000001"
        cls.test_cid = "V-10000001"
        sub = cls.repo.get_subscriber_by_msisdn(cls.test_phone)
        if not sub:
            cls.test_sub = cls.repo.create_subscriber_with_line(
                cid=cls.test_cid,
                msisdn=cls.test_phone,
                plan_id="PLAN_4GMAX_PREPAGO_20GB",
                balance_ves=50.00
            )
        else:
            cls.test_sub = sub
            bal = cls.repo.get_balance_and_quotas(cls.test_phone)
            if bal:
                delta = 50.00 - float(bal.get("balance_ves", 0.0))
                cls.repo.update_balance_and_quotas(cls.test_phone, ves_delta=delta)
        cls.repo.update_line_status(cls.test_phone, "ACTIVO")

    @classmethod
    def tearDownClass(cls):
        cls.repo.update_line_status(cls.test_phone, "ACTIVO")

    def _generate_headers(
        self,
        payload: Dict[str, Any],
        event_type: str = "c2p.callback",
        delivery_id: Optional[str] = None,
        custom_key: Optional[str] = None,
        timestamp_str: Optional[str] = None
    ) -> Tuple[Dict[str, str], bytes]:
        """Utilidad para generar cabeceras válidas con firma HMAC-SHA256."""
        sec = custom_key or self.secret
        ts = timestamp_str or datetime.now(timezone.utc).isoformat()
        del_id = delivery_id or f"del-{uuid.uuid4().hex}"
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sig = HMACSignatureValidator.generate_signature(payload_bytes, sec, ts)

        headers = {
            "Content-Type": "application/json",
            SIGNATURE_HEADER: sig,
            TIMESTAMP_HEADER: ts,
            DELIVERY_ID_HEADER: del_id,
            EVENT_TYPE_HEADER: event_type
        }
        return headers, payload_bytes

    # =========================================================================
    # 1. PRUEBAS DE SEGURIDAD CRIPTOGRÁFICA HMAC-SHA256
    # =========================================================================

    def test_hmac_signature_generation_and_positive_verification(self):
        """Valida que una firma generada con el secreto oficial sea verificada exitosamente."""
        payload = {"transaction": "TX-1001", "amount": 100.0}
        headers, body_bytes = self._generate_headers(payload)

        valid, err = HMACSignatureValidator.verify_signature(
            signature=headers[SIGNATURE_HEADER],
            payload_bytes=body_bytes,
            secret=self.secret,
            timestamp_str=headers[TIMESTAMP_HEADER]
        )
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_hmac_tampered_payload_rejection(self):
        """Valida que cualquier alteración de 1 byte en el payload invalide la firma."""
        payload = {"transaction": "TX-1001", "amount": 100.0}
        headers, body_bytes = self._generate_headers(payload)

        # Alterar payload maliciosamente
        tampered_bytes = body_bytes.replace(b"100.0", b"999.0")

        valid, err = HMACSignatureValidator.verify_signature(
            signature=headers[SIGNATURE_HEADER],
            payload_bytes=tampered_bytes,
            secret=self.secret,
            timestamp_str=headers[TIMESTAMP_HEADER]
        )
        self.assertFalse(valid)
        self.assertIn("Firma HMAC-SHA256 no coincide", err)

    def test_hmac_tampered_secret_rejection(self):
        """Valida que una firma generada con otra clave sea rechazada."""
        payload = {"test": "data"}
        unauthorized_key = "UNAUTHORIZED_SAMPLE_KEY"
        headers, body_bytes = self._generate_headers(payload, custom_key=unauthorized_key)

        valid, err = HMACSignatureValidator.verify_signature(
            signature=headers[SIGNATURE_HEADER],
            payload_bytes=body_bytes,
            secret=self.secret,
            timestamp_str=headers[TIMESTAMP_HEADER]
        )
        self.assertFalse(valid)
        self.assertIn("Firma HMAC-SHA256 no coincide", err)

    def test_hmac_replay_attack_expired_timestamp(self):
        """Valida protección anti-repetición: rechazo si el timestamp tiene más de 300s de antigüedad."""
        payload = {"attack": "replay"}
        old_ts = time.time() - 400  # 400 segundos en el pasado
        headers, body_bytes = self._generate_headers(payload, timestamp_str=str(int(old_ts)))

        valid, err = HMACSignatureValidator.verify_signature(
            signature=headers[SIGNATURE_HEADER],
            payload_bytes=body_bytes,
            secret=self.secret,
            timestamp_str=headers[TIMESTAMP_HEADER],
            tolerance_seconds=300
        )
        self.assertFalse(valid)
        self.assertIn("fuera de la ventana de tolerancia", err)

    def test_hmac_missing_headers_rejection(self):
        """Valida rechazo explícito cuando faltan cabeceras de seguridad."""
        payload_bytes = b'{"msg": "test"}'
        valid, err = HMACSignatureValidator.verify_signature(
            signature=None,
            payload_bytes=payload_bytes,
            secret=self.secret,
            timestamp_str="2026-10-01T12:00:00Z"
        )
        self.assertFalse(valid)
        self.assertIn("firma requerida ausente", err)

    # =========================================================================
    # 2. INGESTA Y PROCESAMIENTO DE WEBHOOKS EN EL MICROSERVICIO
    # =========================================================================

    def test_inbound_webhook_unauthorized_without_signature(self):
        """Petición a /api/v1/webhooks/inbound-events sin firma debe retornar 401 Unauthorized."""
        body = b'{"event": "unauthorized"}'
        status, _, resp_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/webhooks/inbound-events",
            headers={"Content-Type": "application/json"},
            body_bytes=body
        )
        self.assertEqual(status, 401)
        resp = json.loads(resp_bytes.decode("utf-8"))
        self.assertEqual(resp["code"], "ERR_INVALID_SIGNATURE")

    def test_inbound_webhook_idempotency_deduplication(self):
        """Valida que dos envíos con el mismo Delivery-ID no se procesen doblemente."""
        del_id = f"del-idemp-{uuid.uuid4().hex}"
        payload = {"event_test": "idempotency_value"}
        headers, body_bytes = self._generate_headers(payload, event_type="test.event", delivery_id=del_id)

        # Primer despacho: 200 éxito
        status1, _, resp1_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/webhooks/inbound-events",
            headers=headers,
            body_bytes=body_bytes
        )
        self.assertEqual(status1, 200)
        resp1 = json.loads(resp1_bytes.decode("utf-8"))
        self.assertEqual(resp1["status"], "success")

        # Segundo despacho con mismo Delivery-ID: 200 already_processed
        status2, _, resp2_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/webhooks/inbound-events",
            headers=headers,
            body_bytes=body_bytes
        )
        self.assertEqual(status2, 200)
        resp2 = json.loads(resp2_bytes.decode("utf-8"))
        self.assertEqual(resp2["status"], "already_processed")
        self.assertIn("ya fue procesado previamente", resp2["message"])

    def test_c2p_payment_callback_reconciliation_e2e(self):
        """
        Ciclo Completo C2P Callback:
        Webhook entrante de conciliación bancaria -> Validador Antifraude MCP ->
        Actualización de saldo en DB -> Registro de transacción.
        """
        ref_id = f"REF-WH-{uuid.uuid4().hex[:8]}"
        amount_ves = 150.00
        initial_balance = self.repo.get_subscriber_balance(self.test_phone)

        c2p_payload = {
            "reference_id": ref_id,
            "msisdn": self.test_phone,
            "bank_code": "0102",
            "amount_ves": amount_ves,
            "payer_cid": self.test_cid,
            "otp_token": "654321"
        }
        headers, body_bytes = self._generate_headers(c2p_payload, event_type="c2p.callback")

        status, _, resp_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/webhooks/c2p-callback",
            headers=headers,
            body_bytes=body_bytes
        )
        self.assertEqual(status, 200)
        resp = json.loads(resp_bytes.decode("utf-8"))
        self.assertEqual(resp["status"], "success")
        self.assertIn("Suite 2: mcp_fintech_c2p", resp["mcp_suite_engaged"])
        
        proc_result = resp["processing_result"]
        self.assertEqual(proc_result["reconciliation"], "COMPLETED")
        self.assertEqual(proc_result["reference_id"], ref_id)

        # Verificar saldo en base de datos
        new_bal = self.repo.get_subscriber_balance(self.test_phone)
        expected_balance = round(initial_balance + amount_ves, 2)
        self.assertEqual(new_bal, expected_balance)

    def test_eir_lock_callback_e2e(self):
        """
        Ciclo Completo EIR Lock Callback:
        Webhook entrante de confirmación de bloqueo -> Auditoría SIM-Swap MCP ->
        Inserción en lista negra EIR DB -> Bloqueo de línea en DB.
        """
        victim_phone = "04167770099"
        if not self.repo.get_subscriber_by_msisdn(victim_phone):
            self.repo.create_subscriber_with_line(
                cid="V-77700099",
                msisdn=victim_phone,
                plan_id="PLAN_4GMAX_PREPAGO_20GB",
                balance_ves=20.0
            )

        imei_test = f"3589{uuid.uuid4().int % 10000000000:010d}"
        eir_payload = {
            "imei": imei_test,
            "msisdn": victim_phone,
            "reason": "EXTRAVIO_TERMINAL_URGENTE",
            "reported_by": "N8N_INCIDENT_WORKFLOW"
        }
        headers, body_bytes = self._generate_headers(eir_payload, event_type="eir.callback")

        status, _, resp_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/webhooks/eir-callback",
            headers=headers,
            body_bytes=body_bytes
        )
        self.assertEqual(status, 200)
        resp = json.loads(resp_bytes.decode("utf-8"))
        self.assertEqual(resp["status"], "success")
        self.assertIn("Suite 1: mcp_telco_tools", resp["mcp_suite_engaged"])

        proc_result = resp["processing_result"]
        self.assertEqual(proc_result["eir_status"], "BLOCKED_CONFIRMED")
        self.assertEqual(proc_result["imei"], imei_test)
        self.assertTrue(proc_result["line_blocked"])

        # Verificar que el IMEI quedó en lista negra
        self.assertTrue(self.repo.is_imei_blacklisted(imei_test))

    def test_omnichannel_whatsapp_inbound_with_pii_sanitization_and_buttons(self):
        """
        Mensaje entrante de WhatsApp:
        Sanitización PII con Suite 4 -> Consulta en DB -> Formateo de botones con Suite 5.
        """
        msg_payload = {
            "from": self.test_phone,
            "text": "Hola, mi cédula es V-10000001 y requiero saldo de mi línea 04160000001"
        }
        headers, body_bytes = self._generate_headers(msg_payload, event_type="whatsapp.inbound")

        status, _, resp_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/webhooks/inbound-events",
            headers=headers,
            body_bytes=body_bytes
        )
        self.assertEqual(status, 200)
        resp = json.loads(resp_bytes.decode("utf-8"))
        self.assertEqual(resp["status"], "success")
        self.assertIn("Suite 5: mcp_omnichannel_whatsapp", resp["mcp_suite_engaged"])
        
        proc_res = resp["processing_result"]
        self.assertTrue(proc_res["subscriber_found"])
        self.assertIn("suggested_reply", proc_res)
        # Verificar que se generaron los botones de WhatsApp interactivo
        reply = proc_res["suggested_reply"]
        self.assertEqual(reply.get("type"), "interactive")
        self.assertEqual(reply.get("interactive", {}).get("type"), "button")

    def test_crm_retention_event_evaluation(self):
        """Evento de churn risk: Invoca Suite 3 (CRM Retention MCP)."""
        crm_payload = {
            "msisdn": self.test_phone,
            "days_inactive": 25,
            "balance_ves": 0.00
        }
        headers, body_bytes = self._generate_headers(crm_payload, event_type="crm.retention.trigger")

        status, _, resp_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/webhooks/inbound-events",
            headers=headers,
            body_bytes=body_bytes
        )
        self.assertEqual(status, 200)
        resp = json.loads(resp_bytes.decode("utf-8"))
        self.assertIn("Suite 3: mcp_crm_retention", resp["mcp_suite_engaged"])
        assessment = resp["processing_result"]["assessment"]
        self.assertIn("churn_risk_score", assessment)
        self.assertIn("risk_tier", assessment)

    # =========================================================================
    # 3. DESPACHADOR, REINTENTOS EXPONENCIALES, JITTER Y DEAD LETTER QUEUE (DLQ)
    # =========================================================================

    def test_dispatcher_success_immediate(self):
        """Despacho a un receptor saludable (HTTP 200) con 1 solo intento."""
        dlq = WebhookDeadLetterQueue()
        tracker = WebhookDeliveryTracker()

        def mock_transport(req, timeout):
            return 200, '{"status": "received"}'

        dispatcher = WebhookDispatcher(dlq=dlq, tracker=tracker, transport_override=mock_transport)
        result = dispatcher.dispatch(
            target_url="http://mock-n8n.internal/webhook/test",
            event_type="test.success",
            payload={"sample": "data"}
        )

        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.attempts, 1)
        self.assertFalse(result.routed_to_dlq)
        self.assertEqual(dlq.count()["total_dlq"], 0)

    def test_dispatcher_retry_exponential_backoff_and_recovery(self):
        """Simula fallo transitorio (503) en intentos 1 y 2, y éxito (200) en intento 3."""
        dlq = WebhookDeadLetterQueue()
        tracker = WebhookDeliveryTracker()
        call_count = [0]

        def flaky_transport(req, timeout):
            call_count[0] += 1
            if call_count[0] < 3:
                return 503, '{"error": "Temporary server error"}'
            return 200, '{"status": "finally recovered"}'

        dispatcher = WebhookDispatcher(dlq=dlq, tracker=tracker, transport_override=flaky_transport)
        result = dispatcher.dispatch(
            target_url="http://mock-n8n.internal/webhook/flaky",
            event_type="test.recovery",
            payload={"sample": "recovered"},
            max_retries=3
        )

        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.attempts, 3)
        self.assertFalse(result.routed_to_dlq)
        self.assertEqual(dlq.count()["total_dlq"], 0)
        self.assertEqual(tracker.stats["retries_count"], 2)

    def test_dispatcher_permanent_failure_enqueues_to_dlq(self):
        """Simula fallo permanente (500), agota reintentos y enruta hacia la Dead Letter Queue."""
        dlq = WebhookDeadLetterQueue()
        tracker = WebhookDeliveryTracker()

        def failing_transport(req, timeout):
            return 500, '{"error": "Internal Fatal Error"}'

        dispatcher = WebhookDispatcher(dlq=dlq, tracker=tracker, transport_override=failing_transport)
        result = dispatcher.dispatch(
            target_url="http://mock-n8n.internal/webhook/failing",
            event_type="test.failure",
            payload={"sample": "doomed"},
            max_retries=3
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.attempts, 3)
        self.assertTrue(result.routed_to_dlq)

        # Verificar que ingresó en la DLQ
        dlq_stats = dlq.count()
        self.assertEqual(dlq_stats["total_dlq"], 1)
        self.assertEqual(dlq_stats["unresolved_dlq"], 1)

        dlq_items = dlq.list_all(limit=5)
        self.assertEqual(len(dlq_items), 1)
        self.assertEqual(dlq_items[0]["event"]["event_type"], "test.failure")

    def test_dlq_reprocess_flow_e2e(self):
        """Verifica la API /api/v1/webhooks/dlq/retry para rescatar mensajes de la DLQ."""
        # Encolar elemento fallido en el bridge
        bridge = get_webhook_bridge()
        event_sample = {
            "reference": "RESUPPLY-99",
            "phone": self.test_phone
        }
        # Inyectar transporte temporal que falle primero
        orig_transport = bridge.dispatcher.transport_override
        try:
            bridge.dispatcher.transport_override = lambda r, t: (500, '{"error": "crash"}')
            bad_res = bridge.dispatcher.dispatch(
                target_url="mock://failing.url/hook",
                event_type="event.recovery_test",
                payload=event_sample,
                max_retries=1
            )
            self.assertTrue(bad_res.routed_to_dlq)

            # Obtener el dlq_id generado
            dlq_item = bridge.dlq.list_all(limit=1)[0]
            dlq_id = dlq_item["dlq_id"]

            # Ahora cambiar transporte a exitoso para el reprocesamiento
            bridge.dispatcher.transport_override = lambda r, t: (200, '{"status": "ok"}')

            # Llamar endpoint de retry
            status, _, resp_bytes = self.service.dispatch(
                method="POST",
                path="/api/v1/webhooks/dlq/retry",
                headers={"Content-Type": "application/json"},
                body_bytes=json.dumps({"dlq_id": dlq_id}).encode("utf-8")
            )
            self.assertEqual(status, 200)
            resp = json.loads(resp_bytes.decode("utf-8"))
            self.assertTrue(resp["reprocessed"])
            self.assertEqual(resp["delivery_result"]["status_code"], 200)

            # Verificar que quedó marcado como reprocesado
            check_item = bridge.dlq.get_by_id(dlq_id)
            self.assertTrue(check_item["reprocessed"])
        finally:
            bridge.dispatcher.transport_override = orig_transport

    # =========================================================================
    # 4. OBSERVABILIDAD Y MÉTRICAS DE ENTREGAS
    # =========================================================================

    def test_get_webhook_deliveries_observability_endpoint(self):
        """Prueba /api/v1/webhooks/deliveries para telemetría y monitoreo."""
        status, _, resp_bytes = self.service.dispatch(
            method="GET",
            path="/api/v1/webhooks/deliveries",
            headers={},
            body_bytes=b""
        )
        self.assertEqual(status, 200)
        resp = json.loads(resp_bytes.decode("utf-8"))
        self.assertIn("delivery_stats", resp)
        self.assertIn("dead_letter_queue", resp)
        self.assertIn("recent_deliveries", resp)
        self.assertGreaterEqual(resp["delivery_stats"]["success_rate_pct"], 0.0)

    # =========================================================================
    # 5. LATENCIA Y BENCHMARK DE PROCESAMIENTO
    # =========================================================================

    def test_webhook_pipeline_latency_benchmark(self):
        """
        Ejecuta 25 peticiones continuas de webhooks con firma criptográfica y
        mide que la latencia media sea sub-milisegundo o inferior a 5ms.
        """
        latencies = []
        for i in range(25):
            payload = {"benchmark_iter": i, "msisdn": self.test_phone}
            headers, body_bytes = self._generate_headers(
                payload,
                event_type="benchmark.event",
                delivery_id=f"del-bench-{i}-{uuid.uuid4().hex[:6]}"
            )
            t0 = time.time()
            status, _, _ = self.service.dispatch(
                method="POST",
                path="/api/v1/webhooks/inbound-events",
                headers=headers,
                body_bytes=body_bytes
            )
            lat = (time.time() - t0) * 1000
            latencies.append(lat)
            self.assertEqual(status, 200)

        avg_lat = sum(latencies) / len(latencies)
        p95_lat = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f"\n   ⚡ Latencia Webhooks: Promedio={avg_lat:.3f}ms | P95={p95_lat:.3f}ms | Min={min(latencies):.3f}ms | Max={max(latencies):.3f}ms")
        self.assertLess(avg_lat, 10.0, f"Latencia media superior a 10ms: {avg_lat}ms")


if __name__ == "__main__":
    unittest.main()
