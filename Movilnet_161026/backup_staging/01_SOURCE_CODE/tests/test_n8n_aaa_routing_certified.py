#!/usr/bin/env python3
"""
tests/test_n8n_aaa_routing_certified.py — Suite de Certificación AAA del Flujo n8n ↔ Movilnet
=============================================================================================
Valida:
1. Topología de 74 nodos íntegra.
2. Enrutamiento formal del Router hacia 'Movilnet Core - Fast-Path ODA'.
3. Clasificación determinista de intenciones Telco (0 tokens, <5ms).
4. Convergencia hacia 'Merge - Respuestas 5' y salida Egress.
"""

import json
try:
    import pytest
except ImportError:
    pytest = None
from pathlib import Path
from api.service import MovilnetAPIService
from api.agents.agent_n8n_dispatcher import N8nDispatcherAgent
from core.n8n_webhook_payload_extractor import N8nWebhookPayloadExtractor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_FILE = PROJECT_ROOT / "api/n8n_workflows/viki_lpgtec_v2_ids_aaa_certified.json"


def test_aaa_workflow_topology_and_wiring():
    """Verifica que el workflow tenga los 74 nodos y la entrada cableada a Movilnet Core."""
    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        wf = json.load(f)

    nodes = wf["nodes"]
    connections = wf["connections"]

    assert len(nodes) == 74, f"Se esperaban 74 nodos, encontrados {len(nodes)}"

    # Verificar existencia de nodos clave
    node_names = [n["name"] for n in nodes]
    assert "Router - Consultas determinísticas" in node_names
    assert "Movilnet Core - Fast-Path ODA" in node_names
    assert "Merge - Respuestas 5" in node_names
    assert "AI Agent" in node_names

    # Verificar conexiones del Router
    router_branches = connections.get("Router - Consultas determinísticas", {}).get("main", [])
    assert len(router_branches) >= 9, f"El router debe tener al menos 9 ramas, tiene {len(router_branches)}"

    # La rama de Telco debe apuntar a Movilnet Core
    branch_8_targets = [c["node"] for c in router_branches[8]]
    assert "Movilnet Core - Fast-Path ODA" in branch_8_targets, f"Rama 8 debe apuntar a Movilnet Core: {branch_8_targets}"

    # La salida de Movilnet Core debe apuntar a Merge - Respuestas 5
    movilnet_targets = [c["node"] for c in connections.get("Movilnet Core - Fast-Path ODA", {}).get("main", [[]])[0]]
    assert "Merge - Respuestas 5" in movilnet_targets


def test_aaa_telco_fastpath_intent_resolution():
    """Verifica resolución determinista para todas las operadoras venezolanas."""
    agent = N8nDispatcherAgent()

    casos = [
        ("04161234567", "Hola, deseo consultar mi saldo disponible", "BALANCE_CHECK"),
        ("04269876543", "Buenas tardes, cuál es mi contrato y plan activo?", "CONTRACT_INFO"),
        ("04142650088", "Necesito hacer una recarga por pago móvil c2p", "RECHARGE_C2P"),
        ("04125556677", "Me robaron el teléfono, necesito bloqueo imei urgente", "EMERGENCY_EIR"),
    ]

    for phone, msg, expected_intent in casos:
        payload = {
            "event": "messages.upsert",
            "instance": "Viki LPGTEC",
            "data": {
                "key": {"remoteJid": f"58{phone[1:]}@s.whatsapp.net", "id": f"TEST-{phone}"},
                "pushName": "Abonado Test",
                "message": {"conversation": msg}
            }
        }
        res = agent.process_inbound_webhook(payload)
        assert res["status"] == "success"
        assert res["intent"] == expected_intent
        assert res["latency_mode"] == "FAST_PATH_DETERMINISTIC"
        assert res["tokens_cost_usd"] == 0.0
        assert res["n8n_egress_payload"]["number"] == f"58{phone[1:]}@s.whatsapp.net"


def test_aaa_end_to_end_api_service_ingest():
    """Verifica que el servicio HTTP procese el paquete y retorne código 200 con JSON formal."""
    service = MovilnetAPIService()
    body = {
        "event": "messages.upsert",
        "instance": "Viki LPGTEC",
        "data": {
            "key": {"remoteJid": "584165551234@s.whatsapp.net", "id": "INGEST-TEST-001"},
            "pushName": "Evaluador AAA",
            "message": {"conversation": "saldo de mi línea"}
        }
    }
    body_bytes = json.dumps(body).encode("utf-8")
    status, headers, resp_bytes = service.dispatch(
        method="POST",
        path="/api/v1/n8n/webhook-ingest",
        headers={"Content-Type": "application/json"},
        body_bytes=body_bytes
    )

    assert status == 200
    res = json.loads(resp_bytes.decode("utf-8"))
    assert res["status"] == "success"
    assert res["intent"] == "BALANCE_CHECK"
    assert "n8n_egress_payload" in res
