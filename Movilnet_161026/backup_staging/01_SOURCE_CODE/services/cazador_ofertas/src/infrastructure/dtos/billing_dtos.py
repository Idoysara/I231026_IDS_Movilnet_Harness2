"""
DTOs para Débitos Carrier Billing Movilnet (Puerto :8030).
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class CarrierBillingDTO(BaseModel):
    msisdn: str = Field(..., description="Número Movilnet (ej: 04161234567 o 04261234567)")
    monto_ves: float = Field(..., gt=0, description="Monto en Bolívares a debitar")
    idempotency_key: str = Field(..., min_length=8, description="Llave de idempotencia única")

class BillingResponseDTO(BaseModel):
    success: bool
    transaccion: Dict[str, Any]
    split: Dict[str, float]
    idempotent_replay: bool = False
    carrier: Optional[str] = "Movilnet 0416/0426"
