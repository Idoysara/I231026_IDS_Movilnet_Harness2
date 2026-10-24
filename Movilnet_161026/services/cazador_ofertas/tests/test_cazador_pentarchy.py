"""
Suite de Pruebas Automatizadas de Nivel Militar para Cazador de Ofertas Movilnet.
Cubre las Fases 0 a 4 de la Pentarquía IDS_CORE:
- Invariantes Financieras (Díaz Robisco Margen >= 35%)
- FSM de Ciclo de Vida del Cupón
- Radar Espacial Haversine y Filtro de 3 Anillos
- Bóveda Criptográfica TOTP + Anti-Replay
- Pasarela Idempotente y Split 20/80
- Endpoints REST de FastAPI con TestClient
"""
import sys
from pathlib import Path
import pytest
from starlette.testclient import TestClient

# Configuración limpia de sys.path para carpeta de cliente
CLIENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

for p in (str(PROJECT_ROOT), str(CLIENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.domain.entities import (
    Comercio, Oferta, Cupon, EstadoCupon, TierComercio
)
from src.domain.invariants import (
    CazadorInvariants, DomainInvariantViolationError
)
from src.domain.fsm import (
    CouponFSM, IllegalCouponStateTransitionError
)
from src.application.cazador_service import (
    CazadorApplicationService
)
from src.infrastructure.app import app

# =============================================================================
# 1. PRUEBAS DE DOMINIO E INVARIANTES MATEMÁTICAS (FASE 0 / GENESIS)
# =============================================================================

def test_invariante_margen_bruto_valido():
    """Margen >= 35% debe ser aceptado."""
    # Venta: 100, Costo: 60 -> Margen = (100 - 60) / 100 = 40% >= 35%
    valido, margen = CazadorInvariants.validar_margen_bruto(100.0, 60.0)
    assert valido is True
    assert margen == 40.0

def test_invariante_margen_bruto_rechazado():
    """Margen < 35% debe ser rechazado por DomainInvariantViolationError."""
    # Venta: 100, Costo: 75 -> Margen = (100 - 75) / 100 = 25% < 35%
    with pytest.raises(DomainInvariantViolationError) as exc_info:
        CazadorInvariants.validar_margen_bruto(100.0, 75.0)
    assert "Margen bruto de 25.00% es inferior al umbral mínimo del 35.0%" in str(exc_info.value)

def test_invariante_margen_precios_invalidos():
    """Precios <= 0 o costos negativos deben lanzar DomainInvariantViolationError."""
    with pytest.raises(DomainInvariantViolationError):
        CazadorInvariants.validar_margen_bruto(0.0, 10.0)
    with pytest.raises(DomainInvariantViolationError):
        CazadorInvariants.validar_margen_bruto(100.0, -5.0)

def test_validacion_msisdn_movilnet():
    """Prefijos 0416 y 0426 deben ser válidos; otras operadoras deben ser rechazadas."""
    assert CazadorInvariants.validar_msisdn_movilnet("04161234567") == "04161234567"
    assert CazadorInvariants.validar_msisdn_movilnet("04269876543") == "04269876543"
    assert CazadorInvariants.validar_msisdn_movilnet("+58416-555-1234") == "584165551234"

    # Rechazos
    with pytest.raises(DomainInvariantViolationError):
        CazadorInvariants.validar_msisdn_movilnet("04141234567") # Digitel
    with pytest.raises(DomainInvariantViolationError):
        CazadorInvariants.validar_msisdn_movilnet("04129876543") # Digitel

def test_validacion_idempotencia_key():
    """Clave de idempotencia debe tener longitud >= 8 caracteres."""
    assert CazadorInvariants.validar_idempotencia_key("KEY-12345678") == "KEY-12345678"
    with pytest.raises(DomainInvariantViolationError):
        CazadorInvariants.validar_idempotencia_key("corta")
    with pytest.raises(DomainInvariantViolationError):
        CazadorInvariants.validar_idempotencia_key("")

def test_split_transaccional_20_80():
    """Split 20% Telco Movilnet / 80% Comercio."""
    telco, neto = CazadorInvariants.calcular_split_transaccional(100.0)
    assert telco == 20.0
    assert neto == 80.0

    telco2, neto2 = CazadorInvariants.calcular_split_transaccional(95.0)
    assert telco2 == 19.0
    assert neto2 == 76.0

# =============================================================================
# 2. PRUEBAS DE MÁQUINA DE ESTADOS FINITOS (FSM) DEL CUPÓN (FASE 2)
# =============================================================================

def test_fsm_transiciones_legales():
    """Transiciones legales deben permitirse."""
    assert CouponFSM.validar_transicion(EstadoCupon.EMITIDO, EstadoCupon.RESERVADO) is True
    assert CouponFSM.validar_transicion(EstadoCupon.EMITIDO, EstadoCupon.CANJEADO) is True
    assert CouponFSM.validar_transicion(EstadoCupon.RESERVADO, EstadoCupon.CANJEADO) is True
    assert CouponFSM.validar_transicion(EstadoCupon.EMITIDO, EstadoCupon.EXPIRADO) is True

def test_fsm_transiciones_ilegales_doble_gasto():
    """Un cupón CANJEADO o EXPIRADO es inmutable. No puede re-canjearse ni transicionar."""
    with pytest.raises(IllegalCouponStateTransitionError):
        CouponFSM.validar_transicion(EstadoCupon.CANJEADO, EstadoCupon.CANJEADO)

    with pytest.raises(IllegalCouponStateTransitionError):
        CouponFSM.validar_transicion(EstadoCupon.CANJEADO, EstadoCupon.EMITIDO)

    with pytest.raises(IllegalCouponStateTransitionError):
        CouponFSM.validar_transicion(EstadoCupon.EXPIRADO, EstadoCupon.CANJEADO)

# =============================================================================
# 3. PRUEBAS DE SERVICIO DE APLICACIÓN Y ECOSISTEMA SIMBIÓTICO
# =============================================================================

@pytest.fixture
def service():
    # Instancia aislada del servicio con datos semilla
    return CazadorApplicationService()

def test_radar_geoespacial_clasificacion_anillos(service):
    """Prueba que el radar clasifique adecuadamente las ofertas de Caracas en sus 3 anillos."""
    # Coordenadas en Chacao (cerca de Avila Gourmet)
    res = service.buscar_ofertas_radar(user_lat=10.4912, user_lon=-66.8580, max_distancia_m=3000.0)
    assert res["success"] is True
    assert res["total_comercios_en_rango"] > 0
    assert "zona_1_inmediata" in res["anillos"]
    assert "zona_2_vecindario" in res["anillos"]
    assert "zona_3_urbana" in res["anillos"]

def test_flujo_completo_reclamo_y_canje_cupon(service):
    """Flujo end-to-end: reclamo de cupón dinámico -> validación de firma -> canje atómico en caja."""
    oferta_id = "OFE-001"
    msisdn = "04161234567"

    # 1. Obtener stock inicial
    stock_inicial = service.ofertas[oferta_id].stock_disponible

    # 2. Reclamar cupón
    reclamo = service.reclamar_cupon(oferta_id=oferta_id, msisdn=msisdn)
    assert reclamo["success"] is True
    cupon = reclamo["cupon"]
    assert cupon["estado"] == "EMITIDO"
    assert cupon["codigo_dinamico"].startswith("QRO-")
    assert len(cupon["firma_hmac"]) == 16

    # Verificar reducción de stock
    assert service.ofertas[oferta_id].stock_disponible == stock_inicial - 1

    # 3. Canjear cupón en caja POS
    canje = service.canjear_cupon(
        cupon_id=cupon["uuid"],
        msisdn=msisdn,
        comercio_id=cupon["comercio_id"],
        firma_hmac=cupon["firma_hmac"]
    )
    assert canje["success"] is True
    assert canje["estado"] == "CANJEADO"
    assert service.cupones[cupon["uuid"]].estado == EstadoCupon.CANJEADO

    # 4. Intentar doble canje (Ataque de Replay) -> Debe fallar
    with pytest.raises(IllegalCouponStateTransitionError):
        service.canjear_cupon(
            cupon_id=cupon["uuid"],
            msisdn=msisdn,
            comercio_id=cupon["comercio_id"],
            firma_hmac=cupon["firma_hmac"]
        )

def test_carrier_billing_idempotente(service):
    """Prueba de débito Carrier Billing con validación de idempotencia."""
    msisdn = "04169876543"
    monto = 95.0
    key = "TEST-IDEMP-KEY-99999"

    # Primer cobro
    res1 = service.procesar_carrier_billing(msisdn=msisdn, monto_ves=monto, idempotency_key=key)
    assert res1["success"] is True
    assert res1["idempotent_replay"] is False
    assert res1["split"]["telco_20_pct"] == 19.0
    assert res1["split"]["neto_80_pct"] == 76.0

    # Segundo cobro idéntico -> Debe retornar la respuesta cacheada sin re-cobrar
    res2 = service.procesar_carrier_billing(msisdn=msisdn, monto_ves=monto, idempotency_key=key)
    assert res2["success"] is True
    assert res2["idempotent_replay"] is True

# =============================================================================
# 4. PRUEBAS DE INTEGRACIÓN HTTP REST (FASTAPI / TESTCLIENT)
# =============================================================================

@pytest.fixture
def client():
    return TestClient(app)

def test_endpoint_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["port"] == 8030

def test_endpoint_radar_ofertas(client):
    response = client.get("/api/radar/ofertas?lat=10.4912&lon=-66.8580&max_m=3000")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "anillos" in data

def test_endpoint_cupon_reclamo_y_canje(client):
    # 1. Reclamar cupón vía API
    resp_reclamar = client.post("/api/cupon/reclamar", json={
        "oferta_id": "OFE-002",
        "msisdn": "04261112233"
    })
    assert resp_reclamar.status_code == 201
    cupon_data = resp_reclamar.json()["cupon"]

    # 2. Canjear cupón vía API
    resp_canjear = client.post("/api/cupon/canjear", json={
        "cupon_id": cupon_data["uuid"],
        "msisdn": "04261112233",
        "comercio_id": cupon_data["comercio_id"],
        "firma_hmac": cupon_data["firma_hmac"]
    })
    assert resp_canjear.status_code == 200
    assert resp_canjear.json()["estado"] == "CANJEADO"

    # 3. Intentar re-canjear -> Debe devolver HTTP 409 Conflict
    resp_recanjear = client.post("/api/cupon/canjear", json={
        "cupon_id": cupon_data["uuid"],
        "msisdn": "04261112233",
        "comercio_id": cupon_data["comercio_id"],
        "firma_hmac": cupon_data["firma_hmac"]
    })
    assert resp_recanjear.status_code == 409

def test_endpoint_carrier_billing_rechazo_operadora_ajena(client):
    """Operadora Digitel (0414) debe ser rechazada con HTTP 422."""
    resp = client.post("/api/billing/debitar", json={
        "msisdn": "04141234567",
        "monto_ves": 95.0,
        "idempotency_key": "TX-DIGITEL-ERR-001"
    })
    assert resp.status_code == 422
    assert "no pertenece a la operadora Movilnet" in resp.json()["detail"]

def test_invariante_grounding_real_b2c_cero_alucinacion(service):
    """
    Invariante Fundamental: Prohibido alucinar o proponer ofertas sintéticas no respaldadas por datos reales.
    Toda oferta debe residir físicamente en el catálogo auditado.
    """
    # 1. Oferta real en catálogo -> Pasa validación
    assert CazadorInvariants.validar_grounding_oferta_b2c("OFE-001", set(service.ofertas.keys())) is True

    # 2. Oferta alucinada / inexistente -> Lanza DomainInvariantViolationError
    with pytest.raises(DomainInvariantViolationError) as exc_info:
        CazadorInvariants.validar_grounding_oferta_b2c("OFE-FANTASMA-999", set(service.ofertas.keys()))
    assert "Prohibida la alucinación o invención de ofertas sin respaldo físico" in str(exc_info.value)

    # 3. Intentar reclamar oferta alucinada en el servicio -> Rechazo inmediato
    with pytest.raises(DomainInvariantViolationError) as exc_service:
        service.reclamar_cupon("OFE-FANTASMA-999", "04161234567")
    assert "no existe en el catálogo real verificado" in str(exc_service.value)

def test_endpoint_cupon_rechazo_oferta_alucinada(client):
    """La API REST debe responder HTTP 422 con mensaje explícito ante ofertas alucinadas."""
    resp = client.post("/api/cupon/reclamar", json={
        "oferta_id": "OFE-ALUCINADA-TOTAL",
        "msisdn": "04161234567"
    })
    assert resp.status_code == 422
    data = resp.json()
    assert data["error_type"] == "DomainInvariantViolation"
    assert "Prohibida la alucinación o invención de ofertas" in data["detail"]

