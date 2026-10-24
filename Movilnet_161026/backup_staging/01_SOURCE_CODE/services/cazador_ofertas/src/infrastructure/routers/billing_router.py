"""
Router para Facturación Directa Carrier Billing Movilnet (Puerto :8030).
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, status

from ..dependencies import get_cazador_service
from ...application.cazador_service import CazadorApplicationService
from ..dtos.billing_dtos import CarrierBillingDTO, BillingResponseDTO

router = APIRouter(prefix="/api/billing", tags=["Carrier Billing Movilnet"])

@router.post("/debitar")
def procesar_billing(
    body: CarrierBillingDTO,
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> Dict[str, Any]:
    """
    Ejecuta un cobro a la línea Movilnet (0416/0426) con garantía de idempotencia
    y split transaccional inmutable (20% Telco / 80% Comercio).
    """
    res = service.procesar_carrier_billing(
        msisdn=body.msisdn,
        monto_ves=body.monto_ves,
        idempotency_key=body.idempotency_key
    )
    return res

@router.get("/historial/{msisdn}")
def historial_billing(
    msisdn: str,
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> Dict[str, Any]:
    """
    Retorna el historial de débitos Carrier Billing procesados para una línea.
    """
    txs = service.obtener_historial_billing(msisdn)
    return {
        "success": True,
        "msisdn": msisdn,
        "total": len(txs),
        "transacciones": txs
    }
