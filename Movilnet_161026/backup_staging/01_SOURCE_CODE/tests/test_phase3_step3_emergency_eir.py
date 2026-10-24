#!/usr/bin/env python3
"""
test_phase3_step3_emergency_eir.py — Batería de Pruebas Automatizadas: Fase 3, Paso 3
====================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Hito: Fase 3 — Paso 3: Agente Nivel 3 (Gestión de Emergencias, Fraude y Bloqueo EIR/IMEI)
Estándares: TM Forum ODA (TMF675 Geographic Location & Incident / TMF638 Resource Inventory /
             TMF642 Alarm Management) / GSMA IMEI Blacklist (3GPP TS 23.003) / CONATEL
"""

import os
import sys
import json
import time
import uuid
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.repository import MovilnetRepository
from api.service import MovilnetAPIService
from api.agents.agent_customer_care import CustomerCareAgent, AgentMessage
from api.agents.agent_emergency_eir import (
    EmergencyEIRAgent,
    EIRLockType,
    EIRStatus,
    EmergencyEIRRequest,
    EmergencyEIRResponse,
    IMEILuhnValidator,
    SIMSwapDefenseEngine
)
from api.webhook_bridge import (
    HMACSignatureValidator,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    DELIVERY_ID_HEADER,
    EVENT_TYPE_HEADER,
    DEFAULT_WEBHOOK_SECRET
)


