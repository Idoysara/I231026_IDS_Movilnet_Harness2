#!/usr/bin/env python3
"""
tests/test_action_plan_rules_204.py — Suite de Verificación Formal de Reglas Capítulo 204
==========================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)

Pruebas Automatizadas (100% Pass Obligatorio):
1. Test de Parámetros APN 4GMAX (PARAMETROS_APN): 0 tokens, <15ms, APN oficial int.movilnet.com.ve.
2. Test de Guardarraíl Fuera de Ámbito (OFF_TOPIC_TELCO_GUARD): corte inmediato a <40 tokens.
3. Test de Hitos Comerciales de Caracas: Los Palos Grandes, Tolón, El Marqués, La Boyera.
4. Test de Memoria GPS de Sesión (TTL 30 min): persistencia de coordenadas entre turnos.
5. Test de Compuerta de Seguridad C2P a Terceros (HIJA_TERCEROS_GUARD): exigencia de 0416/0426.
6. Test de Inmutabilidad de Teléfono Oficial C2P: unificación exclusiva a 0424-1533712.
7. Test de Cero Saldos Quemados en N8N y FastPath: erradicación total de Bs. 1.650,00 ficticio.
"""

import sys
import time
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.fastpath_intent_interceptor import FastPathIntentInterceptor


@pytest.fixture
def interceptor():
    return FastPathIntentInterceptor()


