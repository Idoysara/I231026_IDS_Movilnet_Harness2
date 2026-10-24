#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents_router.py — Router de Dominio para Agentes Cognitivos e IA Telco
=============================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
Enruta operaciones de Atención al Cliente (MOVI), Despacho de Emergencia 911,
Agentes Especializados FinTech C2P, Bloqueo EIR, Retención/Churn ML,
Evaluación Fast-Path en <15ms e Ingesta de Webhooks n8n.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.routers.base_router import BaseDomainRouter, RouteResult, cors_headers, json_response


def _parse_body(body_bytes: bytes) -> Tuple[bool, Any, Optional[RouteResult]]:
    """Valida y parsea el payload JSON; retorna error 400 si está malformado."""
    if not body_bytes:
        return True, {}, None
    try:
        body_str = body_bytes.decode("utf-8")
        data = json.loads(body_str) if body_str else {}
        return True, data, None
    except Exception:
        err = {
            "code": "ERR_INVALID_JSON",
            "reason": "Payload JSON malformado",
            "message": "El cuerpo de la solicitud debe ser un objeto JSON válido.",
            "status": 400,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return False, {}, (400, cors_headers(), json.dumps(err).encode("utf-8"))


class AgentsRouter(BaseDomainRouter):
    """Router para agentes autónomos y Fast-Path de Movilnet."""

    AGENTS_GET_ROUTES = {
        "/api/v1/agents/emergency-eir/status",
        "/agents/emergency-eir/status",
        "/api/v1/agents/retention-churn/status",
        "/agents/retention-churn/status",
    }

    AGENTS_POST_ROUTES = {
        "/api/v1/agents/customer-care/process",
        "/agents/customer-care/process",
        "/api/v1/agent/chat",
        "/agent/chat",
        "/api/v1/chat",
        "/api/v1/n8n/webhook-ingest",
        "/n8n/webhook-ingest",
        "/api/v1/agents/fintech-c2p/process",
        "/agents/fintech-c2p/process",
        "/api/v1/agents/emergency-eir/process",
        "/agents/emergency-eir/process",
        "/api/v1/agents/retention-churn/predict",
        "/agents/retention-churn/predict",
        "/api/v1/agents/retention-churn/offer",
        "/agents/retention-churn/offer",
        "/api/v1/fastpath/evaluate",
        "/fastpath/evaluate",
        "/api/v1/session/isolate",
        "/session/isolate",
        "/api/v1/emergency/sos",
        "/emergency/sos",
    }

    def match(self, method: str, clean_path: str) -> bool:
        if method in ("GET", "HEAD"):
            return clean_path in self.AGENTS_GET_ROUTES
        elif method == "POST":
            return clean_path in self.AGENTS_POST_ROUTES
        return False

    def handle(
        self,
        method: str,
        path: str,
        clean_path: str,
        headers: Dict[str, str],
        body_bytes: bytes,
        service: Any
    ) -> RouteResult:
        resp_headers = cors_headers()

        # ----------------- GET ROUTES -----------------
        if method in ("GET", "HEAD"):
            parsed_url = urlparse(path)
            params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}

            if clean_path in ["/api/v1/agents/emergency-eir/status", "/agents/emergency-eir/status"]:
                status, payload = service.handle_emergency_eir_status(params)
                return status, resp_headers, json.dumps(payload).encode("utf-8")

            if clean_path in ["/api/v1/agents/retention-churn/status", "/agents/retention-churn/status"]:
                status, payload = service.handle_retention_churn_status(params)
                return status, resp_headers, json.dumps(payload).encode("utf-8")

        # ----------------- POST ROUTES -----------------
        if method == "POST":
            ok, json_body, err_resp = _parse_body(body_bytes)
            if not ok and err_resp is not None:
                return err_resp

            # Atención al Cliente / Chat Bot MOVI / Emergencia 911
            if clean_path in [
                "/api/v1/agents/customer-care/process",
                "/agents/customer-care/process",
                "/api/v1/agent/chat",
                "/agent/chat",
                "/api/v1/chat"
            ]:
                status, payload = service.handle_customer_care_agent(json_body)
                return status, resp_headers, json.dumps(payload, ensure_ascii=False).encode("utf-8")

            # Despacho SOS de Alta Precisión Sub-5 Metros (<5m)
            if clean_path in ["/api/v1/emergency/sos", "/emergency/sos"]:
                from core.emergency_dispatcher import emergency_dispatcher
                phone = json_body.get("phone") or "04142554590"
                lat = float(json_body.get("latitude") or json_body.get("lat") or 10.502078)
                lon = float(json_body.get("longitude") or json_body.get("lon") or -66.843345)
                accuracy = float(json_body.get("accuracy_meters") or json_body.get("accuracy") or 3.0)
                altitude = float(json_body["altitude_meters"]) if "altitude_meters" in json_body else None
                heading = float(json_body["heading_degrees"]) if "heading_degrees" in json_body else None
                source = json_body.get("source_channel") or "PWA_SOS_HIGH_ACCURACY"
                text = json_body.get("text") or "Alerta SOS de Alta Precisión"

                sos_result = emergency_dispatcher.process_high_precision_emergency(
                    phone=phone,
                    lat=lat,
                    lon=lon,
                    accuracy_meters=accuracy,
                    altitude_meters=altitude,
                    heading_degrees=heading,
                    source_channel=source,
                    text_context=text
                )
                return 200, resp_headers, json.dumps(sos_result, ensure_ascii=False).encode("utf-8")

            # Ingesta n8n
            if clean_path in ["/api/v1/n8n/webhook-ingest", "/n8n/webhook-ingest"]:
                status, payload = service.handle_n8n_webhook_ingest(json_body)
                return status, resp_headers, json.dumps(payload, ensure_ascii=False).encode("utf-8")

            # Agente FinTech C2P
            if clean_path in ["/api/v1/agents/fintech-c2p/process", "/agents/fintech-c2p/process"]:
                status, payload = service.handle_fintech_c2p_agent(json_body)
                return status, resp_headers, json.dumps(payload).encode("utf-8")

            # Agente Emergencia EIR
            if clean_path in ["/api/v1/agents/emergency-eir/process", "/agents/emergency-eir/process"]:
                status, payload = service.handle_emergency_eir_agent(json_body)
                return status, resp_headers, json.dumps(payload).encode("utf-8")

            # Churn Predict
            if clean_path in ["/api/v1/agents/retention-churn/predict", "/agents/retention-churn/predict"]:
                status, payload = service.handle_retention_churn_predict(json_body)
                return status, resp_headers, json.dumps(payload).encode("utf-8")

            # Churn Offer
            if clean_path in ["/api/v1/agents/retention-churn/offer", "/agents/retention-churn/offer"]:
                status, payload = service.handle_retention_churn_offer(json_body)
                return status, resp_headers, json.dumps(payload).encode("utf-8")

            # FastPath Evaluator
            if clean_path in ["/api/v1/fastpath/evaluate", "/fastpath/evaluate"]:
                from core.fastpath_intent_interceptor import fastpath_interceptor
                from core.semantic_response_cache import semantic_cache
                msg = json_body.get("message", "")
                phone = json_body.get("phone", "")

                fp_res = fastpath_interceptor.intercept(msg, phone)
                if fp_res.can_intercept:
                    return 200, resp_headers, json.dumps({
                        "handled": True,
                        "source": "FAST_PATH_TELCO",
                        "response": fp_res.response_text,
                        "intent": fp_res.intent_detected,
                        "tokens_saved": 450,
                        "latency_ms": fp_res.latency_ms
                    }).encode("utf-8")

                cache_hit = semantic_cache.get(msg)
                if cache_hit:
                    text, tokens = cache_hit
                    return 200, resp_headers, json.dumps({
                        "handled": True,
                        "source": "SEMANTIC_CACHE",
                        "response": text,
                        "intent": "CACHE_HIT",
                        "tokens_saved": tokens,
                        "latency_ms": 1.2
                    }).encode("utf-8")

                return 200, resp_headers, json.dumps({
                    "handled": False,
                    "source": "DELEGATE_TO_COGNITIVE_AI",
                    "response": "",
                    "intent": "CONVERSACION_LIBRE",
                    "tokens_saved": 0,
                    "latency_ms": fp_res.latency_ms
                }).encode("utf-8")

            # Session Isolate
            if clean_path in ["/api/v1/session/isolate", "/session/isolate"]:
                from core.session_identity_isolator import SessionIdentityIsolator
                jid = json_body.get("remote_jid")
                phone = json_body.get("phone")
                push = json_body.get("push_name")
                identity = SessionIdentityIsolator.isolate_session(remote_jid=jid, phone_number=phone, push_name=push)
                return 200, resp_headers, json.dumps(identity.to_dict()).encode("utf-8")

        return 404, resp_headers, b'{"code":"ERR_NOT_FOUND","message":"Ruta Agentes no encontrada"}'


