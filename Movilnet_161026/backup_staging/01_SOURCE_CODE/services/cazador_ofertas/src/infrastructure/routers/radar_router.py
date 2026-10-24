"""
Router para el Radar Geoespacial de Ofertas Movilnet (Puerto :8030).
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query, Depends

from ..dependencies import get_cazador_service
from ...application.cazador_service import CazadorApplicationService

router = APIRouter(prefix="/api/radar", tags=["Radar Geoespacial"])

@router.get("/ofertas")
def radar_ofertas(
    lat: float = Query(..., description="Latitud GPS del usuario"),
    lon: float = Query(..., description="Longitud GPS del usuario"),
    max_m: float = Query(3000.0, description="Radio máximo en metros (hasta 3000m)"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría de comercio"),
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> Dict[str, Any]:
    """
    Consulta ofertas geolocalizadas agrupadas en los 3 anillos concéntricos:
    1. Caliente (0 - 500m): Transeúntes inmediatos.
    2. Tibio (500m - 1500m): Caminata corta (5-15 min).
    3. Frío (1500m - 3000m): Vehículo / transporte.
    """
    res = service.buscar_ofertas_radar(
        user_lat=lat,
        user_lon=lon,
        max_distancia_m=max_m,
        categoria=categoria
    )
    return res