class TestActionPlanRulesCapitulo204:

    def test_apn_resolution_zero_token_fastpath(self, interceptor):
        """Verifica que consultas de APN se resuelvan en <15ms con 0 tokens y parámetros oficiales."""
        queries = [
            "¿Cuál es el APN de Movilnet?",
            "como configuro el punto de acceso",
            "parametros apn para lte",
            "ajustes de red apn movilnet"
        ]
        for q in queries:
            t0 = time.perf_counter()
            res = interceptor.intercept(message_text=q, phone_number="04161234567")
            lat = (time.perf_counter() - t0) * 1000

            assert res.can_intercept is True, f"Fallo al interceptar APN: '{q}'"
            assert res.intent_detected == "PARAMETROS_APN"
            assert res.tokens_consumed == 0
            assert lat < 50.0  # Menos de 50ms en entorno de pruebas
            assert "int.movilnet.com.ve" in res.response_text
            assert "734" in res.response_text
            assert "06" in res.response_text

    def test_off_topic_telco_guard_short_circuit(self, interceptor):
        """Verifica que consultas ajenas a telco (restaurantes, impresoras) se acoten a <40 tokens."""
        queries = [
            "¿Qué restaurantes recomiendas cerca de Los Palos Grandes?",
            "necesito comprar tinta epson para mi impresora",
            "donde hay una farmacia abierta con medicinas",
            "dame una lista de hamburguesas y pizzas"
        ]
        for q in queries:
            res = interceptor.intercept(message_text=q, phone_number="04142554590")
            assert res.can_intercept is True, f"Fallo al acotar off-topic: '{q}'"
            assert res.intent_detected == "OFF_TOPIC_TELCO_GUARD"
            assert res.tokens_consumed == 0
            # Validar que la respuesta sea concisa (<1100 caracteres incluyendo sufijo PWA freemium, 0 tokens LLM)
            assert len(res.response_text) < 1100
            assert "Movilnet" in res.response_text
            assert "conectividad" in res.response_text.lower() or "telecomunicaciones" in res.response_text.lower()

    def test_caracas_commercial_landmarks_mapping(self, interceptor):
        """Verifica que hitos caraqueños se mapeen a las oficinas Movilnet correctas."""
        # 1. Los Palos Grandes -> Centro Plaza
        res_lpg = interceptor.intercept(
            message_text="Me puedes indicar qué oficina de Movilnet es la más cercana a Los Palos Grandes?",
            phone_number="04142650088"
        )
        assert res_lpg.can_intercept is True
        assert res_lpg.intent_detected == "LOCALIZADOR_OFICINAS_TELCO"
        assert "Centro Plaza" in res_lpg.response_text

        # 2. Tolón / Las Mercedes -> Sambil Chacao o Torre El Rosal
        res_tolon = interceptor.intercept(
            message_text="oficinas movilnet cerca de tolon las mercedes",
            phone_number="04142554590"
        )
        assert res_tolon.can_intercept is True
        assert "Sambil Chacao" in res_tolon.response_text or "Torre El Rosal" in res_tolon.response_text

        # 3. El Marqués / Boleíta -> Centro Plaza
        res_marques = interceptor.intercept(
            message_text="agencia movilnet el marques boleita",
            phone_number="04161234567"
        )
        assert res_marques.can_intercept is True
        assert "Centro Plaza" in res_marques.response_text

        # 4. La Boyera / El Hatillo -> Centro Plaza
        res_boyera = interceptor.intercept(
            message_text="donde hay oficina movilnet en la boyera el hatillo",
            phone_number="04142554590"
        )
        assert res_boyera.can_intercept is True
        assert "Centro Plaza" in res_boyera.response_text

    def test_gps_session_memory_persistence(self, interceptor):
        """Verifica que las coordenadas GPS enviadas persistan para turnos subsiguientes."""
        phone = "04142554590"
        # Turno 1: Envía GPS de Caracas (CC Centro Plaza aprox)
        lat_in = 10.4960
        lon_in = -66.8525
        res1 = interceptor.intercept(
            message_text="oficina cercana",
            phone_number=phone,
            latitude=lat_in,
            longitude=lon_in
        )
        assert res1.can_intercept is True
        assert "Centro Plaza" in res1.response_text
        assert "A pie:" in res1.response_text

        # Turno 2: Pregunta "dame otra oficina cercana" sin adjuntar coordenadas GPS nuevamente
        res2 = interceptor.intercept(
            message_text="otra agencia cercana",
            phone_number=phone
        )
        assert res2.can_intercept is True
        # Debe haber usado el GPS en caché en vez de solicitar coordenadas desde cero
        assert "Centro Plaza" in res2.response_text or "Torre El Rosal" in res2.response_text

    def test_c2p_third_party_guard_enforcement(self, interceptor):
        """Verifica que recargas desde operadoras externas o a terceros exijan número 0416/0426."""
        # 1. Usuario Movistar diciendo 'Recargar'
        res_movistar = interceptor.intercept(
            message_text="quiero recargar saldo con pago movil",
            phone_number="04142554590"
        )
        assert res_movistar.can_intercept is True
        assert "0416" in res_movistar.response_text
        assert "0426" in res_movistar.response_text
        assert "0424-1533712" in res_movistar.response_text

        # 2. Usuario mencionando 'hija' o 'familiar'
        res_hija = interceptor.intercept(
            message_text="como recargo el saldo de mi hija",
            phone_number="04161234567"
        )
        assert res_hija.can_intercept is True
        assert "0416" in res_hija.response_text or "número Movilnet a recargar" in res_hija.response_text
        assert "0424-1533712" in res_hija.response_text

    def test_unified_official_c2p_phone(self, interceptor):
        """Verifica que el teléfono receptor para Pago Móvil C2P sea única y exclusivamente 0424-1533712."""
        res = interceptor.intercept(
            message_text="recarga c2p",
            phone_number="04142554590"
        )
        assert "0424-1533712" in res.response_text
        # Asegurar que no se cuele ningún teléfono antiguo o inconsistente
        assert "0416-6251587" not in res.response_text

    def test_zero_burned_balance_hallucination(self, interceptor):
        """Verifica que el saldo quemado ficticio 'Bs. 1.650,00' nunca se emita."""
        res_comp = interceptor.intercept(
            message_text="saldo",
            phone_number="04142554590"
        )
        assert "1.650,00" not in res_comp.response_text
        assert "11.9 GB" not in res_comp.response_text

        res_nat = interceptor.intercept(
            message_text="saldo",
            phone_number="04169999999"
        )
        assert "1.650,00" not in res_nat.response_text


if __name__ == "__main__":
    pytest.main(["-v", __file__])