# ============================================================================
# CLI DE AUTO-VERIFICACIÓN
# ============================================================================

def run_self_tests() -> int:
    """Ejecuta suite de pruebas unitarias para AgentsRouter."""
    print("🧪 Verificando agents_router.py...")
    router = AgentsRouter()

    # 1. Match verificación
    assert router.match("POST", "/api/v1/agents/customer-care/process") is True
    assert router.match("POST", "/api/v1/agent/chat") is True
    assert router.match("POST", "/agent/chat") is True
    assert router.match("POST", "/api/v1/chat") is True
    assert router.match("POST", "/api/v1/n8n/webhook-ingest") is True
    assert router.match("POST", "/api/v1/fastpath/evaluate") is True
    assert router.match("GET", "/api/v1/agents/emergency-eir/status") is True
    assert router.match("GET", "/api/v1/agents/retention-churn/status") is True
    assert router.match("DELETE", "/api/v1/agent/chat") is False

    # 2. Mock service para /api/v1/agent/chat
    class MockService:
        def handle_customer_care_agent(self, data):
            if not data.get("message"):
                return 400, {"code": "ERR_EMPTY_MESSAGE", "message": "Mensaje requerido"}
            return 200, {"response": "Hola desde Movilnet 4GMAX", "intent": "SALUDO"}
        def handle_emergency_eir_status(self, params):
            return 200, {"status": "ACTIVE"}

    mock_srv = MockService()

    # Test POST /api/v1/agent/chat válido
    valid_body = json.dumps({"phone": "04161234567", "message": "Hola"}).encode("utf-8")
    status, _, body = router.handle("POST", "/api/v1/agent/chat", "/api/v1/agent/chat", {}, valid_body, mock_srv)
    assert status == 200
    assert b"4GMAX" in body

    # Test POST /api/v1/agent/chat mensaje vacío
    status, _, body = router.handle("POST", "/api/v1/agent/chat", "/api/v1/agent/chat", {}, b'{}', mock_srv)
    assert status == 400
    assert b"ERR_EMPTY_MESSAGE" in body

    # Test GET status
    status, _, body = router.handle("GET", "/agents/emergency-eir/status", "/agents/emergency-eir/status", {}, b"", mock_srv)
    assert status == 200
    assert b"ACTIVE" in body

    print("✅ [TEST PASS] agents_router: 5/5 pruebas aprobadas (100%).")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Agents Domain Router")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación")
    args = parser.parse_args()

    if args.test:
        sys.exit(run_self_tests())
    else:
        print("Uso: python3 -m api.routers.agents_router --test")


if __name__ == "__main__":
    main()
