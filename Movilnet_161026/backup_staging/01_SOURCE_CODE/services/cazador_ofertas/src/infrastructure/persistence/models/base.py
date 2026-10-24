"""
Mixin Base para Modelos ORM de Cazador de Ofertas Movilnet.
Provee marcas temporales UTC y serialización limpia a diccionarios.
"""
import time
from sqlalchemy import Float
from sqlalchemy.orm import Mapped, mapped_column

class TimestampMixin:
    """Mixin para incorporar marcas temporales epoch consistentes y ordenables."""
    created_at: Mapped[float] = mapped_column(Float, default=time.time, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time, onupdate=time.time, nullable=False)
