"""
Repositorio Especializado para Carrier Billing y Registro de Idempotencia.
Tabla: 'transacciones_billing'.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from .base_repository import BaseRepository
from ..models.billing_model import TransaccionBillingModel

class BillingRepository(BaseRepository[TransaccionBillingModel]):
    def __init__(self, session: Session):
        super().__init__(session, TransaccionBillingModel)

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[TransaccionBillingModel]:
        return self.session.query(TransaccionBillingModel).filter_by(
            idempotency_key=idempotency_key.strip()
        ).first()

    def get_by_msisdn(self, msisdn: str) -> List[TransaccionBillingModel]:
        return self.session.query(TransaccionBillingModel).filter_by(
            msisdn=msisdn
        ).order_by(TransaccionBillingModel.created_at.desc()).all()

    def record_billing(
        self,
        tx_id: str,
        idempotency_key: str,
        msisdn: str,
        monto_ves: float,
        comision_telco_ves: float,
        neto_comercio_ves: float,
        estatus: str = "PROCESADO"
    ) -> TransaccionBillingModel:
        tx = TransaccionBillingModel(
            id=tx_id,
            idempotency_key=idempotency_key.strip(),
            msisdn=msisdn.strip(),
            monto_ves=monto_ves,
            comision_telco_ves=comision_telco_ves,
            neto_comercio_ves=neto_comercio_ves,
            estatus=estatus
        )
        return self.save(tx)
