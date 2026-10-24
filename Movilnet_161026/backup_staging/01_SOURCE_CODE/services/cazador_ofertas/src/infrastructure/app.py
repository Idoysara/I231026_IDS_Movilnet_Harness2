"""
FastAPI Server Hexagonal para Cazador de Ofertas Movilnet (Puerto :8030).
Ensambla routers modulares, middleware CORS, manejo de errores de dominio y PWA Zero-Rating.
"""
import os
import sys
from typing import Dict, Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Asegurar path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from .dependencies import get_cazador_service, get_deflector_service
from .routers import (
    radar_router,
    cupon_router,
    billing_router,
    catalogo_router,
    deflector_router
)
from ..domain.invariants import DomainInvariantViolationError
from ..domain.fsm import IllegalCouponStateTransitionError

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))

# Instancia global del servicio para acceso directo y retrocompatibilidad
service = get_cazador_service()
deflector_service = get_deflector_service()

app = FastAPI(
    title="Cazador de Ofertas Movilnet Core API",
    description="Motor soberano de radar geoespacial, cuponería dinámica TOTP, Deflector Conversacional y Carrier Billing 0416/0426",
    version="1.1.0"
)

# Habilitar CORS con lista blanca estricta (Zero-Wildcard, anti CWE-942)
ALLOWED_ORIGINS = [
    "http://localhost:8030",
    "http://127.0.0.1:8030",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8007",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# =============================================================================
# MANEJADORES DE EXCEPCIONES DE DOMINIO Y FSM
# =============================================================================
@app.exception_handler(DomainInvariantViolationError)
async def domain_invariant_exception_handler(request: Request, exc: DomainInvariantViolationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"success": False, "error_type": "DomainInvariantViolation", "detail": str(exc)}
    )

@app.exception_handler(IllegalCouponStateTransitionError)
async def illegal_fsm_exception_handler(request: Request, exc: IllegalCouponStateTransitionError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"success": False, "error_type": "IllegalFSMTransition", "detail": str(exc)}
    )

# =============================================================================
# ENSAMBLAJE DE ROUTERS MODULARES (TOPOLOGÍA HEXAGONAL)
# =============================================================================
app.include_router(radar_router)
app.include_router(cupon_router)
app.include_router(billing_router)
app.include_router(catalogo_router)
app.include_router(deflector_router)

# =============================================================================
# HEALTH CHECK & MONITOREO SOBERANO
# =============================================================================
@app.get("/health", tags=["Monitoreo"])
def health_check():
    metricas = service.obtener_resumen_metricas()
    return {
        "status": "ONLINE",
        "service": "cazador_ofertas_movilnet",
        "port": 8030,
        "pwa_port": 3005,
        "carrier": "Movilnet 0416/0426",
        "zero_rating": "HABILITADO",
        "metricas": metricas
    }

# =============================================================================
# FRONTEND ESTÁTICO & PWA ENTRYPOINT ZERO-RATING
# =============================================================================
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/manifest.json", response_class=FileResponse, tags=["PWA Entrypoint"])
def get_manifest():
    manifest_path = os.path.join(FRONTEND_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/manifest+json")
    return JSONResponse(status_code=404, content={"detail": "Manifest no encontrado"})

@app.get("/sw.js", response_class=FileResponse, tags=["PWA Entrypoint"])
def get_service_worker():
    sw_path = os.path.join(FRONTEND_DIR, "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    return JSONResponse(status_code=404, content={"detail": "Service Worker no encontrado"})

@app.get("/", response_class=FileResponse, tags=["PWA Entrypoint"])
def index_pwa():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"message": "Cazador de Ofertas Movilnet API está online. Frontend no encontrado."})

@app.get("/comercio", response_class=FileResponse, tags=["Dashboard Empresas"])
@app.get("/portal", response_class=FileResponse, tags=["Dashboard Empresas"])
def dashboard_comercio():
    comercio_file = os.path.join(FRONTEND_DIR, "comercio.html")
    if os.path.exists(comercio_file):
        return FileResponse(comercio_file)
    return JSONResponse({"message": "Dashboard de comercios no encontrado."})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("pruebas_clientes.28_Cazador_Ofertas.src.infrastructure.app:app", host="0.0.0.0", port=8030, reload=True)
