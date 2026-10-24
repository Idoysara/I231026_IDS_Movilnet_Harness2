#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fintech_router.py — Router de Dominio FinTech (TMF676: Pasarela Pago Móvil C2P)
=============================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
Enruta operaciones de procesamiento y conciliación de Pago Móvil Interbancario
C2P homologado bajo normativas SUDEBAN y TM Forum Open API TMF676.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

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


class FintechRouter(BaseDomainRouter):
    """Router para operaciones de pagos e integración bancaria C2P (TMF676)."""

    FINTECH_ROUTES = {
        "/api/v1/payments/c2p",
        "/payments/c2p",
    }

    def match(self, method: str, clean_path: str) -> bool:
        return method == "POST" and clean_path in self.FINTECH_ROUTES

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
        ok, json_body, err_resp = _parse_body(body_bytes)
        if not ok and err_resp is not None:
            return err_resp

        status, payload = service.handle_c2p_payment(json_body)
        return status, resp_headers, json.dumps(payload).encode("utf-8")


# ============================================================================
# CLI DE AUTO-VERIFICACIÓN
# ============================================================================

def run_self_tests() -> int:
    """Ejecuta suite de pruebas unitarias para FintechRouter."""
    print("🧪 Verificando fintech_router.py...")
    router = FintechRouter()

    # 1. Match verificación
    assert router.match("POST", "/api/v1/payments/c2p") is True
    assert router.match("POST", "/payments/c2p") is True
    assert router.match("GET", "/api/v1/payments/c2p") is False

    # 2. Mock service para /api/v1/payments/c2p
    class MockService:
        def handle_c2p_payment(self, data):
            if not data.get("amount"):
                return 400, {"code": "ERR_INVALID_PARAM", "message": "Monto requerido"}
            return 200, {"status": "APPROVED", "reference": "REC-9988"}

    mock_srv = MockService()

    # Petición válida
    valid_body = json.dumps({"phone": "04161234567", "amount": 100.0, "bank": "0102"}).encode("utf-8")
    status, _, body = router.handle("POST", "/api/v1/payments/c2p", "/api/v1/payments/c2p", {}, valid_body, mock_srv)
    assert status == 200
    assert b"APPROVED" in body

    # Petición con parámetro faltante
    status, _, body = router.handle("POST", "/api/v1/payments/c2p", "/api/v1/payments/c2p", {}, b'{}', mock_srv)
    assert status == 400
    assert b"ERR_INVALID_PARAM" in body

    # Petición JSON inválido
    status, _, body = router.handle("POST", "/api/v1/payments/c2p", "/api/v1/payments/c2p", {}, b'{malo', mock_srv)
    assert status == 400
    assert b"ERR_INVALID_JSON" in body

    print("✅ [TEST PASS] fintech_router: 4/4 pruebas aprobadas (100%).")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Fintech Domain Router")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación")
    args = parser.parse_args()

    if args.test:
        sys.exit(run_self_tests())
    else:
        print("Uso: python3 -m api.routers.fintech_router --test")


if __name__ == "__main__":
    main()
