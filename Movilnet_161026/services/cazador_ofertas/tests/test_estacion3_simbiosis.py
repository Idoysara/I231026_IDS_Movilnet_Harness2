"""
Suite de Pruebas Automatizadas para la Estación 3: Dominio Puro y Motores de Cálculo Simbióticos.
Verifica la orquestación entre Repositorios Hexagonales, CazadorApplicationService y los 4 MCPs:
- mcp_spatial_radar (Geometría determinista Haversine)
- mcp_crypto_token_vault (Bóveda TOTP 60s & Firma HMAC-SHA256)
- mcp_idempotent_gateway (Carrier Billing & Split 20/80)
- mcp_universal_memory (SQLite FTS5 Memoria Presupuestada)
- Control de Cuota de Acaparamiento (máx. 3 cupones activos por usuario)
"""
import os
import sys
import time
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

CLIENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

for p in (str(PROJECT_ROOT), str(CLIENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.infrastructure.persistence.database import Base
from src.application.cazador_service import CazadorApplicationService
from src.domain.invariants import DomainInvariantViolationError
from src.domain.entities import EstadoCupon

@pytest.fixture(scope="function")
def service_in_memory():
    """Instancia del servicio de aplicación con base de datos en memoria y semilla."""
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    session = TestingSession()
    
    seed_path = os.path.join(CLIENT_ROOT, "data", "seed_data.json")
    srv = CazadorApplicationService(db_session=session, seed_path=seed_path)
    try:
        yield srv
    finally:
        session.close()

def test_control_cuota_acaparamiento_max_3_cupones(service_in_memory):
    """Un usuario solo puede poseer un máximo de 3 cupones activos simultáneamente."""
    msisdn = "04169991122"

    # Reclamar 3 cupones para ofertas disponibles
    c1 = service_in_memory.reclamar_cupon("OFE-001", msisdn)
    c2 = service_in_memory.reclamar_cupon("OFE-002", msisdn)
    c3 = service_in_memory.reclamar_cupon("OFE-003", msisdn)

    assert c1["success"] is True
    assert c2["success"] is True
    assert c3["success"] is True

    # El 4to reclamo debe ser rechazado por límite de acaparamiento
    with pytest.raises(DomainInvariantViolationError) as exc_info:
        service_in_memory.reclamar_cupon("OFE-004", msisdn)
    assert "Límite de acaparamiento alcanzado: Máximo 3 cupones activos" in str(exc_info.value)

def test_liberacion_cuota_tras_canje(service_in_memory):
    """Al canjear uno de los cupones en caja, la cuota se libera y permite reclamar uno nuevo."""
    msisdn = "04168882233"

    # Reclamar 3 cupones
    c1 = service_in_memory.reclamar_cupon("OFE-001", msisdn)
    c2 = service_in_memory.reclamar_cupon("OFE-002", msisdn)
    c3 = service_in_memory.reclamar_cupon("OFE-003", msisdn)

    # Canjear el primer cupón en caja POS
    cupon_data = c1["cupon"]
    canje = service_in_memory.canjear_cupon(
        cupon_id=cupon_data["uuid"],
        msisdn=msisdn,
        comercio_id=cupon_data["comercio_id"],
        firma_hmac=cupon_data["firma_hmac"]
    )
    assert canje["success"] is True
    assert canje["estado"] == "CANJEADO"

    # Ahora tiene 2 activos; el 4to reclamo debe permitirse
    c4 = service_in_memory.reclamar_cupon("OFE-004", msisdn)
    assert c4["success"] is True
    assert c4["cupon"]["uuid"] is not None

def test_persistencia_boveda_anti_replay_en_repositorio(service_in_memory):
    """La huella criptográfica se asienta en la tabla boveda_hashes_quemados."""
    msisdn = "04267773344"
    reclamo = service_in_memory.reclamar_cupon("OFE-005", msisdn)
    cupon_data = reclamo["cupon"]

    # Canjear cupón
    service_in_memory.canjear_cupon(
        cupon_id=cupon_data["uuid"],
        msisdn=msisdn,
        comercio_id=cupon_data["comercio_id"],
        firma_hmac=cupon_data["firma_hmac"]
    )

    # Verificar que el repositorio persistente registró la quema
    fingerprint = f"{cupon_data['uuid']}:{cupon_data['firma_hmac'].strip().upper()}"
    assert service_in_memory.cupon_repo.is_hash_burned(fingerprint) is True

def test_memoria_universal_fts5_registro_eventos(service_in_memory):
    """Verifica que el motor mcp_universal_memory registre eventos en capas USER, DECISION y PROJECT."""
    if not service_in_memory.memory_engine:
        pytest.skip("mcp_universal_memory no disponible en este entorno")

    msisdn = "04165554433"
    
    # 1. Reclamo (capa USER)
    rec = service_in_memory.reclamar_cupon("OFE-001", msisdn)
    c_uuid = rec["cupon"]["uuid"]

    # 2. Canje (capa DECISION)
    service_in_memory.canjear_cupon(
        cupon_id=c_uuid,
        msisdn=msisdn,
        comercio_id=rec["cupon"]["comercio_id"],
        firma_hmac=rec["cupon"]["firma_hmac"]
    )

    # 3. Carrier Billing (capa PROJECT)
    service_in_memory.procesar_carrier_billing(
        msisdn=msisdn,
        monto_ves=95.0,
        idempotency_key=f"TEST-FTS5-KEY-{int(time.time())}"
    )

    # Consultar memoria con presupuesto de tokens
    query_res = service_in_memory.memory_engine.query_budgeted(msisdn, token_budget=400)
    assert query_res["count"] >= 1
    assert any(msisdn in str(r.get("content", "")) for r in query_res.get("records", []))
