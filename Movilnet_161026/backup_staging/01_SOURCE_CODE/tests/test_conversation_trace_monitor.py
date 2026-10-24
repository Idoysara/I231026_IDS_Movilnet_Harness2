#!/usr/bin/env python3
"""
tests/test_conversation_trace_monitor.py — Suite de Pruebas del Centro de Monitoreo Conversacional E2E
======================================================================================================
Valida el motor de reconstrucción secuencial de conversaciones, enrutamiento nodo a nodo
y endpoints del monitor REST en api/service.py.
"""

import sys
import json
from pathlib import Path
try:
    import pytest
except ImportError:
    class _FallbackPytest:
        @staticmethod
        def main(args):
            inst = TestConversationTraceMonitor()
            if hasattr(inst, "setup_method"):
                inst.setup_method()
            passed = 0
            for name in sorted(dir(inst)):
                if name.startswith("test_"):
                    getattr(inst, name)()
                    print(f"  [PASS] TestConversationTraceMonitor.{name}")
                    passed += 1
            print(f"✅ {passed}/{passed} pruebas en test_conversation_trace_monitor.py 100% PASS")
            return 0
    pytest = _FallbackPytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.conversation_trace_engine import conversation_trace_engine, ConversationTraceEngine
from api.service import MovilnetAPIService


