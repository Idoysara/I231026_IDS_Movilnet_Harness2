"""
Repositorio Especializado para Cupones y Bóveda Anti-Replay.
Tabla: 'cupones' y 'boveda_hashes_quemados'.
"""
import time
from typing import List, Optional
from sqlalchemy.orm import Session
from .base_repository import BaseRepository
from ..models.cupon_model import CuponModel
from ..models.boveda_model import BovedaHashesQuemadosModel

class CuponRepository(BaseRepository[CuponModel]):
    def __init__(self, session: Session):
        super().__init__(session, CuponModel)

    def get_by_uuid(self, cupon_uuid: str) -> Optional[CuponModel]:
        return self.session.query(CuponModel).filter_by(uuid=cupon_uuid).first()

    def get_by_user(self, msisdn: str) -> List[CuponModel]:
        return self.session.query(CuponModel).filter_by(usuario_msisdn=msisdn).order_by(CuponModel.created_at.desc()).all()

    def count_active_by_user(self, msisdn: str) -> int:
        """Cuenta cupones en estado EMITIDO o RESERVADO (regla de tope de acaparamiento)."""
        return self.session.query(CuponModel).filter(
            CuponModel.usuario_msisdn == msisdn,
            CuponModel.estado.in_(["EMITIDO", "RESERVADO"])
        ).count()

    def update_estado(self, cupon_uuid: str, nuevo_estado: str, canjeado_en: Optional[float] = None) -> Optional[CuponModel]:
        cupon = self.get_by_uuid(cupon_uuid)
        if not cupon:
            return None
        cupon.estado = nuevo_estado
        if canjeado_en is not None:
            cupon.canjeado_en = canjeado_en
        self.session.commit()
        self.session.refresh(cupon)
        return cupon

    def is_hash_burned(self, fingerprint: str) -> bool:
        """Verifica en la bóveda de persistencia si el hash ya fue quemado."""
        return self.session.query(BovedaHashesQuemadosModel).filter_by(fingerprint=fingerprint).first() is not None

    def burn_hash(self, fingerprint: str, cupon_uuid: str, comercio_id: str) -> BovedaHashesQuemadosModel:
        """Registra la quema atómica de la huella del cupón."""
        boveda_entry = BovedaHashesQuemadosModel(
            fingerprint=fingerprint,
            cupon_uuid=cupon_uuid,
            comercio_id=comercio_id,
            quemado_en=time.time()
        )
        self.session.add(boveda_entry)
        self.session.commit()
        self.session.refresh(boveda_entry)
        return boveda_entry
