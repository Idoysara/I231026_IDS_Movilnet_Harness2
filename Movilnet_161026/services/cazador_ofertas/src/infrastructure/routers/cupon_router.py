"""
Router para Cuponería Dinámica TOTP y Validación en Caja POS (Puerto :8030).
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, status

from ..dependencies import get_cazador_service
from ...application.cazador_service import CazadorApplicationService
from ..dtos.cupon_dtos import ReclamarCuponDTO, CanjearCuponDTO

router = APIRouter(prefix="/api/cupon", tags=["Cuponería Dinámica"])

@router.post("/reclamar", status_code=status.HTTP_201_CREATED)
def reclamar_cupon(
    body: ReclamarCuponDTO,
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> Dict[str, Any]:
    """
    Emite un cupón dinámico con código TOTP + firma criptográfica HMAC.
    Aplica regla anti-acaparamiento (máximo 3 cupones activos por usuario).
    """
    res = service.reclamar_cupon(oferta_id=body.oferta_id, msisdn=body.msisdn)
    return res

@router.post("/canjear")
def canjear_cupon(
    body: CanjearCuponDTO,
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> Dict[str, Any]:
    """
    Valida y canjea un cupón dinámico en el punto de venta (POS) del comercio.
    Verifica la FSM inmutable y registra la huella en la Bóveda Anti-Replay.
    """
    res = service.canjear_cupon(
        cupon_id=body.cupon_id,
        msisdn=body.msisdn,
        comercio_id=body.comercio_id,
        firma_hmac=body.firma_hmac
    )
    return res

@router.get("/usuario/{msisdn}")
def listar_cupones_usuario(
    msisdn: str,
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> Dict[str, Any]:
    """
    Consulta todos los cupones (activos y canjeados) pertenecientes a una línea Movilnet.
    """
    cupones = service.obtener_cupones_usuario(msisdn)
    return {
        "success": True,
        "msisdn": msisdn,
        "total": len(cupones),
        "cupones": cupones
    }