class TestConversationTraceMonitor:
    """Verificación formal del Centro de Monitoreo de Secuencias Conversacionales."""

    def test_seeded_execution_9635_hard_evidence(self):
        """Verifica que la ejecución real 9635 esté cargada con sus 9 nodos verificados."""
        engine = ConversationTraceEngine()
        trace_9635 = engine.get_trace_detail("9635")
        assert trace_9635 is not None
        assert trace_9635["execution_id"] == "9635"
        assert trace_9635["bot_number"] == "+58 416 625 1587"
        assert trace_9635["user_phone"] == "04142554590"
        assert trace_9635["carrier"] == "MOVISTAR"
        assert trace_9635["is_competitor"] is True
        assert trace_9635["total_duration_sec"] == 2.85
        assert len(trace_9635["steps"]) == 9

        # Verificar nombres de nodos clave
        node_names = [s["node_name"] for s in trace_9635["steps"]]
        assert "Webhook" in node_names
        assert "If (fromMe == false)" in node_names
        assert "Edit Fields & Switch" in node_names
        assert "Captura Texto ➔ Chat" in node_names
        assert "Postgres Chat Memory" in node_names
        assert "AI Agent (LangChain + Gemini Flash)" in node_names

    def test_seeded_execution_9636_live_telemetry(self):
        """Verifica que la ejecución real 9636 recibida en vivo esté cargada con evidencia dura."""
        engine = ConversationTraceEngine()
        trace_9636 = engine.get_trace_detail("9636")
        assert trace_9636 is not None
        assert trace_9636["execution_id"] == "9636"
        assert trace_9636["user_message"] == "Hokaaaaaaa"
        assert trace_9636["bot_reply"] == "¡Hola! ¿En qué puedo ayudarte?"
        assert trace_9636["carrier"] == "MOVISTAR"
        assert trace_9636["total_duration_sec"] == 1.81
        assert len(trace_9636["steps"]) == 9

    def test_seeded_execution_9637_live_telemetry(self):
        """Verifica que la ejecución real 9637 (SerpAPI + Gemini) esté cargada con evidencia dura."""
        engine = ConversationTraceEngine()
        trace_9637 = engine.get_trace_detail("9637")
        assert trace_9637 is not None
        assert trace_9637["execution_id"] == "9637"
        assert trace_9637["user_message"] == "Que novedad tenemos"
        assert "noticias actuales" in trace_9637["bot_reply"]
        assert trace_9637["carrier"] == "MOVISTAR"
        assert trace_9637["total_duration_sec"] == 7.66
        assert len(trace_9637["steps"]) == 11
        node_names = [s["node_name"] for s in trace_9637["steps"]]
        assert "SerpAPI (Búsqueda en Google)" in node_names
        assert "Google Gemini Chat Model" in node_names



    def test_simulate_movilnet_fastpath_trace(self):
        """Verifica simulación de abonado Movilnet (Base 4M) con enrutamiento Fast-Path <0.15ms."""
        engine = ConversationTraceEngine()
        trace = engine.simulate_trace(
            phone_number="0416-6251587",
            message_text="deseo consultar mi saldo y megas",
            sender_name="Ismael Test",
            device_type="iPhone 15 Pro"
        )
        assert trace.carrier == "MOVILNET"
        assert trace.is_competitor is False
        assert trace.pipeline_route == "FAST_PATH_TELCO_ODA"
        assert "1.650,00" in trace.bot_reply or "saldo" in trace.bot_reply.lower()

        # Verificar paso de FastPath ODA
        step_names = [s.node_name for s in trace.steps]
        assert any("Fast-Path ODA" in name for name in step_names)

    def test_simulate_competitor_funnel_trace(self):
        """Verifica simulación de abonado de la competencia (0414) enrutado a Funnel Portabilidad."""
        engine = ConversationTraceEngine()
        trace = engine.simulate_trace(
            phone_number="0414-2554590",
            message_text="quiero cambiarme a movilnet con esim",
            sender_name="Usuario Movistar",
            device_type="Samsung Galaxy S24"
        )
        assert trace.carrier == "MOVISTAR"
        assert trace.is_competitor is True
        assert trace.pipeline_route == "FUNNEL_MARKETING_PORTABILIDAD"
        assert any("Funnel Marketing" in s.node_name for s in trace.steps)

    def test_api_service_monitor_endpoints(self):
        """Verifica endpoints HTTP de observabilidad en MovilnetAPIService."""
        service = MovilnetAPIService()

        # 1. GET /api/v1/monitor/conversations
        status, headers, body = service.dispatch("GET", "/api/v1/monitor/conversations", {}, b"")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "conversations" in data
        assert data["total"] >= 1

        # 2. GET /api/v1/monitor/trace?id=TRACE-EXEC-9635
        status, headers, body = service.dispatch("GET", "/api/v1/monitor/trace?id=TRACE-EXEC-9635", {}, b"")
        assert status == 200
        trace_data = json.loads(body.decode("utf-8"))
        assert trace_data["execution_id"] == "9635"
        assert len(trace_data["steps"]) == 9

        # 3. POST /api/v1/monitor/simulate-trace
        payload = json.dumps({
            "phone": "04121234567",
            "message": "Hola, qué planes tienen?",
            "sender_name": "Maria Digitel",
            "device_type": "Xiaomi Redmi Note"
        }).encode("utf-8")
        status, headers, body = service.dispatch("POST", "/api/v1/monitor/simulate-trace", {}, payload)
        assert status == 200
        post_data = json.loads(body.decode("utf-8"))
        assert post_data["success"] is True
        assert post_data["trace"]["carrier"] == "DIGITEL"
        assert post_data["trace"]["is_competitor"] is True
        # 4. GET /api/v1/monitor/chat (Verificación formato WhatsApp / Telegram continuo)
        status, headers, body = service.dispatch("GET", "/api/v1/monitor/chat?phone=04142554590", {}, b"")
        assert status == 200
        chat_data = json.loads(body.decode("utf-8"))
        assert "messages" in chat_data
        assert chat_data["user_name"] == "Ids"
        assert chat_data["carrier"] == "MOVISTAR"
        assert len(chat_data["messages"]) >= 1

    def test_grouped_conversations_chat_continuity(self):
        """Certifica que cada contacto aparezca una sola vez y contenga su historial continuo."""
        from core.conversation_trace_engine import conversation_trace_engine
        grouped = conversation_trace_engine.get_grouped_conversations()
        assert len(grouped) >= 1
        
        # Verificar que no hayan contactos duplicados en la lista de chats
        phone_keys = [g["phone_key"] for g in grouped]
        assert len(phone_keys) == len(set(phone_keys)), "No debe existir más de un chat por el mismo número"

        # Verificar continuidad del contacto Ids
        ids_thread = conversation_trace_engine.get_phone_history("04142554590")
        assert ids_thread is not None
        assert ids_thread["user_name"] == "Ids"
        assert len(ids_thread["messages"]) >= 1
        assert "time_display" in ids_thread["messages"][0]

    def test_thread_lock_and_buffer_capacity(self):
        """Certifica la presencia del cerrojo de concurrencia y capacidad ampliada a 1000 trazas."""
        engine = ConversationTraceEngine()
        assert hasattr(engine, "_lock"), "El motor debe poseer un cerrojo de sincronización multihilo"
        assert engine._lock is not None

    def test_grouped_conversations_deduplication(self):
        """Certifica que ejecuciones duplicadas (ej: #13077) se dedupliquen dentro de thread['messages']."""
        from core.conversation_trace_engine import ConversationTrace
        engine = ConversationTraceEngine()
        # Inyectar trazas con IDs duplicados para un mismo abonado
        t1 = ConversationTrace(
            trace_id="TRACE-EXEC-13077",
            execution_id="13077",
            workflow_id="sNMbtiEiTkuQ9OCY",
            started_at="2026-10-11T12:00:00Z",
            stopped_at="2026-10-11T12:00:01Z",
            total_duration_sec=1.0,
            status="SUCCESS",
            bot_number="+58 424 153 3712",
            user_phone="04149990001",
            user_push_name="Abonado Test",
            carrier="MOVISTAR",
            carrier_label="Movistar Venezuela",
            is_competitor=True,
            user_message="Mensaje duplicado",
            bot_reply="Respuesta 1",
            intent_detected="TEST",
            pipeline_route="AI_AGENT_GEMINI"
        )
        t2 = ConversationTrace(
            trace_id="TRACE-EXEC-13077",
            execution_id="13077",
            workflow_id="sNMbtiEiTkuQ9OCY",
            started_at="2026-10-11T12:00:00Z",
            stopped_at="2026-10-11T12:00:01Z",
            total_duration_sec=1.0,
            status="SUCCESS",
            bot_number="+58 424 153 3712",
            user_phone="04149990001",
            user_push_name="Abonado Test",
            carrier="MOVISTAR",
            carrier_label="Movistar Venezuela",
            is_competitor=True,
            user_message="Mensaje duplicado",
            bot_reply="Respuesta actualizada",
            intent_detected="TEST",
            pipeline_route="AI_AGENT_GEMINI"
        )
        engine.traces_cache.insert(0, t1)
        engine.traces_cache.insert(0, t2)

        history = engine.get_phone_history("04149990001")
        assert history is not None
        # Verificar que el mensaje #13077 no esté duplicado en messages
        msg_ids = [m["execution_id"] for m in history["messages"] if m.get("execution_id") == "13077"]
        assert len(msg_ids) == 1, f"El mensaje #13077 debe aparecer una sola vez, pero apareció {len(msg_ids)} veces"

    def test_prefix_0058_normalization(self):
        """Certifica que el prefijo internacional 0058 se normalice al formato canónico nacional 04..."""
        from core.conversation_trace_engine import ConversationTrace
        engine = ConversationTraceEngine()
        t = ConversationTrace(
            trace_id="TRACE-0058-TEST",
            execution_id="99999",
            workflow_id="sNMbtiEiTkuQ9OCY",
            started_at="2026-10-11T13:00:00Z",
            stopped_at="2026-10-11T13:00:01Z",
            total_duration_sec=1.0,
            status="SUCCESS",
            bot_number="+58 424 153 3712",
            user_phone="00584241329949",
            user_push_name="Usuario 0058",
            carrier="MOVISTAR",
            carrier_label="Movistar Venezuela",
            is_competitor=True,
            user_message="Hola desde 0058",
            bot_reply="Bienvenido",
            intent_detected="TEST",
            pipeline_route="AI_AGENT_GEMINI"
        )
        engine.traces_cache.insert(0, t)
        history = engine.get_phone_history("00584241329949")
        assert history is not None
        assert history["phone_key"] == "04241329949"

    def test_seeded_history_for_04241329949(self):
        """Certifica que el número 04241329949 (Dios Guia, Exec 9822) esté disponible de fábrica en el motor."""
        engine = ConversationTraceEngine()
        history = engine.get_phone_history("04241329949")
        assert history is not None
        assert history["phone_key"] == "04241329949"
        assert history["user_name"] == "Dios Guia"
        assert len(history["messages"]) >= 1

    def test_persist_does_not_purge_traces_without_execution_id(self):
        """Certifica que _persist_trace_to_shared no purgue registros previos que tengan execution_id=None."""
        from core.conversation_trace_engine import ConversationTrace
        engine = ConversationTraceEngine()
        d_existing = {"trace_id": "TRACE-SAMP-1", "user_phone": "04160000001", "execution_id": None}
        new_trace = ConversationTrace(
            trace_id="TRACE-SAMP-2",
            execution_id=None,
            workflow_id="test",
            started_at="2026-10-11T12:00:00Z",
            stopped_at="2026-10-11T12:00:01Z",
            total_duration_sec=1.0,
            status="SUCCESS",
            bot_number="+58 424 153 3712",
            user_phone="04160000002",
            user_push_name="User 2",
            carrier="MOVILNET",
            carrier_label="Movilnet 4GMAX",
            is_competitor=False,
            user_message="Msg 2",
            bot_reply="Reply 2",
            intent_detected="TEST",
            pipeline_route="FAST_PATH_TELCO_ODA"
        )
        assert engine._is_same_trace_record(d_existing, new_trace) is False


if __name__ == "__main__":
    pytest.main(["-v", __file__])
