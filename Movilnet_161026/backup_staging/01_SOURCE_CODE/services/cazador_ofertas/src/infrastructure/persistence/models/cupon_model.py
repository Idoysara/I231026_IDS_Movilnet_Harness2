"""
Modelo ORM para Cupones Emitidos en Cazador de Ofertas Movilnet.
Tabla: 'cupones'
Gobernado por la FSM de Ciclo de Vida (EMITIDO -> RESERVADO -> CANJEADO / EXPIRADO).
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .base import TimestampMixin

if TYPE_CHECKING:
    from .oferta_model import OfertaModel

class CuponModel(Base, TimestampMixin):
    __tablename__ = "cupones"

    uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    oferta_id: Mapped[str] = mapped_column(String(36), ForeignKey("ofertas.id"), nullable=False, index=True)
    comercio_id: Mapped[str] = mapped_column(String(36), ForeignKey("comercios.id"), nullable=False, index=True)
    usuario_msisdn: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    codigo_dinamico: Mapped[str] = mapped_column(String(30), nullable=False)
    firma_hmac: Mapped[str] = mapped_column(String(32), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="EMITIDO", nullable=False, index=True)
    time_step_emision: Mapped[int] = mapped_column(Integer, nullable=False)
    canjeado_en: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relación
    oferta: Mapped["OfertaModel"] = relationship("OfertaModel", back_populates="cupones")

    __table_args__ = (
        Index("idx_cupones_usuario_estado", "usuario_msisdn", "estado"),
    )

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "oferta_id": self.oferta_id,
            "comercio_id": self.comercio_id,
            "usuario_msisdn": self.usuario_msisdn,
            "codigo_dinamico": self.codigo_dinamico,
            "firma_hmac": self.firma_hmac,
            "estado": self.estado,
            "time_step_emision": self.time_step_emision,
            "canjeado_en": self.canjeado_en,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
