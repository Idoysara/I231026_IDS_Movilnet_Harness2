"""
Inyección de dependencias para los Routers de FastAPI en Cazador de Ofertas Movilnet.
"""
from typing import Optional
from ..application.cazador_service import CazadorApplicationService
from .deflector.magic_link_service import MagicLinkService

# Instancias compartidas (Singleton por proceso)
_cazador_service: Optional[CazadorApplicationService] = None
_deflector_service: Optional[MagicLinkService] = None

def get_cazador_service() -> CazadorApplicationService:
    global _cazador_service
    if _cazador_service is None:
        _cazador_service = CazadorApplicationService()
    return _cazador_service

def set_cazador_service(service: CazadorApplicationService) -> None:
    """Permite inyectar un servicio mock o preconfigurado en tests."""
    global _cazador_service, _deflector_service
    _cazador_service = service
    _deflector_service = MagicLinkService(service)

def get_deflector_service() -> MagicLinkService:
    global _deflector_service
    if _deflector_service is None:
        svc = get_cazador_service()
        _deflector_service = MagicLinkService(svc)
    return _deflector_service
