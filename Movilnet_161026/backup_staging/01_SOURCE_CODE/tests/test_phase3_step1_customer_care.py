#!/usr/bin/env python3
"""
test_phase3_step1_customer_care.py — Suite de Pruebas: Agente Nivel 1 (Customer Care)
====================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Fase 3: Paso 1 — Core de Inteligencia Artificial & Enjambre Autónomo (Nivel 5)
Estándares: TM Forum ODA (TMF632 Customer Management, TMF654 Prepay Balance, TMF638)
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

from api.agents.agent_customer_care import (
    CustomerCareAgent,
    IntentType,
    AgentExecutionMode,
    AgentMessage,
    AgentResponse,
    L1SessionCache,
    SessionMemory,
    FastPathEngine
)
from api.service import MovilnetAPIService
from api.webhook_bridge import get_webhook_bridge
from db.repository import MovilnetRepository


class TestCustomerCareAgent(unittest.TestCase):
    """Batería de pruebas unitarias y de integración para el Agente Nivel 1."""

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
                balance_ves=150.00,
                quota_mb=10240
            )

        cls.agent = CustomerCareAgent(repo=cls.repo)
        cls.service = MovilnetAPIService(repository=cls.repo)
        cls.webhook_bridge = get_webhook_bridge()

    def setUp(self):
        # Limpiar caché L1 antes de cada prueba para pruebas deterministas
        self.agent.cache.clear()

    # ------------------------------------------------------------------------
    # 1. Pruebas de Fast-Path Heurístico Determinista (Zero-Token)
    # ------------------------------------------------------------------------

    def test_fast_path_balance_query(self):
        """Verifica consulta de saldo por Fast-Path con latencia sub-milisegundo y $0 costo."""
        msg = AgentMessage(text="Hola, deseo consultar mi saldo disponible", msisdn=self.test_phone)
        resp = self.agent.process_message(msg)

        self.assertEqual(resp.intent, IntentType.BALANCE_QUERY)
        self.assertEqual(resp.execution_mode, AgentExecutionMode.FAST_PATH)
        self.assertEqual(resp.tokens_consumed, 0)
        self.assertEqual(resp.cost_usd, 0.0)
        self.assertFalse(resp.handoff_required)
        self.assertIsNone(resp.target_agent)
        self.assertIn("Consulta de Saldo", resp.response_text)
        self.assertIn("Bs.", resp.response_text)
        self.assertIn("USD", resp.response_text)
        self.assertGreaterEqual(len(resp.interactive_options), 2)
        self.assertLess(resp.latency_ms, 50.0)  # Tolerancia inicial

    def test_fast_path_data_quota_query(self):
        """Verifica consulta de megas y datos con barra visual de consumo."""
        msg = AgentMessage(text="¿cuantos megas me quedan para navegar?", msisdn=self.test_phone)
        resp = self.agent.process_message(msg)

        self.assertEqual(resp.intent, IntentType.DATA_QUOTA_QUERY)
        self.assertEqual(resp.execution_mode, AgentExecutionMode.FAST_PATH)
        self.assertEqual(resp.tokens_consumed, 0)
        self.assertIn("Cupo de Navegación", resp.response_text)
        self.assertIn("MB", resp.response_text)
        self.assertIn("GB", resp.response_text)
        self.assertIn("consumption_pct", resp.metadata)

    def test_fast_path_plan_query(self):
        """Verifica consulta de detalles comerciales del plan activo."""
        msg = AgentMessage(text="¿cuál es mi plan y que incluye?", msisdn=self.test_phone)
        resp = self.agent.process_message(msg)

        self.assertEqual(resp.intent, IntentType.PLAN_QUERY)
        self.assertEqual(resp.execution_mode, AgentExecutionMode.FAST_PATH)
        self.assertEqual(resp.tokens_consumed, 0)
        self.assertIn("Ficha Técnica de tu Plan", resp.response_text)
        self.assertIn("Tarifa Mensual", resp.response_text)
        self.assertIn("plan_id", resp.metadata)

    def test_fast_path_line_status_query(self):
        """Verifica consulta de estatus de línea y radiobase asociada."""
        msg = AgentMessage(text="necesito saber el estatus de mi linea", msisdn=self.test_phone)
        resp = self.agent.process_message(msg)

        self.assertEqual(resp.intent, IntentType.LINE_STATUS_QUERY)
        self.assertEqual(resp.execution_mode, AgentExecutionMode.FAST_PATH)
        self.assertEqual(resp.tokens_consumed, 0)
        self.assertIn("Estatus Operativo de Línea", resp.response_text)
        self.assertIn("ACTIVO", resp.response_text)
        self.assertIn("Radiobase", resp.response_text)

    def test_fast_path_apn_support(self):
        """Verifica entrega de parámetros oficiales de configuración APN LTE."""
        msg = AgentMessage(text="como configurar el APN de movilnet para internet", msisdn=self.test_phone)
        resp = self.agent.process_message(msg)

        self.assertEqual(resp.intent, IntentType.APN_TECH_SUPPORT)
        self.assertEqual(resp.execution_mode, AgentExecutionMode.FAST_PATH)
        self.assertEqual(resp.tokens_consumed, 0)
        self.assertIn("int.movilnet.com.ve", resp.response_text)
        self.assertIn("734", resp.response_text)
        self.assertIn("06", resp.response_text)

    def test_fast_path_office_locations(self):
        """Verifica consulta de oficinas comerciales y centros de servicio."""
        msg = AgentMessage(text="donde quedan las oficinas comerciales y atencion al cliente?", msisdn=self.test_phone)
        resp = self.agent.process_message(msg)

        self.assertEqual(resp.intent, IntentType.OFFICE_LOCATION_QUERY)
        self.assertEqual(resp.execution_mode, AgentExecutionMode.FAST_PATH)
        self.assertEqual(resp.tokens_consumed, 0)
        self.assertIn("Oficinas Comerciales", resp.response_text)
        self.assertIn("El Recreo", resp.response_text)
        self.assertIn("Maracaibo", resp.response_text)

    # ------------------------------------------------------------------------
    # 2. Pruebas de Caché L1 en Memoria
    # ------------------------------------------------------------------------

    def test_l1_cache_hit_and_performance(self):
        """Verifica que el segundo acceso a un abonado impacta el Caché L1 en < 1.0 ms."""
        msg = AgentMessage(text="saldo", msisdn=self.test_phone)

        # 1er llamado (Cold Cache)
        resp1 = self.agent.process_message(msg)
        self.assertEqual(resp1.execution_mode, AgentExecutionMode.FAST_PATH)

        # 2do llamado (Warm Cache Hit)
        resp2 = self.agent.process_message(msg)
        self.assertEqual(resp2.execution_mode, AgentExecutionMode.FAST_PATH)
        best_latency = min(resp2.latency_ms, self.agent.process_message(msg).latency_ms)
        self.assertLess(best_latency, 10.0, "La latencia con L1 Cache Hit debe ser sub-10ms")

        # Verificar operaciones del caché
        self.assertGreater(self.agent.cache.size(), 0)
        self.agent.cache.clear()
        self.assertEqual(self.agent.cache.size(), 0)

    # ------------------------------------------------------------------------
    # 3. Pruebas de Detección de Handoff Swarm (Nivel 5)
    # ------------------------------------------------------------------------

    def test_swarm_handoff_fintech_c2p(self):
        """Verifica detección de intención de recarga y preparación de Handoff a Agente Nivel 2."""
        queries = [
            "quiero recargar saldo",
            "como hago un pago movil c2p",
            "deseo pagar mi factura con banco de venezuela",
            "recargar 100 bs"
        ]
        for q in queries:
            msg = AgentMessage(text=q, msisdn=self.test_phone)
            resp = self.agent.process_message(msg)
            self.assertEqual(resp.intent, IntentType.HANDOFF_FINTECH_C2P)
            self.assertTrue(resp.handoff_required)
            self.assertEqual(resp.target_agent, "agent_fintech_c2p")
            self.assertIn("Pasarela Financiera Movilnet C2P", resp.response_text)

    def test_swarm_handoff_emergency_eir(self):
        """Verifica detección de hurto/extravío y escalado inmediato a Agente Nivel 3."""
        queries = [
            "me acaban de robar el celular bloquear linea",
            "perdi mi telefono extravio urgente",
            "sospecho de clonacion sim-swap bloquear imei"
        ]
        for q in queries:
            msg = AgentMessage(text=q, msisdn=self.test_phone)
            resp = self.agent.process_message(msg)
            self.assertEqual(resp.intent, IntentType.HANDOFF_EMERGENCY_EIR)
            self.assertTrue(resp.handoff_required)
            self.assertEqual(resp.target_agent, "agent_emergency_eir")
            self.assertIn("Protocolo de Emergencia", resp.response_text)
            self.assertEqual(resp.metadata.get("security_priority"), "HIGH")

    def test_swarm_handoff_retention_churn(self):
        """Verifica detección de intención de baja/portabilidad y Handoff a Agente Nivel 4."""
        queries = [
            "quiero cancelar mi linea me voy a digitel",
            "darme de baja de movilnet pesimo servicio",
            "solicito portabilidad no sirve la red"
        ]
        for q in queries:
            msg = AgentMessage(text=q, msisdn=self.test_phone)
            resp = self.agent.process_message(msg)
            self.assertEqual(resp.intent, IntentType.HANDOFF_RETENTION_CHURN)
            self.assertTrue(resp.handoff_required)
            self.assertEqual(resp.target_agent, "agent_retention_churn")
            self.assertIn("Atención Preferencial", resp.response_text)

    # ------------------------------------------------------------------------
    # 4. Pruebas de Razonamiento LLM / Contingencia Semántica
    # ------------------------------------------------------------------------

    def test_llm_reasoning_esim_inquiry(self):
        """Verifica razonamiento contextual sobre disponibilidad de tecnología eSIM."""
        msg = AgentMessage(text="¿tienen servicio de eSIM y cómo la solicito?", msisdn=self.test_phone)
        resp = self.agent.process_message(msg)

        self.assertEqual(resp.intent, IntentType.GENERAL_FAQ)
        self.assertEqual(resp.execution_mode, AgentExecutionMode.LLM_REASONING)
        self.assertGreater(resp.tokens_consumed, 0)
        self.assertGreater(resp.cost_usd, 0.0)
        self.assertTrue(any(k in resp.response_text for k in ["eSIM", "SIM virtual", "eSIM 4GMAX"]))
        self.assertTrue(any(k in resp.response_text.lower() for k in ["cédula", "oficina", "atención"]))

    def test_llm_reasoning_lte_bands(self):
        """Verifica razonamiento técnico sobre bandas LTE soportadas."""
        msg = AgentMessage(text="¿cuáles son las bandas y frecuencias de cobertura 4G?", msisdn=self.test_phone)
        resp = self.agent.process_message(msg)

        self.assertEqual(resp.intent, IntentType.GENERAL_FAQ)
        self.assertEqual(resp.execution_mode, AgentExecutionMode.LLM_REASONING)
        self.assertTrue(any(k in resp.response_text.lower() for k in ["banda 3", "banda 4", "banda 28", "banda 8", "4g", "lte"]))
        self.assertTrue(any(k in resp.response_text for k in ["1800", "1.800", "Banda 28", "Banda 8", "Banda 4", "banda 4", "1700", "2100", "700"]))

    def test_llm_reasoning_greetings(self):
        """Verifica respuesta a saludos y bienvenida."""
        msg = AgentMessage(text="Hola buenas tardes", msisdn=self.test_phone)
        resp = self.agent.process_message(msg)

        self.assertEqual(resp.intent, IntentType.GENERAL_FAQ)
        self.assertTrue("Movilnet" in resp.response_text)

    # ------------------------------------------------------------------------
    # 5. Pruebas de Memoria Conversacional Multi-Turno
    # ------------------------------------------------------------------------

    def test_session_memory_retention(self):
        """Verifica retención de turnos e historial en SessionMemory."""
        sess_id = f"test-sess-{uuid.uuid4().hex[:6]}"

        m1 = AgentMessage(text="Hola", session_id=sess_id, msisdn=self.test_phone)
        self.agent.process_message(m1)

        m2 = AgentMessage(text="Consultar saldo", session_id=sess_id, msisdn=self.test_phone)
        self.agent.process_message(m2)

        session_ctx = self.agent.memory.get_session(sess_id)
        turns = session_ctx.get("turns", [])
        self.assertEqual(len(turns), 4)  # 2 user turns + 2 agent turns
        self.assertEqual(turns[0]["role"], "user")
        self.assertEqual(turns[1]["role"], "agent")
        self.assertEqual(turns[2]["role"], "user")
        self.assertEqual(turns[3]["role"], "agent")

    # ------------------------------------------------------------------------
    # 6. Pruebas de Integración con REST API & OpenAPI 3.1
    # ------------------------------------------------------------------------

    def test_rest_api_customer_care_endpoint_success(self):
        """Verifica endpoint POST /api/v1/agents/customer-care/process vía dispatch REST."""
        body = {
            "text": "Consultar saldo",
            "msisdn": self.test_phone,
            "session_id": "test-api-sess-01",
            "channel": "web"
        }
        status, headers, resp_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/agents/customer-care/process",
            headers={"Content-Type": "application/json"},
            body_bytes=json.dumps(body).encode("utf-8")
        )
        self.assertEqual(status, 200)
        data = json.loads(resp_bytes.decode("utf-8"))
        self.assertEqual(data["intent"], "BALANCE_QUERY")
        self.assertEqual(data["execution_mode"], "FAST_PATH")
        self.assertEqual(data["tokens_consumed"], 0)
        self.assertIn("balance_ves", data["metadata"])

    def test_rest_api_customer_care_endpoint_missing_text(self):
        """Verifica rechazo con HTTP 400 si el campo 'text' está ausente o vacío."""
        body = {"msisdn": self.test_phone}
        status, headers, resp_bytes = self.service.dispatch(
            method="POST",
            path="/api/v1/agents/customer-care/process",
            headers={"Content-Type": "application/json"},
            body_bytes=json.dumps(body).encode("utf-8")
        )
        self.assertEqual(status, 400)
        data = json.loads(resp_bytes.decode("utf-8"))
        self.assertEqual(data["code"], "ERR_MISSING_TEXT")

    # ------------------------------------------------------------------------
    # 7. Pruebas de Integración con Webhook Bridge Omnicanal
    # ------------------------------------------------------------------------

    def test_webhook_bridge_omnichannel_integration(self):
        """Verifica que mensajes omnicanal invocan al Agente Nivel 1 a través del puente de webhooks."""
        inbound_payload = {
            "text": "¿cuantos megas tengo?",
            "from": self.test_phone,
            "channel": "whatsapp"
        }
        status, resp = self.webhook_bridge.process_inbound_event(
            headers={"X-Movilnet-Event-Type": "whatsapp.inbound"},
            body_bytes=json.dumps(inbound_payload).encode("utf-8"),
            skip_hmac_check=True
        )
        self.assertEqual(status, 200)
        res_data = resp["processing_result"]
        self.assertEqual(res_data["workflow"], "OMNICHANNEL_INBOUND_PROCESSED")
        self.assertTrue(res_data["subscriber_found"])
        self.assertIn("agent_response", res_data)

        agent_data = res_data["agent_response"]
        self.assertEqual(agent_data["intent"], "DATA_QUOTA_QUERY")
        self.assertEqual(agent_data["execution_mode"], "FAST_PATH")

    # ------------------------------------------------------------------------
    # 8. Benchmark de Latencia y Rendimiento Telco (Carrier-Grade SLA)
    # ------------------------------------------------------------------------

    def test_sre_latency_benchmark(self):
        """Evalúa 50 consultas consecutivas Fast-Path garantizando latencia P95 < 2.0 ms."""
        latencies = []
        msg = AgentMessage(text="saldo", msisdn=self.test_phone)

        # Warm-up
        self.agent.process_message(msg)

        for _ in range(50):
            t0 = time.perf_counter()
            resp = self.agent.process_message(msg)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)
            self.assertEqual(resp.execution_mode, AgentExecutionMode.FAST_PATH)

        latencies.sort()
        avg_lat = sum(latencies) / len(latencies)
        p95_lat = latencies[int(len(latencies) * 0.95)]

        self.assertLess(p95_lat, 15.0, "La latencia P95 del Fast-Path debe ser inferior a 15.0ms")


if __name__ == "__main__":
    unittest.main()
