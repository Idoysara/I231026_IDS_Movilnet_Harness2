#!/usr/bin/env python3
"""
test_n8n_full_cycle.py — Suite de Pruebas Unitarias e Integración para el Ciclo Completo
=======================================================================================
Valida el ciclo:
Movilnet (Abonado) ↔ Input (n8n) ↔ Nodos (n8n) ↔ Output (n8n) ↔ Movilnet
"""

import json
try:
    import pytest
except ImportError:
    pytest = None
from api.service import MovilnetAPIService
from api.agents.agent_n8n_dispatcher import N8nDispatcherAgent
from scripts.inject_movilnet_node_into_n8n import inject_movilnet_integration


def test_api_service_n8n_webhook_ingest_success():
    """Valida el endpoint HTTP POST /api/v1/n8n/webhook-ingest en el Core de Movilnet."""
    service = MovilnetAPIService()
    payload = {
        "event": "messages.upsert",
        "instance": "Viki LPGTEC",
        "data": {
            "key": {
                "remoteJid": "584142650088@s.whatsapp.net",
                "id": "MSG-E2E-TEST-001"
            },
            "pushName": "Francisco Landaeta",
            "message": {
                "conversation": "Saludo informa contrato"
            }
        }
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    status, headers, resp_body = service.dispatch(
        method="POST",
        path="/api/v1/n8n/webhook-ingest",
        headers={"Content-Type": "application/json"},
        body_bytes=body_bytes
    )

    assert status == 200
    res = json.loads(resp_body.decode("utf-8"))
    assert res["status"] == "success"
    assert res["phone"] == "04142650088"
    assert res["intent"] == "CONTRACT_INFO"
    assert "Inteliplan 10GB 4GMAX" in res["reply_text"]
    assert res["n8n_egress_payload"]["number"] == "584142650088@s.whatsapp.net"
    assert res["n8n_egress_payload"]["instanceId"] == "Viki LPGTEC"


def test_api_service_n8n_webhook_ingest_invalid_payload():
    """Valida que un payload sin teléfono retorne HTTP 400 Bad Request."""
    service = MovilnetAPIService()
    payload = {"invalid": "sin datos"}
    body_bytes = json.dumps(payload).encode("utf-8")
    status, headers, resp_body = service.dispatch(
        method="POST",
        path="/api/v1/n8n/webhook-ingest",
        headers={"Content-Type": "application/json"},
        body_bytes=body_bytes
    )

    assert status == 400
    res = json.loads(resp_body.decode("utf-8"))
    assert res["status"] == "error" or res.get("code") == "ERR_INVALID_PAYLOAD"


def test_dispatcher_agent_balance_check():
    """Valida el subagente despachador ante consulta de saldo."""
    agent = N8nDispatcherAgent()
    payload = {
        "phone": "04142650088",
        "message": "Hola, ¿cuánto debo de saldo y cuántos megas me quedan?"
    }
    res = agent.process_inbound_webhook(payload)
    assert res["status"] == "success"
    assert res["intent"] == "BALANCE_CHECK"
    assert "04142650088" in res["reply_text"]


def test_n8n_canvas_injection_integrity():
    """Valida que la inyección del nodo en n8n genere el archivo con 67 nodos y conexión a Merge."""
    res = inject_movilnet_integration()
    assert res["status"] == "success"
    assert res["total_nodes"] >= 67

    with open(res["output_file"], "r", encoding="utf-8") as f:
        wf = json.load(f)

    node_names = [n["name"] for n in wf["nodes"]]
    assert "Movilnet Core - Fast-Path ODA" in node_names
    assert "Merge - Respuestas 5" in str(wf["connections"])


def test_n8n_google_suite_injection_integrity():
    """Valida la inyección del ecosistema Google (Gmail, Drive, Calendar) totalizando 74 nodos."""
    from scripts.inject_google_suite_into_n8n import inject_google_suite
    res = inject_google_suite()
    assert res["status"] == "success"
    assert res["total_nodes"] >= 74
    assert res["injected_google_nodes"] == 7

    with open(res["output_file"], "r", encoding="utf-8") as f:
        wf = json.load(f)

    node_names = [n["name"] for n in wf["nodes"]]
    assert "Gmail - Enviar Factura Digital" in node_names
    assert "Google Drive - Respaldar Contrato" in node_names
    assert "Google Calendar - Agendar Cita Agencia" in node_names
    assert "Enrutador Servicios Google & Notificaciones" in node_names
    assert "Respuesta - Confirmación Despacho Google" in node_names
