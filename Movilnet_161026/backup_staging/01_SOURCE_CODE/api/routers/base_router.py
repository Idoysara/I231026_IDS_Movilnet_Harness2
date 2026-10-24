#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
base_router.py — Protocolo Base y Utilidades para Routers de Dominio
=============================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
Define el contrato abstracto BaseDomainRouter, tipos invariantes y helpers
canónicos para serialización JSON, validación defensiva y cabeceras CORS.
"""

from __future__ import annotations

import argparse
import json
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

# Tipo estándar de respuesta HTTP en Movilnet Core
RouteResult = Tuple[int, Dict[str, str], bytes]


def cors_headers(content_type: str = "application/json; charset=utf-8") -> Dict[str, str]:
    """Retorna conjunto canónico de cabeceras CORS y seguridad militar para APIs Movilnet."""
    return {
        "Content-Type": content_type,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, post-check=0, pre-check=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }


def json_response(
    status: int,
    data: Any,
    extra_headers: Optional[Dict[str, str]] = None
) -> RouteResult:
    """Serializa un objeto Python a JSON estructurado con cabeceras estándar."""
    headers = cors_headers("application/json; charset=utf-8")
    if extra_headers:
        headers.update(extra_headers)

    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return status, headers, payload


def error_response(
    status: int,
    code: str,
    message: str,
    details: Optional[Any] = None,
    extra_headers: Optional[Dict[str, str]] = None
) -> RouteResult:
    """Genera una respuesta de error estandarizada TM Forum ODA."""
    body: Dict[str, Any] = {
        "code": code,
        "message": message,
        "status": status
    }
    if details is not None:
        body["details"] = details
    return json_response(status, body, extra_headers=extra_headers)


def parse_json_body(body_bytes: bytes) -> Tuple[bool, Any, Optional[str]]:
    """
    Parsea de forma segura el cuerpo recibido.
    Retorna: (éxito, objeto_parseado_o_none, mensaje_error_o_none).
    """
    if not body_bytes:
        return False, None, "Cuerpo de solicitud vacío"
    try:
        data = json.loads(body_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            return False, None, "El payload JSON debe ser un objeto"
        return True, data, None
    except UnicodeDecodeError:
        return False, None, "Codificación no válida (se requiere UTF-8)"
    except json.JSONDecodeError as exc:
        return False, None, f"JSON malformado: {str(exc)}"


class BaseDomainRouter(ABC):
    """Contrato base abstracto para todos los routers de dominio en api/routers/."""

    @abstractmethod
    def match(self, method: str, clean_path: str) -> bool:
        """Determina en O(1) si esta ruta y verbo HTTP pertenecen al dominio."""
        raise NotImplementedError

    @abstractmethod
    def handle(
        self,
        method: str,
        path: str,
        clean_path: str,
        headers: Dict[str, str],
        body_bytes: bytes,
        service: Any
    ) -> RouteResult:
        """Procesa la petición y retorna una tupla (status_code, headers, body_bytes)."""
        raise NotImplementedError


# ============================================================================
# CLI DE AUTO-VERIFICACIÓN
# ============================================================================

def run_self_tests() -> int:
    """Ejecuta suite de pruebas unitarias para helpers del base_router."""
    print("🧪 Verificando base_router.py...")

    # 1. cors_headers
    h = cors_headers()
    assert h["Access-Control-Allow-Origin"] == "*"
    assert "application/json" in h["Content-Type"]

    # 2. json_response
    status, hdrs, body = json_response(200, {"ok": True, "servicio": "MOVILNET"})
    assert status == 200
    assert json.loads(body.decode("utf-8"))["ok"] is True

    # 3. error_response
    status, _, body = error_response(400, "ERR_INVALID", "Dato incorrecto")
    assert status == 400
    assert b"ERR_INVALID" in body

    # 4. parse_json_body válido
    ok, data, err = parse_json_body(b'{"canal": "4GMAX"}')
    assert ok is True and data["canal"] == "4GMAX" and err is None

    # 5. parse_json_body inválido
    ok, data, err = parse_json_body(b'{invalido')
    assert ok is False and data is None and "JSON malformado" in err

    # 6. parse_json_body vacío
    ok, data, err = parse_json_body(b'')
    assert ok is False and "vacío" in err

    print("✅ [TEST PASS] base_router: 6/6 pruebas aprobadas (100%).")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Base Domain Router Protocol")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación")
    args = parser.parse_args()

    if args.test:
        sys.exit(run_self_tests())
    else:
        print("Uso: python3 -m api.routers.base_router --test")


if __name__ == "__main__":
    main()
