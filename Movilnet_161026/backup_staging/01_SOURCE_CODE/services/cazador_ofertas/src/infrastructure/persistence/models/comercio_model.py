"""
Modelo ORM para Comercios Aliados en Cazador de Ofertas Movilnet.
Tabla: 'comercios'
"""
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import TimestampMixin

if TYPE_CHECKING:
    from .oferta_model import OfertaModel

class ComercioModel(Base, TimestampMixin):
    __tablename__ = "comercios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    rif: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    categoria: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="BASICO", nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tipo_cobertura: Mapped[str] = mapped_column(String(30), default="PUNTO_INTERES", nullable=False)
    zona_sector: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    radio_cobertura_m: Mapped[float] = mapped_column(Float, default=500.0, nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relación uno a muchos con ofertas
    ofertas: Mapped[List["OfertaModel"]] = relationship(
        "OfertaModel",
        back_populates="comercio",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        Index("idx_comercios_lat_lon", "lat", "lon"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rif": self.rif,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "lat": self.lat,
            "lon": self.lon,
            "tier": self.tier,
            "activo": self.activo,
            "tipo_cobertura": self.tipo_cobertura,
            "zona_sector": self.zona_sector,
            "radio_cobertura_m": self.radio_cobertura_m,
            "direccion": self.direccion,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