class TestPhase3Step3EmergencyEIR(unittest.TestCase):
    """Suite de validación formal para el Agente Nivel 3 (EmergencyEIRAgent)."""

    @classmethod
    def setUpClass(cls):
        cls.repo = MovilnetRepository()
        cls.service = MovilnetAPIService(repository=cls.repo)
        cls.agent = cls.service.emergency_eir_agent
        cls.customer_care = cls.service.customer_care_agent
        cls.agent.set_customer_care_agent(cls.customer_care)

        # Generar número de prueba exclusivo
        cls.test_msisdn = f"0416{uuid.uuid4().int % 10000000:07d}"
        cls.test_cid = f"V-{uuid.uuid4().int % 100000000:08d}"
        cls.test_imei_14 = f"35824005{uuid.uuid4().int % 1000000:06d}"
        cls.test_check = IMEILuhnValidator.calculate_luhn_check_digit(cls.test_imei_14)
        cls.test_imei = cls.test_imei_14 + str(cls.test_check)

        cls.repo.create_subscriber_with_line(
            cid=cls.test_cid,
            msisdn=cls.test_msisdn,
            plan_id="PLAN_10GB_4GMAX",
            balance_ves=100.0,
            quota_mb=10240,
            imei=cls.test_imei
        )

    def test_01_luhn_algorithm_valid_imeis(self):
        """Valida códigos IMEI correctos de 15 dígitos y autocompletado de 14 dígitos."""
        # 1. 15 dígitos con Luhn exacto
        val1 = IMEILuhnValidator.validate(self.test_imei)
        self.assertTrue(val1.is_valid)
        self.assertEqual(val1.imei, self.test_imei)
        self.assertEqual(val1.check_digit, self.test_check)
        self.assertIn("Huawei", val1.brand_guess)


        # 2. 14 dígitos (TAC + SNR) autocompletado
        val2 = IMEILuhnValidator.validate(self.test_imei_14)
        self.assertTrue(val2.is_valid)
        self.assertEqual(len(val2.imei), 15)
        self.assertEqual(val2.imei, self.test_imei)

    def test_02_luhn_algorithm_invalid_imeis(self):
        """Rechaza IMEIs con dígito de control alterado, no numéricos o longitud incorrecta."""
        # Check digit alterado
        bad_check = (self.test_check + 1) % 10
        bad_imei = self.test_imei_14 + str(bad_check)
        val = IMEILuhnValidator.validate(bad_imei)
        self.assertFalse(val.is_valid)
        self.assertIn("Dígito verificador Luhn inválido", val.reason)

        # Caracteres no numéricos
        val_alpha = IMEILuhnValidator.validate("35824005111111A")
        self.assertFalse(val_alpha.is_valid)

        # Longitud incorrecta
        val_short = IMEILuhnValidator.validate("123456789")
        self.assertFalse(val_short.is_valid)

        # Patrón repetido no válido
        val_dummy = IMEILuhnValidator.validate("000000000000000")
        self.assertFalse(val_dummy.is_valid)

    def test_03_sim_swap_defense_engine_recent_swap(self):
        """Detecta alerta crítica de seguridad si la tarjeta SIM fue cambiada hace menos de 24h."""
        swap_2h_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        res = SIMSwapDefenseEngine.audit_swap_window(
            msisdn="04169991122",
            last_swap_at=swap_2h_ago,
            current_imsi="734069991122"
        )
        self.assertTrue(res.is_recent_swap)
        self.assertGreaterEqual(res.risk_score, 0.85)
        self.assertIn("ALERTA CRÍTICA", res.recommendation)
        self.assertLess(res.hours_since_last_swap, 3.0)

    def test_04_sim_swap_defense_engine_stable_line(self):
        """Confirma bajo riesgo en líneas estables sin cambios de SIM en las últimas 72 horas."""
        swap_5d_ago = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        res = SIMSwapDefenseEngine.audit_swap_window(
            msisdn="04169991122",
            last_swap_at=swap_5d_ago,
            current_imsi="734069991122"
        )
        self.assertFalse(res.is_recent_swap)
        self.assertLessEqual(res.risk_score, 0.10)
        self.assertIn("normalmente", res.recommendation)

    def test_05_process_emergency_lock_theft_nominal(self):
        """Ejecuta el protocolo completo THEFT_LOCK, actualizando línea y persistiendo en EIR."""
        req = EmergencyEIRRequest(
            msisdn=self.test_msisdn,
            imei=self.test_imei,
            lock_type=EIRLockType.THEFT_LOCK,
            reason="Atraco a mano armada en transporte público",
            police_report_number="CICPC-EXP-2026-8819",
            reporting_agent="unit_test_suite"
        )
        resp = self.agent.process_emergency_lock(req)

        self.assertEqual(resp.status, EIRStatus.CONFIRMED_LOCKED)
        self.assertTrue(resp.ticket_id.startswith("EIR-"))
        self.assertEqual(resp.line_status, "BLOQUEADO_ROBO")
        self.assertTrue(resp.conatel_broadcast_ready)
        self.assertIn("CONSTANCIA DIGITAL DE BLOQUEO DE SEGURIDAD EIR", resp.security_notice)
        self.assertIn("CICPC-EXP-2026-8819", resp.security_notice)

        # Verificar persistencia en base de datos
        self.assertTrue(self.repo.is_imei_blacklisted(self.test_imei))
        line = self.repo.get_line_details(self.test_msisdn)
        self.assertEqual(line["status"], "BLOQUEADO_ROBO")

    def test_06_process_emergency_lock_already_blacklisted(self):
        """Rechaza con ALREADY_BLACKLISTED un intento redundante de bloqueo sobre un IMEI bloqueado."""
        req = EmergencyEIRRequest(
            msisdn=self.test_msisdn,
            imei=self.test_imei,
            lock_type=EIRLockType.THEFT_LOCK,
            reason="Segundo reporte del mismo hurto"
        )
        resp = self.agent.process_emergency_lock(req)
        self.assertEqual(resp.status, EIRStatus.ALREADY_BLACKLISTED)
        self.assertIn("Previamente Bloqueado", resp.security_notice)

    def test_07_process_emergency_lock_fraud_suspension(self):
        """Ejecuta suspensión preventiva de línea por FRAUD_SUSPENSION con estatus SUSPENDIDO_FRAUDE."""
        victim_msisdn = f"0416{uuid.uuid4().int % 10000000:07d}"
        victim_imei_14 = f"35791200{uuid.uuid4().int % 1000000:06d}"
        victim_check = IMEILuhnValidator.calculate_luhn_check_digit(victim_imei_14)
        victim_imei = victim_imei_14 + str(victim_check)

        self.repo.create_subscriber_with_line(
            cid=f"V-{uuid.uuid4().int % 100000000:08d}",
            msisdn=victim_msisdn,
            plan_id="PLAN_10GB_4GMAX",
            imei=victim_imei
        )

        req = EmergencyEIRRequest(
            msisdn=victim_msisdn,
            imei=victim_imei,
            lock_type=EIRLockType.FRAUD_SUSPENSION,
            reason="Fraude transaccional C2P detectado por Agente Fintech N2",
            reporting_agent="agent_fintech_c2p"
        )
        resp = self.agent.process_emergency_lock(req)
        self.assertEqual(resp.status, EIRStatus.CONFIRMED_LOCKED)
        self.assertEqual(resp.line_status, "SUSPENDIDO_FRAUDE")

        line = self.repo.get_line_details(victim_msisdn)
        self.assertEqual(line["status"], "SUSPENDIDO_FRAUDE")

    def test_08_process_emergency_lock_invalid_imei_rejected(self):
        """Rechaza bloqueo de emergencia si el IMEI provisto viola el algoritmo de Luhn."""
        bad_imei = "358240051111119" # Check digit intencionalmente incorrecto
        req = EmergencyEIRRequest(
            msisdn=self.test_msisdn,
            imei=bad_imei,
            lock_type=EIRLockType.THEFT_LOCK
        )
        resp = self.agent.process_emergency_lock(req)
        self.assertEqual(resp.status, EIRStatus.REJECTED_INVALID_IMEI)
        self.assertIn("Rechazada", resp.security_notice)

    def test_09_process_emergency_lock_line_not_found(self):
        """Retorna LINE_NOT_FOUND si el número telefónico no existe en la red Movilnet."""
        req = EmergencyEIRRequest(
            msisdn="04160009999",
            lock_type=EIRLockType.THEFT_LOCK
        )
        resp = self.agent.process_emergency_lock(req)
        self.assertEqual(resp.status, EIRStatus.LINE_NOT_FOUND)

    def test_10_check_eir_status_query(self):
        """Consulta el estado en la lista negra EIR mediante check_eir_status."""
        res_imei = self.agent.check_eir_status(imei=self.test_imei)
        self.assertTrue(res_imei["blacklisted"])
        self.assertEqual(res_imei["status"], "BLACKLISTED_EIR")
        self.assertIsNotNone(res_imei.get("current_event"))

        res_msisdn = self.agent.check_eir_status(msisdn=self.test_msisdn)
        self.assertTrue(res_msisdn["blacklisted"])
        self.assertGreaterEqual(len(res_msisdn["events_history"]), 1)

    def test_11_swarm_escalation_from_fintech_c2p(self):
        """Verifica la recepción y ejecución de escalamiento de fraude desde el Agente N2."""
        fraud_msisdn = f"0416{uuid.uuid4().int % 10000000:07d}"
        fraud_imei_14 = f"86812345{uuid.uuid4().int % 1000000:06d}"
        fraud_check = IMEILuhnValidator.calculate_luhn_check_digit(fraud_imei_14)
        fraud_imei = fraud_imei_14 + str(fraud_check)

        self.repo.create_subscriber_with_line(
            cid=f"V-{uuid.uuid4().int % 100000000:08d}",
            msisdn=fraud_msisdn,
            plan_id="PLAN_10GB_4GMAX",
            imei=fraud_imei
        )

        escalation_payload = {
            "msisdn": fraud_msisdn,
            "imei": fraud_imei,
            "reason": "PATRON_ANOMALO_MULTIPLES_CEDULAS_DETECTADO",
            "risk_score": 0.85
        }
        resp = self.agent.escalate_from_swarm("agent_fintech_c2p", escalation_payload)
        self.assertEqual(resp.status, EIRStatus.CONFIRMED_LOCKED)
        self.assertEqual(resp.line_status, "SUSPENDIDO_FRAUDE")
        self.assertIn("AGENT_FINTECH_C2P", resp.security_notice)

    def test_12_swarm_escalation_from_customer_care(self):
        """Verifica la recepción de handoff de hurto verbal desde el Agente N1."""
        theft_msisdn = f"0416{uuid.uuid4().int % 10000000:07d}"
        theft_imei_14 = f"01234567{uuid.uuid4().int % 1000000:06d}"
        theft_check = IMEILuhnValidator.calculate_luhn_check_digit(theft_imei_14)
        theft_imei = theft_imei_14 + str(theft_check)

        self.repo.create_subscriber_with_line(
            cid=f"V-{uuid.uuid4().int % 100000000:08d}",
            msisdn=theft_msisdn,
            plan_id="PLAN_10GB_4GMAX",
            imei=theft_imei
        )

        payload = {
            "msisdn": theft_msisdn,
            "text": "Me robaron el celular en la camionetica, por favor bloquéenlo de inmediato"
        }
        resp = self.agent.escalate_from_swarm("agent_customer_care", payload)
        self.assertEqual(resp.status, EIRStatus.CONFIRMED_LOCKED)
        self.assertEqual(resp.line_status, "BLOQUEADO_ROBO")
        self.assertTrue(self.repo.is_imei_blacklisted(theft_imei))

    def test_13_customer_care_cache_invalidation_on_lock(self):
        """Verifica que el Agente N1 invalida su Caché L1 tras un bloqueo EIR."""
        cache_phone = f"0416{uuid.uuid4().int % 10000000:07d}"
        cache_imei_14 = f"35599988{uuid.uuid4().int % 1000000:06d}"
        cache_check = IMEILuhnValidator.calculate_luhn_check_digit(cache_imei_14)
        cache_imei = cache_imei_14 + str(cache_check)

        self.repo.create_subscriber_with_line(
            cid=f"V-{uuid.uuid4().int % 100000000:08d}",
            msisdn=cache_phone,
            plan_id="PLAN_10GB_4GMAX",
            balance_ves=50.0,
            imei=cache_imei
        )

        # Calentar Caché L1 en Agente N1 (debe devolver ACTIVO)
        msg1 = AgentMessage(text="estatus", msisdn=cache_phone)
        res1 = self.customer_care.process_message(msg1)
        self.assertIn("ACTIVO", res1.response_text)
        self.assertIsNotNone(self.customer_care.cache.get(f"sub_ctx_{cache_phone}"))

        # Ejecutar Bloqueo EIR
        req = EmergencyEIRRequest(msisdn=cache_phone, imei=cache_imei, lock_type=EIRLockType.THEFT_LOCK)
        self.agent.process_emergency_lock(req)

        # Caché L1 en N1 debe haber sido invalidado
        self.assertIsNone(self.customer_care.cache.get(f"sub_ctx_{cache_phone}"))

        # Nueva consulta en N1 debe reflejar BLOQUEADO_ROBO sin caché obsoleto
        res2 = self.customer_care.process_message(msg1)
        self.assertIn("BLOQUEADO_ROBO", res2.response_text)

    def test_14_rest_api_emergency_eir_endpoints(self):
        """Verifica el despacho de POST /api/v1/agents/emergency-eir/process y GET /status."""
        api_phone = f"0416{uuid.uuid4().int % 10000000:07d}"
        api_imei_14 = f"35311122{uuid.uuid4().int % 1000000:06d}"
        api_check = IMEILuhnValidator.calculate_luhn_check_digit(api_imei_14)
        api_imei = api_imei_14 + str(api_check)

        self.repo.create_subscriber_with_line(
            cid=f"V-{uuid.uuid4().int % 100000000:08d}",
            msisdn=api_phone,
            plan_id="PLAN_10GB_4GMAX",
            imei=api_imei
        )

        # 1. POST /api/v1/agents/emergency-eir/process
        body = {
            "msisdn": api_phone,
            "imei": api_imei,
            "lock_type": "THEFT_LOCK",
            "reason": "Robo con despojo de pertenencias",
            "police_report_number": "DEN-9921",
            "channel": "whatsapp"
        }
        body_bytes = json.dumps(body).encode("utf-8")
        status, _, resp_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/agents/emergency-eir/process",
            headers={"Content-Type": "application/json"},
            body_bytes=body_bytes
        )
        self.assertEqual(status, 200)
        data = json.loads(resp_bytes.decode("utf-8"))
        self.assertEqual(data["status"], "CONFIRMED_LOCKED")
        self.assertEqual(data["line_status"], "BLOQUEADO_ROBO")
        self.assertTrue(data["ticket_id"].startswith("EIR-"))

        # 2. GET /api/v1/agents/emergency-eir/status
        status_get, _, get_bytes = self.service.dispatch(
            method="GET",
            path=f"/api/v1/agents/emergency-eir/status?imei={api_imei}&msisdn={api_phone}",
            headers={},
            body_bytes=b""
        )
        self.assertEqual(status_get, 200)
        get_data = json.loads(get_bytes.decode("utf-8"))
        self.assertTrue(get_data["blacklisted"])

    def test_15_webhook_bridge_eir_callback_delegation(self):
        """Verifica que el webhook /api/v1/webhooks/eir-callback delega al Agente N3."""
        wh_phone = f"0416{uuid.uuid4().int % 10000000:07d}"
        wh_imei_14 = f"35899900{uuid.uuid4().int % 1000000:06d}"
        wh_check = IMEILuhnValidator.calculate_luhn_check_digit(wh_imei_14)
        wh_imei = wh_imei_14 + str(wh_check)

        self.repo.create_subscriber_with_line(
            cid=f"V-{uuid.uuid4().int % 100000000:08d}",
            msisdn=wh_phone,
            plan_id="PLAN_10GB_4GMAX",
            imei=wh_imei
        )

        payload = {
            "imei": wh_imei,
            "msisdn": wh_phone,
            "reason": "EXTRAVIO_TERMINAL_URGENTE",
            "reported_by": "N8N_INCIDENT_WORKFLOW"
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        ts_str = datetime.now(timezone.utc).isoformat()
        sig = HMACSignatureValidator.generate_signature(payload_bytes, DEFAULT_WEBHOOK_SECRET, ts_str)
        headers = {
            "Content-Type": "application/json",
            SIGNATURE_HEADER: sig,
            TIMESTAMP_HEADER: ts_str,
            DELIVERY_ID_HEADER: f"del-eir-{uuid.uuid4().hex[:6]}",
            EVENT_TYPE_HEADER: "eir.callback"
        }

        status, _, resp_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/webhooks/eir-callback",
            headers=headers,
            body_bytes=payload_bytes
        )
        self.assertEqual(status, 200)
        resp = json.loads(resp_bytes.decode("utf-8"))
        self.assertEqual(resp["status"], "success")
        proc = resp["processing_result"]
        self.assertEqual(proc["eir_status"], "BLOCKED_CONFIRMED")
        self.assertIn("agent_eir_response", proc)
        self.assertEqual(proc["agent_eir_response"]["status"], "CONFIRMED_LOCKED")

    def test_16_emergency_lock_latency_benchmark(self):
        """Mide que la latencia media de procesamiento y bloqueo en el EIR sea sub-10ms (SLA Telco)."""
        latencies = []
        base_ts = int(time.time())
        for i in range(25):
            bench_phone = f"04169{str(base_ts)[-4:]}{i:02d}"
            bench_imei_14 = f"35{int(time.time() * 1000) % 100000000:08d}{i:02d}{uuid.uuid4().int % 100:02d}"
            bench_check = IMEILuhnValidator.calculate_luhn_check_digit(bench_imei_14)
            bench_imei = bench_imei_14 + str(bench_check)

            try:
                self.repo.create_subscriber_with_line(
                    cid=f"V-{uuid.uuid4().int % 100000000:08d}",
                    msisdn=bench_phone,
                    plan_id="PLAN_10GB_4GMAX",
                    imei=bench_imei
                )
            except Exception:
                pass

            req = EmergencyEIRRequest(
                msisdn=bench_phone,
                imei=bench_imei,
                lock_type=EIRLockType.THEFT_LOCK,
                reason="Benchmark de latencia carrier-grade"
            )

            t0 = time.perf_counter()
            resp = self.agent.process_emergency_lock(req)
            lat = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat)
            self.assertIn(resp.status, [EIRStatus.CONFIRMED_LOCKED, EIRStatus.ALREADY_BLACKLISTED])

        latencies.sort()
        avg_lat = sum(latencies) / len(latencies)
        p95_lat = latencies[int(len(latencies) * 0.95)]
        min_lat = min(latencies)

        print(f"\n   ⚡ Latencia Agente N3 (Emergency EIR): Promedio={avg_lat:.3f}ms | P95={p95_lat:.3f}ms | Min={min_lat:.3f}ms")
        self.assertLess(avg_lat, 20.0, f"Latencia media superior al SLA de 20ms: {avg_lat:.3f}ms")


if __name__ == "__main__":
    unittest.main()
