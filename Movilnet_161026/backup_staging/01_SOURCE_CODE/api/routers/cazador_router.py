#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api/routers/cazador_router.py — Router de Dominio para Cazador de Ofertas & Club 4GMAX
====================================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
Gobierna los endpoints REST para exploración por radar de proximidad, emisión
y canje de cupones dinámicos TOTP, y liquidación Carrier Billing con split 20/80.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.routers.base_router import (
    BaseDomainRouter,
    RouteResult,
    cors_headers,
    json_response,
    error_response,
    parse_json_body
)
from services.cazador_ofertas.src.application.cazador_service import CazadorApplicationService
from services.cazador_ofertas.src.infrastructure.deflector.magic_link_service import MagicLinkService
from services.cazador_ofertas.src.domain.zones import listar_zonas_disponibles
from services.cazador_ofertas.src.domain.invariants import (
    CazadorInvariants,
    DomainInvariantViolationError
)
from services.cazador_ofertas.src.domain.fsm import IllegalCouponStateTransitionError


class CazadorRouter(BaseDomainRouter):
    """Router para operaciones de Cazador de Ofertas, Cuponería y Carrier Billing."""

    CAZADOR_ROUTES = {
        "/api/v1/cazador/ofertas",
        "/api/v1/cazador/cupon/reclamar",
        "/api/v1/cazador/cupon/canjear",
        "/api/v1/cazador/magic-link",
        "/api/v1/cazador/billing",
        "/api/v1/cazador/comercio/registro-rapido",
        "/api/v1/cazador/zonas",
    }

    def __init__(self, service: Optional[CazadorApplicationService] = None):
        self.cazador_service = service or CazadorApplicationService()
        self.magic_service = MagicLinkService(service=self.cazador_service)

    def match(self, method: str, clean_path: str) -> bool:
        """Determina si la ruta pertenece al dominio de Cazador de Ofertas."""
        if clean_path in self.CAZADOR_ROUTES:
            return True
        if clean_path.startswith("/api/v1/cazador/cupones/"):
            return method == "GET"
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
        """Enruta y ejecuta la solicitud de Cazador de Ofertas."""
        parsed_url = urllib.parse.urlparse(path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        try:
            # 1. GET /api/v1/cazador/ofertas (Radar Geoespacial)
            if method == "GET" and clean_path == "/api/v1/cazador/ofertas":
                lat_str = query_params.get("lat", [None])[0]
                lon_str = query_params.get("lon", [None])[0]
                if not lat_str or not lon_str:
                    lat = 10.4925
                    lon = -66.8550
                else:
                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                    except ValueError:
                        return error_response(400, "ERR_INVALID_COORDINATES", "Las coordenadas lat y lon deben ser números válidos.")

                max_m = float(query_params.get("max_m", [3000.0])[0])
                categoria = query_params.get("categoria", [None])[0]

                radar_res = self.cazador_service.buscar_ofertas_radar(
                    user_lat=lat,
                    user_lon=lon,
                    max_distancia_m=max_m,
                    categoria=categoria
                )
                return json_response(200, radar_res)

            # 2. POST /api/v1/cazador/cupon/reclamar
            elif method == "POST" and clean_path == "/api/v1/cazador/cupon/reclamar":
                ok, body, err_msg = parse_json_body(body_bytes)
                if not ok:
                    return error_response(400, "ERR_INVALID_JSON", err_msg or "JSON inválido")

                oferta_id = body.get("oferta_id")
                msisdn = body.get("msisdn")
                if not oferta_id or not msisdn:
                    return error_response(400, "ERR_MISSING_FIELDS", "Campos obligatorios: oferta_id y msisdn.")

                res_cupon = self.cazador_service.reclamar_cupon(oferta_id=oferta_id, msisdn=msisdn)
                return json_response(201, res_cupon)

            # 3. POST /api/v1/cazador/cupon/canjear
            elif method == "POST" and clean_path == "/api/v1/cazador/cupon/canjear":
                ok, body, err_msg = parse_json_body(body_bytes)
                if not ok:
                    return error_response(400, "ERR_INVALID_JSON", err_msg or "JSON inválido")

                cupon_id = body.get("cupon_id")
                msisdn = body.get("msisdn")
                comercio_id = body.get("comercio_id")
                firma_hmac = body.get("firma_hmac")

                if not all([cupon_id, msisdn, comercio_id, firma_hmac]):
                    return error_response(
                        400,
                        "ERR_MISSING_FIELDS",
                        "Campos obligatorios: cupon_id, msisdn, comercio_id, firma_hmac."
                    )

                res_canje = self.cazador_service.canjear_cupon(
                    cupon_id=cupon_id,
                    msisdn=msisdn,
                    comercio_id=comercio_id,
                    firma_hmac=firma_hmac
                )
                return json_response(200, res_canje)

            # 4. GET /api/v1/cazador/cupones/{msisdn}
            elif method == "GET" and clean_path.startswith("/api/v1/cazador/cupones/"):
                msisdn = clean_path.replace("/api/v1/cazador/cupones/", "").strip()
                cupones = self.cazador_service.obtener_cupones_usuario(msisdn)
                return json_response(200, {
                    "success": True,
                    "msisdn": msisdn,
                    "total": len(cupones),
                    "cupones": cupones
                })

            # 5. GET /api/v1/cazador/magic-link
            elif method == "GET" and clean_path == "/api/v1/cazador/magic-link":
                msisdn = query_params.get("msisdn", [None])[0]
                if not msisdn:
                    return error_response(400, "ERR_MISSING_MSISDN", "Parámetro msisdn requerido.")
                oferta_id = query_params.get("oferta_id", [None])[0]
                link = self.magic_service.generar_magic_link(msisdn=msisdn, oferta_id=oferta_id)
                return json_response(200, {
                    "success": True,
                    "msisdn": msisdn,
                    "magic_link": link,
                    "zero_rating": True
                })

            # 6. POST /api/v1/cazador/billing
            elif method == "POST" and clean_path == "/api/v1/cazador/billing":
                ok, body, err_msg = parse_json_body(body_bytes)
                if not ok:
                    return error_response(400, "ERR_INVALID_JSON", err_msg or "JSON inválido")

                msisdn = body.get("msisdn")
                monto_ves = body.get("monto_ves")
                idempotency_key = body.get("idempotency_key")

                if not msisdn or monto_ves is None or not idempotency_key:
                    return error_response(
                        400,
                        "ERR_MISSING_FIELDS",
                        "Campos obligatorios: msisdn, monto_ves, idempotency_key."
                    )

                res_bill = self.cazador_service.procesar_carrier_billing(
                    msisdn=msisdn,
                    monto_ves=float(monto_ves),
                    idempotency_key=idempotency_key
                )
                return json_response(200, res_bill)

            # 7. GET /api/v1/cazador/zonas (Catálogo Canónico de Zonas para Cero Fricción)
            elif method == "GET" and clean_path == "/api/v1/cazador/zonas":
                zonas = listar_zonas_disponibles()
                return json_response(200, {
                    "success": True,
                    "total": len(zonas),
                    "zonas": zonas
                })

            # 8. POST /api/v1/cazador/comercio/registro-rapido (Modelo 3 Escenarios Cero Fricción)
            elif method == "POST" and clean_path == "/api/v1/cazador/comercio/registro-rapido":
                ok, body, err_msg = parse_json_body(body_bytes)
                if not ok:
                    return error_response(400, "ERR_INVALID_JSON", err_msg or "JSON inválido")

                nombre = body.get("nombre")
                rif = body.get("rif")
                categoria = body.get("categoria", "Comercio General")
                if not nombre or not rif:
                    return error_response(
                        400,
                        "ERR_MISSING_FIELDS",
                        "Campos obligatorios: nombre y rif."
                    )

                res_reg = self.cazador_service.registrar_comercio_zero_friccion(
                    nombre=nombre,
                    rif=rif,
                    categoria=categoria,
                    tipo_cobertura=body.get("tipo_cobertura", "PUNTO_INTERES"),
                    zona_sector=body.get("zona_sector"),
                    direccion=body.get("direccion"),
                    lat=body.get("lat"),
                    lon=body.get("lon"),
                    radio_manual_m=body.get("radio_manual_m"),
                    tier=body.get("tier", "BASICO")
                )
                return json_response(201, res_reg)

            return error_response(404, "ERR_NOT_FOUND", f"Ruta no encontrada: {method} {clean_path}")

        except DomainInvariantViolationError as dive:
            return error_response(422, "ERR_DOMAIN_INVARIANT", str(dive))
        except IllegalCouponStateTransitionError as iste:
            return error_response(409, "ERR_ILLEGAL_STATE_TRANSITION", str(iste))
        except Exception as ex:
            return error_response(500, "ERR_INTERNAL", f"Error procesando solicitud: {str(ex)}")


# ============================================================================
# CLI DE AUTO-VERIFICACIÓN (Pilar II & V)
# ============================================================================

def run_self_verification() -> bool:
    """Verifica formalmente el CazadorRouter con solicitudes sintéticas."""
    print("🧪 Verificando CazadorRouter...")
    router = CazadorRouter()

    # 1. Match checks
    assert router.match("GET", "/api/v1/cazador/ofertas") is True
    assert router.match("POST", "/api/v1/cazador/cupon/reclamar") is True
    assert router.match("GET", "/api/v1/cazador/cupones/04169991122") is True
    assert router.match("GET", "/api/v1/cazador/ruta_inexistente") is False
    print("  ✅ Match de rutas validado.")

    # 2. Radar de ofertas (Chacao: 10.4925, -66.8550)
    status, headers, body = router.handle(
        method="GET",
        path="/api/v1/cazador/ofertas?lat=10.4925&lon=-66.8550",
        clean_path="/api/v1/cazador/ofertas",
        headers={},
        body_bytes=b"",
        service=None
    )
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["success"] is True
    assert data["total_comercios_en_rango"] > 0
    print(f"  ✅ Radar de ofertas respondió 200 OK con {data['total_comercios_en_rango']} comercios.")

    # 3. Reclamo de cupón
    status_cup, _, body_cup = router.handle(
        method="POST",
        path="/api/v1/cazador/cupon/reclamar",
        clean_path="/api/v1/cazador/cupon/reclamar",
        headers={},
        body_bytes=json.dumps({"oferta_id": "OFE-001", "msisdn": "04161112233"}).encode("utf-8"),
        service=None
    )
    assert status_cup == 201
    cup_data = json.loads(body_cup.decode("utf-8"))
    assert cup_data["success"] is True
    assert "cupon" in cup_data
    print(f"  ✅ Cupón emitido 201 Created: {cup_data['cupon']['uuid']}.")

    # 4. Magic link
    status_ml, _, body_ml = router.handle(
        method="GET",
        path="/api/v1/cazador/magic-link?msisdn=04161112233&oferta_id=OFE-001",
        clean_path="/api/v1/cazador/magic-link",
        headers={},
        body_bytes=b"",
        service=None
    )
    assert status_ml == 200
    ml_data = json.loads(body_ml.decode("utf-8"))
    assert ml_data["success"] is True
    assert "magic_link" in ml_data
    print("  ✅ Magic Link generado 200 OK.")

    print("🎉 CazadorRouter verificado al 100% con CERO fallas.")
    return True


if __name__ == "__main__":
    run_self_verification()
