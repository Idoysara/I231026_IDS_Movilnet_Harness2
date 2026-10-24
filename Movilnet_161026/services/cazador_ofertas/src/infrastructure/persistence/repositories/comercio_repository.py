"""
Repositorio Especializado para Comercios Aliados.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from .base_repository import BaseRepository
from ..models.comercio_model import ComercioModel

class ComercioRepository(BaseRepository[ComercioModel]):
    def __init__(self, session: Session):
        super().__init__(session, ComercioModel)

    def get_active(self) -> List[ComercioModel]:
        return self.session.query(ComercioModel).filter_by(activo=True).all()

    def get_by_rif(self, rif: str) -> Optional[ComercioModel]:
        return self.session.query(ComercioModel).filter_by(rif=rif.strip().upper()).first()

    def get_by_categoria(self, categoria: str) -> List[ComercioModel]:
        return self.session.query(ComercioModel).filter(
            ComercioModel.categoria.ilike(f"%{categoria.strip()}%"),
            ComercioModel.activo.is_(True)
        ).all()
