#!/usr/bin/env python3
"""
test_n_to_1_activation_engine.py — Suite de Pruebas Unitarias e Invariantes N -> 1
==================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: Regla del 100% Pass)
"""

try:
    import pytest
except ImportError:
    pytest = None
from pathlib import Path
from scripts.research_n_to_1_activation_engine import (
    NTo1ActivationEngine,
    InboundActivationRequest,
    ActivationChannel,
    PWAActivatorAdapter,
    TelegramActivatorAdapter,
    AndroidSmsGatewayAdapter,
    HeaderEnrichmentAdapter,
    generate_comparative_benchmark_matrix
)


def test_inbound_request_invariants():
    """Valida que solicitudes con identificador vacío sean rechazadas inmediatamente."""
    req = InboundActivationRequest(raw_identifier="", channel=ActivationChannel.PWA_ONE_TAP, message_text="saldo")
    with pytest.raises(ValueError, match="DomainInvariantViolation"):
        req.validate_invariants()


def test_pwa_activation_session_and_fastpath():
    """Valida activación de sesión PWA por número celular en FastPath."""
    engine = NTo1ActivationEngine()
    req = PWAActivatorAdapter.create_inbound_request("04160000001", "saldo")
    res = engine.process_consultation(req)

    assert res.session.canonical_msisdn == "04160000001"
    assert res.session.operator == "MOVILNET"
    assert res.channel == ActivationChannel.PWA_ONE_TAP
    assert res.cost_usd_per_query == 0.00
    assert res.tokens_consumed == 0
    assert res.is_zero_pii_compliant is True
    assert len(res.session.blind_index_hash) == 64


def test_telegram_contact_activation():
    """Valida activación de sesión mediante número celular certificado por Telegram."""
    engine = NTo1ActivationEngine()
    req = TelegramActivatorAdapter.create_inbound_request(
        telegram_user_id=88776655,
        verified_phone="584260000002",
        message="planes"
    )
    res = engine.process_consultation(req)

    assert res.session.canonical_msisdn == "04260000002"
    assert res.session.operator == "MOVILNET"
    assert res.channel == ActivationChannel.TELEGRAM_CONTACT
    assert res.cost_usd_per_query == 0.00


def test_android_sms_gateway_activation():
    """Valida activación por SMS Gateway local autónomo."""
    engine = NTo1ActivationEngine()
    req = AndroidSmsGatewayAdapter.create_inbound_request("04142554590", "recarga c2p")
    res = engine.process_consultation(req)

    assert res.session.canonical_msisdn == "04142554590"
    assert res.session.operator == "MOVISTAR"
    assert res.channel == ActivationChannel.ANDROID_SMS_GATEWAY
    assert res.cost_usd_per_query == 0.00


def test_header_enrichment_activation():
    """Valida activación automática por cabecera de red 4GMAX."""
    engine = NTo1ActivationEngine()
    req = HeaderEnrichmentAdapter.create_inbound_request("584169998877", "saldo")
    res = engine.process_consultation(req)

    assert res.session.canonical_msisdn == "04169998877"
    assert res.channel == ActivationChannel.HEADER_ENRICHMENT
    assert res.cost_usd_per_query == 0.00


def test_n_to_1_concurrent_stress_simulation():
    """Valida concurrencia N -> 1 y ausencia total de fugas o colisiones entre sesiones."""
    engine = NTo1ActivationEngine()
    sim_res = engine.run_concurrent_n_to_1_simulation(n_subscribers=30)

    assert sim_res["successful_resolutions"] == 30
    assert sim_res["exceptions_count"] == 0
    assert sim_res["has_session_leak"] is False
    assert sim_res["total_tokens_consumed"] == 0
    assert sim_res["total_cost_usd"] == 0.00


def test_benchmark_matrix_structure():
    """Valida integridad de la matriz comparativa de canales."""
    matrix = generate_comparative_benchmark_matrix()
    assert matrix["canales_gratuitos_soberanos"] == 4
    assert len(matrix["matriz_comparativa"]) == 5
    assert len(matrix["conclusiones_tecnicas"]) >= 4
