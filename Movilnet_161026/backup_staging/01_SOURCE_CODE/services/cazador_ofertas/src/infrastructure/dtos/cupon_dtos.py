"""
DTOs para Cuponería Dinámica en Cazador de Ofertas Movilnet.
"""
from typing import Optional
from pydantic import BaseModel, Field

class ReclamarCuponDTO(BaseModel):
    oferta_id: str = Field(..., description="ID de la oferta existente")
    msisdn: str = Field(..., description="Número Movilnet (ej: 04161234567)")

class CanjearCuponDTO(BaseModel):
    cupon_id: str = Field(..., description="UUID del cupón a redimir")
    msisdn: str = Field(..., description="Número del titular")
    comercio_id: str = Field(..., description="ID del comercio que valida en caja")
    firma_hmac: str = Field(..., description="Firma criptográfica TOTP")
