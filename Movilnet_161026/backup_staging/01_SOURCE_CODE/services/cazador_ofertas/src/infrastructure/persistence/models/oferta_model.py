"""
Modelo ORM para Ofertas y Promociones en Cazador de Ofertas Movilnet.
Tabla: 'ofertas'
Incluye constraints DDL de Invariante II (Margen >= 35%) y Precio Menor.
"""
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import TimestampMixin

if TYPE_CHECKING:
    from .comercio_model import ComercioModel
    from .cupon_model import CuponModel

class OfertaModel(Base, TimestampMixin):
    __tablename__ = "ofertas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    comercio_id: Mapped[str] = mapped_column(String(36), ForeignKey("comercios.id"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(140), nullable=False)
    precio_regular_ves: Mapped[float] = mapped_column(Float, nullable=False)
    precio_oferta_ves: Mapped[float] = mapped_column(Float, nullable=False)
    costo_directo_ves: Mapped[float] = mapped_column(Float, nullable=False)
    descuento_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    margen_pct: Mapped[float] = mapped_column(Float, nullable=False)
    stock_disponible: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    horario_validez: Mapped[str] = mapped_column(String(60), default="10:00 - 20:00", nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relaciones
    comercio: Mapped["ComercioModel"] = relationship("ComercioModel", back_populates="ofertas")
    cupones: Mapped[List["CuponModel"]] = relationship(
        "CuponModel",
        back_populates="oferta",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("precio_oferta_ves < precio_regular_ves", name="chk_precio_menor_regular"),
        CheckConstraint("margen_pct >= 35.0", name="chk_invariante_margen_minimo"),
        CheckConstraint("stock_disponible >= 0", name="chk_stock_no_negativo"),
        Index("idx_ofertas_comercio_activa", "comercio_id", "activa"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "comercio_id": self.comercio_id,
            "titulo": self.titulo,
            "precio_regular_ves": self.precio_regular_ves,
            "precio_oferta_ves": self.precio_oferta_ves,
            "costo_directo_ves": self.costo_directo_ves,
            "descuento_pct": self.descuento_pct,
            "margen_pct": self.margen_pct,
            "stock_disponible": self.stock_disponible,
            "horario_validez": self.horario_validez,
            "activa": self.activa,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
