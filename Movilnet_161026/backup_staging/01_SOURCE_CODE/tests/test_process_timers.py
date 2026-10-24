#!/usr/bin/env python3
"""
tests/test_process_timers.py — Suite de Pruebas de Process Timers Conversacionales E2E
======================================================================================
Valida la medición temporal paso a paso desde el envío del abonado (T1) hasta la
entrega física en el dispositivo móvil (T7), erradicando falsas certificaciones.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import math
try:
    import pytest
except ImportError:
    class _Approx:
        def __init__(self, val, rel=1e-2):
            self.val = val
            self.rel = rel
        def __eq__(self, other):
            return math.isclose(self.val, other, rel_tol=self.rel, abs_tol=1e-4)
    class _FallbackPytest:
        approx = staticmethod(_Approx)
        @staticmethod
        def main(args):
            inst = TestProcessTimersE2E()
            passed = 0
            for name in sorted(dir(inst)):
                if name.startswith("test_"):
                    getattr(inst, name)()
                    print(f"  [PASS] TestProcessTimersE2E.{name}")
                    passed += 1
            print(f"✅ {passed}/{passed} pruebas en test_process_timers.py 100% PASS")
            return 0
    pytest = _FallbackPytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.conversation_trace_engine import (
    ConversationTraceEngine,
    ConversationTrace,
    PipelineNodeStep,
    compute_process_timers
)
from api.service import MovilnetAPIService


class TestProcessTimersE2E:
    """Verificación de la estructura y cálculo matemático de timers E2E."""

    def test_compute_process_timers_nominal_delivered(self):
        """Verifica el cálculo de los 8 hitos temporales cuando el mensaje es entregado."""
        t1_ts = "2026-10-11T20:00:00.000Z"
        t2_ts = "2026-10-11T20:00:00.150Z"
        t4_ts = "2026-10-11T20:00:00.450Z"
        t7_ts = "2026-10-11T20:00:01.200Z"

        timers = compute_process_timers(
            started_at=t2_ts,
            stopped_at=t4_ts,
            total_duration_sec=0.30,
            status="SUCCESS",
            message_timestamp=t1_ts,
            is_delivered=True,
            t7_delivered_ts=t7_ts
        )

        assert timers["t1_user_sent_ts"] is not None
        assert timers["t2_n8n_in_ts"] is not None
        assert timers["t3_core_resolved_ts"] is not None
        assert timers["t4_n8n_out_ts"] is not None
        assert timers["t5_evolution_queued_ts"] is not None
        assert timers["t6_meta_server_ack_ts"] is not None
        assert "2026-10-11T20:00:01.200" in timers["t7_phone_delivered_ts"]
        assert timers["t8_user_read_ts"] is not None

        # Deltas
        assert timers["delta_inbound_sec"] == pytest.approx(0.150, rel=1e-2)
        assert timers["delta_processing_sec"] == pytest.approx(0.300, rel=1e-2)
        assert timers["delta_delivery_sec"] is not None
        assert timers["delta_e2e_total_sec"] == pytest.approx(1.200, rel=1e-2)
        assert timers["delivery_state"] == "DELIVERY_ACK"
        assert "✓✓ Entregado" in timers["delivery_badge"]

    def test_compute_process_timers_en_cola_whatsapp(self):
        """Verifica que sin t7_phone_delivered_ts el estado sea EN_COLA_WHATSAPP."""
        t1_ts = "2026-10-11T20:00:00.000Z"
        t2_ts = "2026-10-11T20:00:00.100Z"
        t4_ts = "2026-10-11T20:00:00.350Z"

        timers = compute_process_timers(
            started_at=t2_ts,
            stopped_at=t4_ts,
            total_duration_sec=0.25,
            status="SUCCESS",
            message_timestamp=t1_ts,
            is_delivered=False
        )

        assert timers["t7_phone_delivered_ts"] is None
        assert timers["delivery_state"] == "EN_COLA_WHATSAPP"
        assert "⏳ En cola WhatsApp" in timers["delivery_badge"]
        assert timers["delta_delivery_sec"] is None
        assert timers["delta_e2e_total_sec"] is None
        assert timers["delta_outbound_queue_sec"] == timers["queue_wait_sec"]
        assert timers["queue_wait_sec"] >= 0.0

    def test_message_timestamp_unix_epoch_conversion(self):
        """Verifica la conversión de unix seconds, milliseconds y float strings desde Evolution API."""
        # Segundos enteros: 1791164792 (año 2026)
        timers_sec = compute_process_timers(
            started_at="2026-10-11T20:00:01.000Z",
            message_timestamp=1791164792
        )
        assert "2026" in timers_sec["t1_user_sent_ts"]

        # Milliseconds: 1791164792000
        timers_ms = compute_process_timers(
            started_at="2026-10-11T20:00:01.000Z",
            message_timestamp=1791164792000
        )
        assert "2026" in timers_ms["t1_user_sent_ts"]

        # String con decimales / flotante: "1791164792.5"
        timers_float_str = compute_process_timers(
            started_at="2026-10-11T20:00:01.000Z",
            message_timestamp="1791164792.5"
        )
        assert "2026" in timers_float_str["t1_user_sent_ts"]

        # Clamping de reloj futuro (usuario con hora adelantada)
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        timers_future = compute_process_timers(
            started_at="2026-10-11T20:00:01.000Z",
            message_timestamp=future_ts
        )
        assert timers_future["delta_inbound_sec"] >= 0.0

    def test_simulate_trace_delivered_vs_queued(self):
        """Verifica simulate_trace con delivered=True y delivered=False."""
        engine = ConversationTraceEngine()
        trace_delivered = engine.simulate_trace(
            phone_number="04161112233",
            message_text="saldo",
            delivered=True
        )
        assert trace_delivered.process_timers["t7_phone_delivered_ts"] is not None
        assert trace_delivered.process_timers["delivery_state"] == "DELIVERY_ACK"

        trace_queued = engine.simulate_trace(
            phone_number="04161112234",
            message_text="saldo",
            delivered=False
        )
        assert trace_queued.process_timers["t7_phone_delivered_ts"] is None
        assert trace_queued.process_timers["delivery_state"] == "EN_COLA_WHATSAPP"

    def test_api_conversations_endpoint_exposes_process_timers(self):
        """Verifica que /api/v1/monitor/conversations exponga process_timers sin skew de traces pendientes."""
        service = MovilnetAPIService()
        status, headers, body = service.dispatch("GET", "/api/v1/monitor/conversations", {}, b"")
        assert status == 200
        data = json.loads(body.decode("utf-8"))

        assert "process_timers" in data
        metrics = data["process_timers"]
        assert "avg_e2e_total_sec" in metrics
        assert "avg_processing_sec" in metrics
        assert "avg_queue_wait_sec" in metrics
        assert "in_queue_count" in metrics
        assert "delivered_count" in metrics

        # El promedio de E2E para mensajes entregados debe ser sensato (< 120s en red real, sin alucinación de 32 horas)
        if metrics["delivered_count"] > 0:
            assert metrics["avg_e2e_total_sec"] < 120.0, f"avg_e2e_total_sec no debe estar inflado: {metrics['avg_e2e_total_sec']}"

        # Verificar que cada conversación tenga process_timers
        for conv in data["conversations"]:
            assert "process_timers" in conv
            timers = conv["process_timers"]
            assert "t1_user_sent_ts" in timers
            assert "t2_n8n_in_ts" in timers
            assert "t4_n8n_out_ts" in timers

    def test_grouped_conversations_messages_contain_timers(self):
        """Verifica que en get_grouped_conversations cada mensaje posea sus timers."""
        engine = ConversationTraceEngine()
        grouped = engine.get_grouped_conversations()
        assert len(grouped) >= 1
        for thread in grouped:
            assert "last_process_timers" in thread
            for msg in thread["messages"]:
                assert "process_timers" in msg
                timers = msg["process_timers"]
                assert "delta_inbound_sec" in timers
                assert "delta_processing_sec" in timers

    def test_dynamic_recalculation_of_pending_queue_wait(self):
        """Verifica que para mensajes en cola, el tiempo de espera se recalcule dinámicamente."""
        engine = ConversationTraceEngine()
        # Inyectar traza en cola ocurrida hace 30 segundos
        past_t2 = (datetime.now(timezone.utc) - timedelta(seconds=35)).isoformat()
        past_t4 = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
        t = ConversationTrace(
            trace_id="TRACE-TEST-QUEUE-1",
            execution_id="99991",
            workflow_id="sNMbtiEiTkuQ9OCY",
            started_at=past_t2,
            stopped_at=past_t4,
            total_duration_sec=5.0,
            status="SUCCESS",
            bot_number="+58 424 153 3712",
            user_phone="04169998877",
            user_push_name="Abonado Cola",
            carrier="MOVILNET",
            carrier_label="Movilnet 4GMAX",
            is_competitor=False,
            user_message="Saldo en cola",
            bot_reply="Tu saldo es Bs. 100",
            intent_detected="SALDO",
            pipeline_route="FAST_PATH_TELCO_ODA"
        )
        engine.traces_cache.insert(0, t)

        traces = engine.get_traces_list()
        found = next((tr for tr in traces if tr["trace_id"] == "TRACE-TEST-QUEUE-1"), None)
        assert found is not None
        assert found["delivery_status"] == "EN_COLA_WHATSAPP"
        q_sec = found["process_timers"]["queue_wait_sec"]
        assert q_sec >= 29.0, f"queue_wait_sec debe ser al menos 29s, obtenido: {q_sec}"
        assert found["process_timers"]["delta_outbound_queue_sec"] >= 29.0


    def test_compute_process_timers_error_state_zero_hallucination(self):
        """Verifica que en estado ERROR no se alucinen acuses SERVER_ACK ni tiempos de cola saliente."""
        t1_ts = "2026-10-13T15:30:00.000Z"
        t2_ts = "2026-10-13T15:30:00.150Z"
        t4_ts = "2026-10-13T15:30:01.200Z"

        timers = compute_process_timers(
            started_at=t2_ts,
            stopped_at=t4_ts,
            total_duration_sec=1.05,
            status="ERROR",
            message_timestamp=t1_ts,
            is_delivered=False
        )

        assert timers["t1_user_sent_ts"] is not None
        assert timers["t2_n8n_in_ts"] is not None
        assert timers["t3_core_resolved_ts"] is not None
        assert timers["t4_n8n_out_ts"] is not None
        # Invariantes ZH-MHEP: T5, T6, T7, T8 deben ser None si el flujo falló antes de despachar
        assert timers["t5_evolution_queued_ts"] is None
        assert timers["t6_meta_server_ack_ts"] is None
        assert timers["t7_phone_delivered_ts"] is None
        assert timers["t8_user_read_ts"] is None
        assert timers["delta_outbound_queue_sec"] is None
        assert timers["queue_wait_sec"] is None
        assert timers["delta_delivery_sec"] is None
        assert timers["delta_e2e_total_sec"] is None
        assert timers["delivery_state"] == "ERROR_RECURSO"
        assert "Fallo n8n Cloud (No enviado a WhatsApp)" in timers["delivery_badge"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
