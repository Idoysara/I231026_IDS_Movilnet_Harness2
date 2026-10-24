"""
DTOs para Webhooks de Deflexión Conversacional (WhatsApp / SMS SMPP) y Magic Links Zero-Rating.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class MensajeEntranteDTO(BaseModel):
    canal: str = Field(..., description="Canal de entrada: 'whatsapp' o 'sms'")
    remitente: str = Field(..., description="Número del usuario (ej: 04161234567 o +584161234567)")
    mensaje: str = Field(..., description="Texto enviado por el usuario")
    ubicacion_lat: Optional[float] = Field(None, description="Latitud GPS compartida")
    ubicacion_lon: Optional[float] = Field(None, description="Longitud GPS compartida")

class DeflectorResponseDTO(BaseModel):
    canal: str
    destinatario: str
    mensaje_saliente: str
    magic_link: Optional[str] = None
    zero_rating_activo: bool = True
    ofertas_encontradas: int = 0
    anillos_resumen: Optional[Dict[str, int]] = None

class VerificarLinkResponseDTO(BaseModel):
    valido: bool
    msisdn: str
    oferta_id: Optional[str] = None
    zero_rating_header: str
    mensaje: str
