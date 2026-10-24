"""
Exportación de Routers de FastAPI para Cazador de Ofertas Movilnet.
"""
from .radar_router import router as radar_router
from .cupon_router import router as cupon_router
from .billing_router import router as billing_router
from .catalogo_router import router as catalogo_router
from .deflector_router import router as deflector_router

__all__ = [
    "radar_router",
    "cupon_router",
    "billing_router",
    "catalogo_router",
    "deflector_router"
]
