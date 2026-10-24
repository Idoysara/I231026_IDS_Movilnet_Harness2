"""
Modelo ORM para Bóveda de Hashes Quemados (Anti-Replay / Anti-Doble Gasto).
Tabla: 'boveda_hashes_quemados'
Almacena huellas criptográficas consumidas en caja para invalidar reintentos en 0ms.
"""
import time
from sqlalchemy import String, Float, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

class BovedaHashesQuemadosModel(Base):
    __tablename__ = "boveda_hashes_quemados"

    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    cupon_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    comercio_id: Mapped[str] = mapped_column(String(36), nullable=False)
    quemado_en: Mapped[float] = mapped_column(Float, default=time.time, nullable=False)

    __table_args__ = (
        Index("idx_boveda_cupon_comercio", "cupon_uuid", "comercio_id"),
    )

    def to_dict(self) -> dict:
        return {
            "fingerprint": self.fingerprint,
            "cupon_uuid": self.cupon_uuid,
            "comercio_id": self.comercio_id,
            "quemado_en": self.quemado_en
        }
