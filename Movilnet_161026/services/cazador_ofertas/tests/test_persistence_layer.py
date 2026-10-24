"""
Suite de Pruebas Automatizadas para la Capa de Persistencia y Modelos ORM.
Estación 2 — Pentarquía IDS_CORE (Cazador de Ofertas Movilnet).
Verifica modelos SQLAlchemy 2.0, constraints DDL, Repositorios Hexagonales y quema atómica de hashes.
"""
import os
import sys
import time
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

CLIENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

for p in (str(PROJECT_ROOT), str(CLIENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.infrastructure.persistence.database import Base
from src.infrastructure.persistence.models import (
    ComercioModel, OfertaModel, CuponModel, TransaccionBillingModel, BovedaHashesQuemadosModel
)
from src.infrastructure.persistence.repositories import (
    ComercioRepository, OfertaRepository, CuponRepository, BillingRepository
)

@pytest.fixture(scope="function")
def db_session():
    """Crea una base de datos SQLite en memoria aislada para cada prueba."""
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()

# =============================================================================
# 1. PRUEBAS DE MODELOS Y CONSTRAINTS DDL
# =============================================================================

def test_constraint_oferta_precio_menor_regular(db_session):
    """El precio de oferta debe ser estrictamente menor al regular."""
    comercio = ComercioModel(
        id="COM-TEST-01",
        rif="J-99999999-1",
        nombre="Comercio Test",
        categoria="Restaurantes",
        lat=10.49,
        lon=-66.85
    )
    db_session.add(comercio)
    db_session.commit()

    # Oferta inválida: precio oferta (100) >= precio regular (100)
    oferta_invalida = OfertaModel(
        id="OFE-INV-01",
        comercio_id=comercio.id,
        titulo="Oferta Invalida Precio",
        precio_regular_ves=100.0,
        precio_oferta_ves=100.0,
        costo_directo_ves=50.0,
        margen_pct=50.0,
        stock_disponible=10
    )
    db_session.add(oferta_invalida)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_constraint_invariante_margen_minimo(db_session):
    """El margen debe ser >= 35.0%."""
    comercio = ComercioModel(
        id="COM-TEST-02",
        rif="J-99999999-2",
        nombre="Comercio Test 2",
        categoria="Farmacias",
        lat=10.49,
        lon=-66.85
    )
    db_session.add(comercio)
    db_session.commit()

    # Oferta inválida: margen 25.0% < 35.0%
    oferta_margen_bajo = OfertaModel(
        id="OFE-INV-02",
        comercio_id=comercio.id,
        titulo="Oferta Margen Bajo",
        precio_regular_ves=100.0,
        precio_oferta_ves=80.0,
        costo_directo_ves=60.0,
        margen_pct=25.0,  # Violación de constraint
        stock_disponible=10
    )
    db_session.add(oferta_margen_bajo)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_constraint_billing_monto_positivo(db_session):
    """El monto de facturación debe ser > 0."""
    tx_invalida = TransaccionBillingModel(
        id="TX-INV-01",
        idempotency_key="KEY-INV-01",
        msisdn="04161234567",
        monto_ves=0.0,  # Violación de constraint
        comision_telco_ves=0.0,
        neto_comercio_ves=0.0
    )
    db_session.add(tx_invalida)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

# =============================================================================
# 2. PRUEBAS DE REPOSITORIOS CRUD Y REGLAS DE NEGOCIO
# =============================================================================

def test_comercio_repository_operaciones(db_session):
    repo = ComercioRepository(db_session)

    c1 = ComercioModel(
        id="COM-01", rif="J-12345678-0", nombre="Panadería Altamira",
        categoria="Alimentos", lat=10.49, lon=-66.85, activo=True
    )
    c2 = ComercioModel(
        id="COM-02", rif="J-87654321-0", nombre="Farmacia Los Palos",
        categoria="Salud", lat=10.50, lon=-66.84, activo=False
    )
    repo.save(c1)
    repo.save(c2)

    # get_active solo debe retornar comercios con activo=True
    activos = repo.get_active()
    assert len(activos) == 1
    assert activos[0].id == "COM-01"

    # get_by_rif
    buscado = repo.get_by_rif("j-12345678-0")  # Case insensitive
    assert buscado is not None
    assert buscado.nombre == "Panadería Altamira"

def test_oferta_repository_decremento_atomico(db_session):
    c_repo = ComercioRepository(db_session)
    o_repo = OfertaRepository(db_session)

    comercio = ComercioModel(
        id="COM-DEC", rif="J-11112222-3", nombre="Café Central",
        categoria="Restaurantes", lat=10.49, lon=-66.85
    )
    c_repo.save(comercio)

    oferta = OfertaModel(
        id="OFE-DEC", comercio_id=comercio.id, titulo="Café + Ponqué",
        precio_regular_ves=100.0, precio_oferta_ves=60.0, costo_directo_ves=30.0,
        margen_pct=50.0, stock_disponible=1, activa=True
    )
    o_repo.save(oferta)

    # 1er decremento: de 1 a 0 (debe ser exitoso y auto-pausar)
    assert o_repo.decrement_stock_atomic(oferta.id) is True
    o_actualizada = o_repo.get_by_id(oferta.id)
    assert o_actualizada.stock_disponible == 0
    assert o_actualizada.activa is False

    # 2do decremento: con stock en 0 (debe retornar False)
    assert o_repo.decrement_stock_atomic(oferta.id) is False

def test_cupon_repository_y_boveda_anti_replay(db_session):
    c_repo = ComercioRepository(db_session)
    o_repo = OfertaRepository(db_session)
    cup_repo = CuponRepository(db_session)

    comercio = ComercioModel(
        id="COM-CUP", rif="J-33334444-5", nombre="Tienda de Deportes",
        categoria="Deportes", lat=10.49, lon=-66.85
    )
    c_repo.save(comercio)

    oferta = OfertaModel(
        id="OFE-CUP", comercio_id=comercio.id, titulo="Camiseta Deportiva",
        precio_regular_ves=500.0, precio_oferta_ves=300.0, costo_directo_ves=150.0,
        margen_pct=50.0, stock_disponible=5
    )
    o_repo.save(oferta)

    msisdn = "04169998877"
    cupon = CuponModel(
        uuid="CUP-TEST-1234",
        oferta_id=oferta.id,
        comercio_id=comercio.id,
        usuario_msisdn=msisdn,
        codigo_dinamico="QRO-TEST-1234",
        firma_hmac="ABCD1234EFGH5678",
        estado="EMITIDO",
        time_step_emision=int(time.time() // 60)
    )
    cup_repo.save(cupon)

    # Validar conteo de cupones activos
    assert cup_repo.count_active_by_user(msisdn) == 1

    # Actualizar estado a CANJEADO
    actualizado = cup_repo.update_estado(cupon.uuid, "CANJEADO", canjeado_en=time.time())
    assert actualizado.estado == "CANJEADO"
    assert actualizado.canjeado_en is not None

    # Quema de huella en la bóveda
    fingerprint = f"{cupon.uuid}:{cupon.firma_hmac}"
    assert cup_repo.is_hash_burned(fingerprint) is False
    cup_repo.burn_hash(fingerprint, cupon.uuid, comercio.id)
    assert cup_repo.is_hash_burned(fingerprint) is True

def test_billing_repository_idempotencia(db_session):
    repo = BillingRepository(db_session)
    key = "IDEMP-KEY-TEST-0001"

    tx = repo.record_billing(
        tx_id="TX-TEST-01",
        idempotency_key=key,
        msisdn="04161112233",
        monto_ves=95.0,
        comision_telco_ves=19.0,
        neto_comercio_ves=76.0
    )
    assert tx.id == "TX-TEST-01"

    # Recuperación por clave de idempotencia
    recuperada = repo.get_by_idempotency_key(key)
    assert recuperada is not None
    assert recuperada.monto_ves == 95.0

    # Intentar guardar otra con la misma clave debe violar la unicidad
    with pytest.raises(IntegrityError):
        repo.record_billing(
            tx_id="TX-DUPLICADA",
            idempotency_key=key,
            msisdn="04161112233",
            monto_ves=95.0,
            comision_telco_ves=19.0,
            neto_comercio_ves=76.0
        )
    db_session.rollback()
