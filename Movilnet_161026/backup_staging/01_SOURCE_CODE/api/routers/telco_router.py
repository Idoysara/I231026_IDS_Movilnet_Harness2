#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
telco_router.py — Router de Dominio Telco (TMF678, TMF620, TMF680)
=============================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
Enruta operaciones de consulta de saldo y cuotas O(1), catálogo comercial de
planes 4GMAX, entidades bancarias SUDEBAN, auditoría SIM-Swap y listas EIR.
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
            "reason": "JSON mal formado",
            "message": "El cuerpo de la petición no contiene una estructura JSON válida.",
            "status": 400,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return False, {}, (400, cors_headers(), json.dumps(err).encode("utf-8"))


class TelcoRouter(BaseDomainRouter):
    """Router para operaciones telco TMF678, TMF620 y TMF680."""

    TELCO_GET_ROUTES = {
        "/api/v1/catalog/plans",
        "/banks",
        "/api/v1/banks",
        "/api/v1/security/sim-swap",
        "/security/sim-swap",
    }

    TELCO_POST_ROUTES = {
        "/api/v1/subscribers/balance",
        "/api/v1/security/sim-swap",
        "/security/sim-swap",
        "/api/v1/security/eir-lock",
        "/security/eir-lock",
    }

    def match(self, method: str, clean_path: str) -> bool:
        if method in ("GET", "HEAD"):
            if clean_path in self.TELCO_GET_ROUTES:
                return True
            if clean_path.startswith("/api/v1/catalog/plans/"):
                return True
        elif method == "POST":
            if clean_path in self.TELCO_POST_ROUTES:
                return True
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
            # Catálogo de planes
            if clean_path == "/api/v1/catalog/plans":
                status, payload = service.handle_get_plans()
                return status, resp_headers, json.dumps(payload).encode("utf-8")

            # Plan específico por ID
            if clean_path.startswith("/api/v1/catalog/plans/"):
                plan_id = clean_path.split("/")[-1]
                status, payload = service.handle_get_plan_by_id(plan_id)
                return status, resp_headers, json.dumps(payload).encode("utf-8")

            # Lista de bancos SUDEBAN
            if clean_path in ["/banks", "/api/v1/banks"]:
                status, payload = service.handle_get_banks()
                return status, resp_headers, json.dumps(payload).encode("utf-8")

            # Consulta SIM Swap por GET
            if clean_path in ["/api/v1/security/sim-swap", "/security/sim-swap"]:
                parsed_url = urlparse(path)
                q_phone = parse_qs(parsed_url.query).get("phone", [None])[0] or parse_qs(parsed_url.query).get("msisdn", ["04160000001"])[0]
                status, payload = service.handle_sim_swap_audit({"msisdn": q_phone})
                return status, resp_headers, json.dumps(payload).encode("utf-8")

        # ----------------- POST ROUTES -----------------
        if method == "POST":
            ok, json_body, err_resp = _parse_body(body_bytes)
            if not ok and err_resp is not None:
                return err_resp

            # Consulta de saldo OCS (TMF678)
            if clean_path == "/api/v1/subscribers/balance":
                status, payload = service.handle_subscriber_balance(json_body)
                return status, resp_headers, json.dumps(payload).encode("utf-8")

            # Auditoría SIM Swap (TMF680)
            if clean_path in ["/api/v1/security/sim-swap", "/security/sim-swap"]:
                status, payload = service.handle_sim_swap_audit(json_body)
                return status, resp_headers, json.dumps(payload).encode("utf-8")

            # Bloqueo EIR en lista negra (TMF680)
            if clean_path in ["/api/v1/security/eir-lock", "/security/eir-lock"]:
                status, payload = service.handle_eir_lock(json_body)
                return status, resp_headers, json.dumps(payload).encode("utf-8")

        return 404, resp_headers, b'{"code":"ERR_NOT_FOUND","message":"Ruta Telco no encontrada"}'


# ============================================================================
# CLI DE AUTO-VERIFICACIÓN
# ============================================================================

def run_self_tests() -> int:
    """Ejecuta suite de pruebas unitarias para TelcoRouter."""
    print("🧪 Verificando telco_router.py...")
    router = TelcoRouter()

    # 1. Match verificación
    assert router.match("GET", "/api/v1/catalog/plans") is True
    assert router.match("GET", "/api/v1/catalog/plans/PLAN_4GMAX") is True
    assert router.match("GET", "/api/v1/banks") is True
    assert router.match("POST", "/api/v1/subscribers/balance") is True
    assert router.match("POST", "/api/v1/security/sim-swap") is True
    assert router.match("POST", "/api/v1/security/eir-lock") is True
    assert router.match("DELETE", "/api/v1/subscribers/balance") is False

    # 2. Despacho mock service
    class MockService:
        def handle_get_plans(self):
            return 200, {"plans": [{"id": "P1"}]}
        def handle_get_plan_by_id(self, pid):
            return 200, {"id": pid}
        def handle_get_banks(self):
            return 200, {"banks": []}
        def handle_subscriber_balance(self, data):
            return 200, {"balance": 150.0}
        def handle_sim_swap_audit(self, data):
            return 200, {"sim_swap": False}
        def handle_eir_lock(self, data):
            return 200, {"locked": True}

    mock_srv = MockService()

    # GET plans
    status, _, body = router.handle("GET", "/api/v1/catalog/plans", "/api/v1/catalog/plans", {}, b"", mock_srv)
    assert status == 200
    assert b"P1" in body

    # POST balance válido
    status, _, body = router.handle("POST", "/api/v1/subscribers/balance", "/api/v1/subscribers/balance", {}, b'{"msisdn":"04161234567"}', mock_srv)
    assert status == 200
    assert b"150.0" in body

    # POST balance JSON inválido
    status, _, body = router.handle("POST", "/api/v1/subscribers/balance", "/api/v1/subscribers/balance", {}, b'{bad_json', mock_srv)
    assert status == 400
    assert b"ERR_INVALID_JSON" in body

    print("✅ [TEST PASS] telco_router: 5/5 pruebas aprobadas (100%).")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Telco Domain Router")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación")
    args = parser.parse_args()

    if args.test:
        sys.exit(run_self_tests())
    else:
        print("Uso: python3 -m api.routers.telco_router --test")


if __name__ == "__main__":
    main()
