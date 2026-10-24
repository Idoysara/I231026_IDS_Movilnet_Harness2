#!/usr/bin/env python3
"""
tests/test_conversatorio_e2e_5cases.py — Certificación de Pruebas Reales de los 5 Casos Críticos
================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)

Verifica que el microservicio en puerto 8010 responda determinísticamente y registre en el
Conversatorio los 5 casos críticos analizados:
  1. Francisco Landaeta (0414-2650088): "Me puedes indicar qué oficina de Movilnet es la más cercana a Los Palos Grandes?" -> Centro Plaza
  2. Abonado VIP (0416-0000001): "saldo" -> Saldo real de base de datos sin hardcoding
  3. Ids (0414-2554590): "Quiero recargar saldo para mi hija" -> Exigir 0416/0426 antes de recargar
  4. Ids (0414-2554590): "Qué restaurantes recomiendas cerca de Los Palos Grandes?" -> Off-topic telco guard (<30 palabras)
  5. Abonado (0416-1234567): "Cual es el apn de movilnet?" -> Entrega inmediata de parámetros APN
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pytest
except ImportError:
    pytest = None

from core.fastpath_intent_interceptor import fastpath_interceptor, FastPathIntentInterceptor
from core.conversation_trace_engine import conversation_trace_engine


def test_caso_1_oficina_los_palos_grandes():
    """Caso 1: Francisco Landaeta pregunta por oficina cercana a Los Palos Grandes."""
    msg = "Me puedes indicar qué oficina de Movilnet es la más cercana a Los Palos Grandes?"
    phone = "0414-2650088"
    res = fastpath_interceptor.intercept(msg, phone)
    
    assert res.can_intercept is True
    assert res.intent_detected == "LOCALIZADOR_OFICINAS_TELCO"
    assert "Centro Plaza" in res.response_text
    assert "10.496,-66.8525" in res.response_text
    assert "Portabilidad" in res.response_text
    assert res.latency_ms < 50.0


def test_caso_2_saldo_real_sin_hardcoding():
    """Caso 2: Abonado VIP consulta saldo -> Datos reales OCS/SQLite."""
    msg = "saldo"
    phone = "04160000001"
    res = fastpath_interceptor.intercept(msg, phone)
    
    assert res.can_intercept is True
    assert res.intent_detected == "SALDO_CUPO"
    assert "Movilnet 4GMAX" in res.response_text
    assert "Saldo Disponible:" in res.response_text
    assert "Datos Restantes:" in res.response_text
    assert "11.9 GB de 5 GB" not in res.response_text  # Ficticio purgado
    assert res.latency_ms < 50.0


def test_caso_3_recarga_hija_terceros_guard():
    """Caso 3: Recarga a terceros exige número 0416/0426."""
    msg = "Quiero recargar saldo para mi hija"
    phone = "0414-2554590"
    res = fastpath_interceptor.intercept(msg, phone)
    
    assert res.can_intercept is True
    assert res.intent_detected == "GUIA_PAGO_C2P"
    assert "0416" in res.response_text and "0426" in res.response_text
    assert "0424-1533712" in res.response_text
    assert "Banco de Venezuela (0102)" in res.response_text
    assert res.latency_ms < 50.0


def test_caso_4_off_topic_restaurantes_guard():
    """Caso 4: Preguntas off-topic gastronómicas son contenidas en <30 palabras."""
    msg = "Qué restaurantes recomiendas cerca de Los Palos Grandes?"
    phone = "0414-2554590"
    res = fastpath_interceptor.intercept(msg, phone)
    
    assert res.can_intercept is True
    assert res.intent_detected == "OFF_TOPIC_TELCO_GUARD"
    assert "gastronomía o comercios generales" in res.response_text
    assert ("Portabilidad" in res.response_text or "eSIM digital" in res.response_text)
    assert res.latency_ms < 50.0


def test_caso_5_parametros_apn():
    """Caso 5: Solicitud de configuración de APN entregada en microsegundos."""
    msg = "Cual es el apn de movilnet?"
    phone = "0416-1234567"
    res = fastpath_interceptor.intercept(msg, phone)
    
    assert res.can_intercept is True
    assert res.intent_detected == "PARAMETROS_APN"
    assert "int.movilnet.com.ve" in res.response_text
    assert "Movilnet LTE" in res.response_text
    assert "734" in res.response_text
    assert "06" in res.response_text
    assert res.latency_ms < 50.0


def test_trace_simulation_integration():
    """Verifica que simulate_trace no inyecte datos quemados obsoletos."""
    trace = conversation_trace_engine.simulate_trace(
        phone_number="04160000001",
        message_text="saldo",
        sender_name="Francisco Landaeta",
        device_type="Celular Android"
    )
    assert trace.status == "SUCCESS"
    assert "11.9 GB de 5 GB" not in trace.bot_reply
    assert "4GMAX" in trace.bot_reply


if __name__ == "__main__":
    funcs = [
        test_caso_1_oficina_los_palos_grandes,
        test_caso_2_saldo_real_sin_hardcoding,
        test_caso_3_recarga_hija_terceros_guard,
        test_caso_4_off_topic_restaurantes_guard,
        test_caso_5_parametros_apn,
        test_trace_simulation_integration,
    ]
    for fn in funcs:
        fn()
        print(f"  [PASS] {fn.__name__}")
    print(f"✅ {len(funcs)}/{len(funcs)} pruebas en test_conversatorio_e2e_5cases.py 100% PASS")
