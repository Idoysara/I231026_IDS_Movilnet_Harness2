"""
DTOs para Catálogo y Ofertas en Cazador de Ofertas Movilnet.
"""
from typing import Optional, List
from pydantic import BaseModel, Field

class PublicarOfertaDTO(BaseModel):
    id: str = Field(..., description="Identificador único de la oferta (ej: OFE-001)")
    comercio_id: str = Field(..., description="ID del comercio emisor")
    titulo: str = Field(..., description="Título descriptivo de la oferta")
    precio_regular_ves: float = Field(..., gt=0, description="Precio de lista original")
    precio_oferta_ves: float = Field(..., gt=0, description="Precio de oferta promocional")
    costo_directo_ves: float = Field(..., gt=0, description="Costo directo del inventario/servicio")
    descuento_pct: Optional[float] = Field(0.0, ge=0.0, le=100.0, description="Porcentaje de descuento")
    stock_disponible: int = Field(10, ge=0, description="Unidades físicas disponibles")
    horario_validez: str = Field("10:00 - 20:00", description="Horario de validez de la promoción")

class OfertaResponseDTO(BaseModel):
    id: str
    comercio_id: str
    titulo: str
    precio_regular_ves: float
    precio_oferta_ves: float
    descuento_pct: float
    stock_disponible: int
    horario_validez: str
    valida: bool

class RegistrarComercioDTO(BaseModel):
    id: Optional[str] = Field(None, description="Identificador único del comercio (opcional, auto-generado)")
    nombre: str = Field(..., min_length=2, max_length=100, description="Razón social o nombre comercial")
    rif: str = Field(..., min_length=5, max_length=20, description="RIF fiscal verificado")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitud WGS84")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitud WGS84")
    categoria: str = Field(..., description="Categoría comercial o rubro profesional")
    tier: Optional[str] = Field("BASICO", description="Nivel del comercio: BASICO, DESTACADO, VIP_RADAR")
