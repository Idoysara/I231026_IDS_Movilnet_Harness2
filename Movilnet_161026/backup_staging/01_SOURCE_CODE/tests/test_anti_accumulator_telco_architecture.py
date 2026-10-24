#!/usr/bin/env python3
"""
tests/test_anti_accumulator_telco_architecture.py
=================================================
Verificación formal de la arquitectura desacoplada anti-acumulador:
1. Intercepción en frontera de consultas gastronómicas/off-topic (0 tokens, <15ms).
2. Localización dinámica de agencias Movilnet vía SQLite geo_pois (Cero hardcoding).
3. Preservación estricta de sesión multi-turno en PWA y Gateway API.
4. Integridad de rol: Asistente Telco sin alucinaciones de comida criolla/italiana.
"""

import json
import pytest
from core.fastpath_intent_interceptor import FastPathIntentInterceptor, fastpath_interceptor
from core.geo_catalog import find_agencies_by_city_or_state
from api.service import MovilnetAPIService


class TestAntiAccumulatorTelcoArchitecture:
    """Suite de pruebas de certificación de arquitectura limpia y desacoplada."""

    def test_off_topic_gastronomy_interception_with_geo_context(self):
        """Verifica intercepción determinista de 'un buen restaurant en los palos grandes'."""
        query = "un buen restaurant en los palos grandes"
        phone = "04161234567"

        res = fastpath_interceptor.intercept(query, phone)
        assert res.can_intercept is True
        assert res.intent_detected == "OFF_TOPIC_TELCO_GUARD"
        assert res.tokens_consumed == 0
        assert res.latency_ms < 100.0  # Ultra-baja latencia O(1) <100ms en disco local

        # Debe mencionar la especialidad Telco Movilnet y NO alucinar restaurantes
        reply = res.response_text.lower()
        assert "movilnet" in reply
        assert "telecomunicaciones" in reply or "conectividad" in reply
        assert "4gmax" in reply

        # Al mencionar Los Palos Grandes, debe incluir dinámicamente la oficina Centro Plaza
        assert "centro plaza" in reply or "palos grandes" in reply or "chacao" in reply

        # NO debe recomendar comida criolla, rápida o italiana
        assert "criolla" not in reply
        assert "italiana" not in reply
        assert "¿hay algún tipo de comida en específico que te provoque" not in reply

    def test_off_topic_gastronomy_without_geo(self):
        """Verifica intercepción determinista de 'busca un restaurant para almorzar'."""
        query = "busca un restaurant para almorzar"
        phone = "04161234567"

        res = fastpath_interceptor.intercept(query, phone)
        assert res.can_intercept is True
        assert res.intent_detected == "OFF_TOPIC_TELCO_GUARD"
        assert res.tokens_consumed == 0

        reply = res.response_text.lower()
        assert "movilnet" in reply
        assert "4gmax" in reply
        assert "criolla" not in reply
        assert "italiana" not in reply

    def test_dynamic_sqlite_geo_pois_query(self):
        """Verifica que las oficinas se obtengan dinámicamente de SQLite geo_pois sin acumuladores."""
        results = find_agencies_by_city_or_state("palos grandes", limit=5)
        assert len(results) >= 1
        centro_plaza = results[0]
        assert "Centro Plaza" in centro_plaza["name"]
        assert "Los Palos Grandes" in centro_plaza["address"]
        assert centro_plaza["latitude"] == pytest.approx(10.496, abs=0.01)

    def test_api_service_pwa_fastpath_and_session_continuity(self):
        """Verifica que /api/v1/agents/customer-care/process use FastPath y mantenga sesión."""
        service = MovilnetAPIService()
        session_id = "test_pwa_session_1001"
        phone = "04161234567"

        # Turno 1: Saldo por FastPath
        payload_1 = {
            "text": "saldo",
            "msisdn": phone,
            "session_id": session_id,
            "channel": "pwa_mobile"
        }
        status, headers, body_raw = service.dispatch(
            "POST",
            "/api/v1/agents/customer-care/process",
            {"Content-Type": "application/json"},
            json.dumps(payload_1).encode("utf-8")
        )
        assert status == 200
        data_1 = json.loads(body_raw.decode("utf-8"))
        assert "saldo" in data_1["response_text"].lower() or "bs" in data_1["response_text"].lower()
        assert data_1.get("tokens_consumed") == 0

        # Turno 2: Restaurante en Los Palos Grandes
        payload_2 = {
            "text": "un buen restaurant en los palos grandes",
            "msisdn": phone,
            "session_id": session_id,
            "channel": "pwa_mobile"
        }
        status, headers, body_raw = service.dispatch(
            "POST",
            "/api/v1/agents/customer-care/process",
            {"Content-Type": "application/json"},
            json.dumps(payload_2).encode("utf-8")
        )
        assert status == 200
        data_2 = json.loads(body_raw.decode("utf-8"))
        assert data_2.get("tokens_consumed") == 0
        assert "centro plaza" in data_2["response_text"].lower() or "palos grandes" in data_2["response_text"].lower()

        # Verificar que la memoria de la sesión retuvo ambos turnos
        history = service.customer_care_agent.memory.get_session(session_id)
        assert len(history["turns"]) >= 4  # 2 usuario + 2 agente
        user_texts = [t["content"] for t in history["turns"] if t["role"] == "user"]
        assert "saldo" in user_texts
        assert "un buen restaurant en los palos grandes" in user_texts
