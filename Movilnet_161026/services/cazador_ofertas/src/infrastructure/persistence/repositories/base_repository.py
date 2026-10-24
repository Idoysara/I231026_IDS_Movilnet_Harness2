"""
Repositorio Base Genérico para Operaciones Transaccionales.
Arquitectura Hexagonal / Repository Pattern.
"""
from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.orm import Session

T = TypeVar("T")

class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    def get_by_id(self, entity_id: str) -> Optional[T]:
        return self.session.query(self.model_class).filter_by(id=entity_id).first()

    def get_all(self) -> List[T]:
        return self.session.query(self.model_class).all()

    def save(self, entity: T) -> T:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def delete(self, entity: T) -> None:
        self.session.delete(entity)
        self.session.commit()
