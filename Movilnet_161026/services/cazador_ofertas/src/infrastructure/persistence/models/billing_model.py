"""
Modelo ORM para Transacciones de Carrier Billing en Cazador de Ofertas Movilnet.
Tabla: 'transacciones_billing'
Garantiza idempotencia única contra cobros duplicados y split 20/80 auditado.
"""
from sqlalchemy import String, Float, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .base import TimestampMixin

class TransaccionBillingModel(Base, TimestampMixin):
    __tablename__ = "transacciones_billing"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    msisdn: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    monto_ves: Mapped[float] = mapped_column(Float, nullable=False)
    comision_telco_ves: Mapped[float] = mapped_column(Float, nullable=False)
    neto_comercio_ves: Mapped[float] = mapped_column(Float, nullable=False)
    estatus: Mapped[str] = mapped_column(String(20), default="PROCESADO", nullable=False)

    __table_args__ = (
        CheckConstraint("monto_ves > 0", name="chk_monto_billing_positivo"),
        CheckConstraint("comision_telco_ves >= 0", name="chk_comision_no_negativa"),
        CheckConstraint("neto_comercio_ves >= 0", name="chk_neto_no_negativo"),
        Index("idx_billing_msisdn_created", "msisdn", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "idempotency_key": self.idempotency_key,
            "msisdn": self.msisdn,
            "monto_ves": self.monto_ves,
            "comision_telco_ves": self.comision_telco_ves,
            "neto_comercio_ves": self.neto_comercio_ves,
            "estatus": self.estatus,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
