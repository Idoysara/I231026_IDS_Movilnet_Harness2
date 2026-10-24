"""
Router para Catálogo de Comercios, Ofertas y Métricas de Rendimiento (Puerto :8030).
"""
import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, status

from ..dependencies import get_cazador_service
from ...application.cazador_service import CazadorApplicationService
from ..dtos.oferta_dtos import PublicarOfertaDTO, RegistrarComercioDTO

router = APIRouter(prefix="/api", tags=["Catálogo y Métricas"])

@router.get("/comercios")
def listar_comercios(
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> List[Dict[str, Any]]:
    """Lista todos los comercios afiliados verificados."""
    return [c.model_dump() for c in service.listar_comercios()]

@router.post("/comercios", status_code=status.HTTP_201_CREATED)
def crear_comercio(
    body: RegistrarComercioDTO,
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> Dict[str, Any]:
    """
    Registra un nuevo comercio o empresa de servicios en el radar.
    """
    datos = body.model_dump()
    if not datos.get("id"):
        datos["id"] = f"COM-{uuid.uuid4().hex[:6].upper()}"
    comercio = service.registrar_comercio(datos)
    return {"success": True, "comercio": comercio.model_dump()}

@router.get("/ofertas")
def listar_ofertas(
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> List[Dict[str, Any]]:
    """Lista todas las ofertas publicadas activas."""
    return [o.model_dump() for o in service.listar_ofertas()]

@router.post("/ofertas", status_code=status.HTTP_201_CREATED)
def crear_oferta(
    body: PublicarOfertaDTO,
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> Dict[str, Any]:
    """
    Publica una nueva oferta comercial validando la Invariante II (Margen Bruto >= 35%).
    """
    oferta = service.publicar_oferta(body.model_dump())
    return {"success": True, "oferta": oferta.model_dump()}

@router.get("/metricas")
def metricas_dashboard(
    service: CazadorApplicationService = Depends(get_cazador_service)
) -> Dict[str, Any]:
    """Retorna las métricas cuantitativas clave del sistema."""
    return service.obtener_resumen_metricas()
