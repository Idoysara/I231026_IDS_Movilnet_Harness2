#!/usr/bin/env python3
"""
tests/test_carrier_funnel_classifier.py — Pruebas Unitarias del Clasificador de Operadoras & Funnel
====================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: Regla del 100% Pass)
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
from core.carrier_funnel_classifier import (
    CarrierFunnelClassifier,
    Carrier,
    PipelineRoute
)
from core.webhook_live_feed import WebhookLiveFeedManager


def test_movilnet_subscriber_detection_fastpath():
    """Abonados Movilnet (0416 / 0426) deben enrutarse al Fast-Path Telco ODA sin costo de tokens."""
    res1 = CarrierFunnelClassifier.evaluate_inbound_message("04160000001", "saldo disponible")
    assert res1.carrier == Carrier.MOVILNET
    assert res1.is_competitor is False
    assert res1.pipeline_route == PipelineRoute.FAST_PATH_ODA

    res2 = CarrierFunnelClassifier.evaluate_inbound_message("584261234567@s.whatsapp.net", "cuantos megas me quedan")
    assert res2.carrier == Carrier.MOVILNET
    assert res2.is_competitor is False
    assert res2.pipeline_route == PipelineRoute.FAST_PATH_ODA


def test_movistar_competitor_funnel_trigger():
    """Líneas Movistar (0414 / 0424) deben identificarse como competencia y activar Funnel Marketing."""
    res = CarrierFunnelClassifier.evaluate_inbound_message("584142554590@s.whatsapp.net", "Podemos probar si estas funcionando", sender_name="Ismael")
    assert res.carrier == Carrier.MOVISTAR
    assert res.is_competitor is True
    assert res.pipeline_route == PipelineRoute.FUNNEL_PORTABILITY
    assert "Movistar" in res.funnel_reply_text
    assert "60%" in res.funnel_reply_text


def test_digitel_competitor_funnel_trigger():
    """Líneas Digitel (0412) deben identificarse como competencia y recibir oferta de portabilidad."""
    res = CarrierFunnelClassifier.evaluate_inbound_message("04129998877", "consulta de precios")
    assert res.carrier == Carrier.DIGITEL
    assert res.is_competitor is True
    assert res.pipeline_route == PipelineRoute.FUNNEL_PORTABILITY
    assert "Digitel" in res.funnel_reply_text


def test_portability_intent_conversion_stage():
    """Si el usuario expresa deseo de cambiar de operadora, avanza a etapa BOFU con link de eSIM."""
    res = CarrierFunnelClassifier.evaluate_inbound_message("04142554590", "quiero cambiarme a movilnet con esim")
    assert res.funnel_stage == "BOFU_CONVERSION_PORTABILIDAD"
    assert "portabilidad-express" in res.funnel_reply_text
    assert "10 GB" in res.funnel_reply_text


def test_cantv_fija_trigger():
    """Líneas fijas CANTV y zonales (0212, 0241, 0261) deben identificarse como fijas y orientar a red móvil."""
    res1 = CarrierFunnelClassifier.evaluate_inbound_message("02125551234", "hola información", sender_name="Usuario Caracas")
    assert res1.carrier == Carrier.CANTV_FIJA
    assert res1.is_competitor is True
    assert "fija" in res1.funnel_reply_text

    res2 = CarrierFunnelClassifier.evaluate_inbound_message("02419876543", "consulta", sender_name="Usuario Valencia")
    assert res2.carrier == Carrier.CANTV_FIJA
    assert res2.is_competitor is True


def test_voip_isp_special_services_trigger():
    """Servicios no geográficos y VoIP ISP (0500, 0800) deben identificarse adecuadamente."""
    res_cobro_comp = CarrierFunnelClassifier.evaluate_inbound_message("05001234567", "atencion")
    assert res_cobro_comp.carrier == Carrier.VOIP_ISP_SPECIAL
    assert res_cobro_comp.is_competitor is True

    res_tollfree = CarrierFunnelClassifier.evaluate_inbound_message("08006684563", "contacto")
    assert res_tollfree.carrier == Carrier.VOIP_ISP_SPECIAL
    assert res_tollfree.is_competitor is True


def test_phone_cleaner_e164_variations():
    """Validación exhaustiva de variantes numéricas venezolanas."""
    clean = CarrierFunnelClassifier.clean_msisdn
    assert clean("584142554590@s.whatsapp.net") == "04142554590"
    assert clean("584160000001:1@s.whatsapp.net") == "04160000001"
    assert clean("04121234567") == "04121234567"
    assert clean("4141234567") == "04141234567"
    assert clean("00584241533712") == "04241533712"
    assert clean("00584142554590@s.whatsapp.net") == "04142554590"
    assert clean("00584160000001") == "04160000001"


def test_webhook_live_feed_recording_and_metrics():
    """El gestor de feed debe almacenar eventos concurrentes y calcular KPIs de funnel."""
    mgr = WebhookLiveFeedManager()
    initial_total = len(mgr.events)

    ev = mgr.record_event("04149991122", "quiero portabilidad", sender_name="Lead Movistar", device_type="iPhone iOS")
    assert ev.carrier == "MOVISTAR"
    assert ev.is_competitor is True
    assert "CONVERSION" in ev.funnel_stage

    feed = mgr.get_feed(limit=5)
    assert len(feed) >= 1
    assert feed[0]["phone_number"] == "04149991122"

    metrics = mgr.get_metrics()
    assert metrics["total_inbound_messages"] >= initial_total + 1
    assert metrics["competitors_leads"] >= 1
    assert metrics["server_port"] == 8010


def test_audited_real_subscriber_numbers():
    """Líneas reales de otras operadoras auditadas en la ventana de observación E2E (Capítulo 154)."""
    assert CarrierFunnelClassifier.clean_msisdn("04141241044") == "04141241044"
    assert CarrierFunnelClassifier.clean_msisdn("04123001155") == "04123001155"
    assert CarrierFunnelClassifier.clean_msisdn("04145920871") == "04145920871"


if __name__ == "__main__":
    test_movilnet_subscriber_detection_fastpath()
    test_movistar_competitor_funnel_trigger()
    test_digitel_competitor_funnel_trigger()
    test_portability_intent_conversion_stage()
    test_cantv_fija_trigger()
    test_voip_isp_special_services_trigger()
    test_phone_cleaner_e164_variations()
    test_webhook_live_feed_recording_and_metrics()
    test_audited_real_subscriber_numbers()
    print("✅ [TEST PASS]: Todas las pruebas de test_carrier_funnel_classifier.py aprobadas al 100%.")
