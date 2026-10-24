"""
Entidades de Dominio Puro para Cazador de Ofertas Movilnet.
Separación estricta (Clean Architecture / DDD) con tipado exhaustivo en Pydantic v2.
"""
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import time

from .fsm import EstadoCupon

class TipoCobertura(str, Enum):
    ZONA = "ZONA"
    RUN_OF_NETWORK = "RUN_OF_NETWORK"
    PUNTO_INTERES = "PUNTO_INTERES"

class TierComercio(str, Enum):
    BASICO = "BASICO"
    DESTACADO = "DESTACADO"
    VIP_RADAR = "VIP_RADAR"
    PREMIUM = "PREMIUM"

class NivelUsuario(str, Enum):
    GRATUITO = "GRATUITO"
    CAZADOR_PRO_VIP = "CAZADOR_PRO_VIP"

class Comercio(BaseModel):
    id: str = Field(..., description="UUID o ID del comercio")
    nombre: str = Field(..., min_length=2, max_length=100)
    rif: str = Field(..., description="RIF fiscal verificado")
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    categoria: str = Field(...)
    tier: TierComercio = Field(default=TierComercio.BASICO)
    activo: bool = True
    tipo_cobertura: Optional[TipoCobertura] = Field(default=TipoCobertura.PUNTO_INTERES)
    zona_sector: Optional[str] = Field(default=None, description="Sector canónico o polígono asignado")
    radio_cobertura_m: float = Field(default=500.0, ge=50.0, description="Radio de cobertura en metros (Smart Default 500m)")
    direccion: Optional[str] = Field(default=None, description="Dirección física o punto de referencia")


class Oferta(BaseModel):
    id: str
    comercio_id: str
    titulo: str = Field(..., min_length=5, max_length=120)
    precio_regular_ves: float = Field(..., gt=0)
    precio_oferta_ves: float = Field(..., gt=0)
    costo_directo_ves: float = Field(..., ge=0)
    descuento_pct: float = Field(default=0.0)
    stock_disponible: int = Field(default=10, ge=0)
    horario_validez: str = "10:00 - 20:00"
    activa: bool = True

    @field_validator("precio_oferta_ves")
    @classmethod
    def validar_precio_menor(cls, v, info):
        if "precio_regular_ves" in info.data and v >= info.data["precio_regular_ves"]:
            raise ValueError("El precio de oferta debe ser estrictamente menor al precio regular.")
        return v

class Cupon(BaseModel):
    uuid: str
    oferta_id: str
    usuario_msisdn: str
    comercio_id: str
    codigo_dinamico: str
    firma_hmac: str
    estado: EstadoCupon = EstadoCupon.EMITIDO
    emitido_en: float = Field(default_factory=time.time)
    expira_en_paso: int
    canjeado_en: Optional[float] = None

class TransaccionBilling(BaseModel):
    id: str
    idempotency_key: str
    msisdn: str
    monto_ves: float = Field(..., gt=0)
    comision_telco_ves: float
    neto_comercio_ves: float
    estatus: str = "PROCESADO"
    timestamp: float = Field(default_factory=time.time)
