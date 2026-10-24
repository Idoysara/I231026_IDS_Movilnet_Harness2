"""
Repositorio Especializado para Ofertas y Promociones.
Garantiza decremento atómico de stock físico en caja.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from .base_repository import BaseRepository
from ..models.oferta_model import OfertaModel

class OfertaRepository(BaseRepository[OfertaModel]):
    def __init__(self, session: Session):
        super().__init__(session, OfertaModel)

    def get_all_active(self) -> List[OfertaModel]:
        return self.session.query(OfertaModel).filter(
            OfertaModel.activa.is_(True),
            OfertaModel.stock_disponible > 0
        ).all()

    def get_by_comercio(self, comercio_id: str, only_active: bool = True) -> List[OfertaModel]:
        query = self.session.query(OfertaModel).filter_by(comercio_id=comercio_id)
        if only_active:
            query = query.filter(OfertaModel.activa.is_(True), OfertaModel.stock_disponible > 0)
        return query.all()

    def decrement_stock_atomic(self, oferta_id: str) -> bool:
        """
        Decrementa el stock disponible en 1 de forma atómica.
        Retorna True si la reducción fue exitosa, False si no había stock.
        """
        oferta = self.session.query(OfertaModel).filter_by(id=oferta_id).with_for_update().first()
        if not oferta or not oferta.activa or oferta.stock_disponible <= 0:
            return False

        oferta.stock_disponible -= 1
        if oferta.stock_disponible == 0:
            # Auto-pausar si se agota
            oferta.activa = False

        self.session.commit()
        self.session.refresh(oferta)
        return True
