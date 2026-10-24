#!/usr/bin/env python3
"""
tests/test_n8n_payload_extractor.py — Suite de Pruebas Unitarias para Extractor n8n
===================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilar V — 100% Pass)
"""

try:
    import pytest
except ImportError:
    pytest = None
from core.n8n_webhook_payload_extractor import N8nWebhookPayloadExtractor
from scripts.n8n_node_inspector import N8nNodeInspector


def test_evolution_api_extraction():
    """Valida la extracción del payload real de Evolution API (Francisco Landaeta)."""
    payload = {
        "event": "messages.upsert",
        "instance": "VPK-LPGTEC",
        "data": {
            "key": {
                "remoteJid": "584142650088@s.whatsapp.net",
                "fromMe": False,
                "id": "3EB0C338A1278C695F06"
            },
            "pushName": "Francisco Landaeta",
            "message": {
                "conversation": "Saludo informa contrato"
            },
            "source": "ios"
        },
        "date_time": "2024-10-05T15:51:32.022Z"
    }

    result = N8nWebhookPayloadExtractor.extract_universal(payload)
    assert result.phone == "04142650088"
    assert result.sender_name == "Francisco Landaeta"
    assert result.intent == "CONTRACT_INFO"
    assert result.instance_id == "VPK-LPGTEC"
    assert result.source == "ios"
    assert result.message_id == "3EB0C338A1278C695F06"


def test_phone_normalization():
    """Valida la normalización de teléfonos venezolanos en diversos formatos."""
    p1, _ = N8nWebhookPayloadExtractor.normalize_phone("584161234567@s.whatsapp.net")
    assert p1 == "04161234567"

    p2, _ = N8nWebhookPayloadExtractor.normalize_phone("584269876543")
    assert p2 == "04269876543"

    p3, _ = N8nWebhookPayloadExtractor.normalize_phone("04142650088")
    assert p3 == "04142650088"

    p4, _ = N8nWebhookPayloadExtractor.normalize_phone("+58 412 555-1234")
    assert p4 == "04125551234"

    p5, _ = N8nWebhookPayloadExtractor.normalize_phone("00584241329949@s.whatsapp.net")
    assert p5 == "04241329949"


def test_intent_classification():
    """Valida la detección determinista de intenciones Telco."""
    assert N8nWebhookPayloadExtractor.classify_intent("hola quiero ver mi contrato") == "CONTRACT_INFO"
    assert N8nWebhookPayloadExtractor.classify_intent("¿cuanto debo de saldo?") == "BALANCE_CHECK"
    assert N8nWebhookPayloadExtractor.classify_intent("deseo recargar por pago movil c2p") == "RECHARGE_C2P"
    assert N8nWebhookPayloadExtractor.classify_intent("me robaron el telefono, bloquear imei") == "EMERGENCY_EIR"
    assert N8nWebhookPayloadExtractor.classify_intent("buenos dias amigos de movilnet") == "GENERAL_INQUIRY"


def test_node_inspector():
    """Valida la inspección estructural de nodos webhook."""
    dummy_node = {
        "id": "node_wh_001",
        "name": "Webhook",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 2,
        "parameters": {
            "httpMethod": "POST",
            "path": "messages_upsert",
            "responseMode": "Immediately"
        }
    }

    inspected = N8nNodeInspector.inspect_webhook_node(dummy_node, base_url="https://n8n.lpgtec.net")
    assert inspected["parameters"]["path"] == "messages_upsert"
    assert inspected["settings"]["production_url"] == "https://n8n.lpgtec.net/webhook/messages_upsert"
    assert inspected["settings"]["test_url"] == "https://n8n.lpgtec.net/webhook-test/messages_upsert"
    assert "headers" in inspected["output_box_schema"]
    assert "body" in inspected["output_box_schema"]


def test_end_to_end_movilnet_core_execution():
    """Valida la resolución completa en Movilnet Core (Paso 3 del diagrama)."""
    payload = {
        "event": "messages.upsert",
        "instance": "VPK-LPGTEC",
        "data": {
            "key": {"remoteJid": "584142650088@s.whatsapp.net", "id": "3EB0C338A1278C695F06"},
            "pushName": "Francisco Landaeta",
            "message": {"conversation": "Saludo informa contrato"},
            "source": "ios"
        }
    }

    # 1. Normalizar
    normalized = N8nWebhookPayloadExtractor.extract_universal(payload)
    assert normalized.phone == "04142650088"
    assert normalized.intent == "CONTRACT_INFO"

    # 2. Ejecutar en Core Movilnet
    core_response = N8nWebhookPayloadExtractor.execute_in_movilnet_core(normalized)
    assert core_response["status"] == "success"
    assert core_response["phone"] == "04142650088"
    assert core_response["tokens_cost_usd"] == 0.0
    assert "Francisco Landaeta" in core_response["reply_text"]
    assert "Inteliplan 10GB 4GMAX" in core_response["reply_text"]

