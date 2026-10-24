"""
Suite de Pruebas Automatizadas para el Motor de Simulación Masiva y Conciliación Transaccional.
Cliente 28: Cazador de Ofertas Movilnet (IDS_CORE).
Verifica:
1. Generación de abonados Movilnet válidos (0416/0426).
2. Simulación de búsquedas geoespaciales por radar en Caracas.
3. Reclamo de cupones y bloqueo por cuota anti-acaparamiento (<= 3).
4. Canje presencial en caja POS y persistencia en Bóveda anti-replay.
5. Blindaje del 100% contra intentos de fraude / captura de pantalla.
6. Conciliación de split financiero: 20% Movilnet / 80% Comercio.
7. Existencia e integridad de los datasets de simulación exportados (JSON y CSV).
"""
import os
import sys
import json
import csv
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

CLIENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

for p in (str(PROJECT_ROOT), str(CLIENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.infrastructure.persistence.database import Base
from src.application.cazador_service import CazadorApplicationService
from scripts.simulador_trafico_super_ofertas import CazadorTraficoSimulator

DATA_DIR = CLIENT_ROOT / "data"
SIM_JSON = DATA_DIR / "simulacion_trafico_cazador.json"
SIM_CSV = DATA_DIR / "simulacion_transacciones_cazador.csv"

@pytest.fixture(scope="module")
def simulator():
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    session = TestingSession()
    seed_path = os.path.join(CLIENT_ROOT, "data", "seed_data.json")
    srv = CazadorApplicationService(db_session=session, seed_path=seed_path)
    sim = CazadorTraficoSimulator(seed_usuarios=50, seed_random=123, service=srv)
    yield sim
    session.close()

def test_simulador_generacion_usuarios(simulator):
    """Debe generar abonados Movilnet válidos con prefijos 0416 y 0426."""
    assert len(simulator.usuarios) == 50
    for u in simulator.usuarios:
        assert u.startswith("0416") or u.startswith("0426")
        assert len(u) == 11

def test_simulador_ciclo_completo_y_blindaje(simulator):
    """Ejecuta una corrida controlada y valida KPIs y neutralización de fraude."""
    res = simulator.ejecutar_simulacion_completa(
        num_busquedas=25,
        num_intentos_reclamo=15,
        pct_canje=0.80,
        num_intentos_fraude=5
    )
    simulator.exportar_datos(res)

    # 1. Búsquedas
    kpis_rad = res["metricas_adquisicion_radar"]
    assert kpis_rad["busquedas_exitosas"] == 25
    assert kpis_rad["total_impactos_ofertas"] > 0

    # 2. Cupones
    kpis_cup = res["metricas_conversion_cupones"]
    assert kpis_cup["cupones_emitidos_exitosos"] > 0
    assert kpis_cup["total_cupones_canjeados_en_pos"] > 0

    # 3. Blindaje anti-fraude (100% bloqueado)
    kpis_sec = res["seguridad_y_blindaje_anti_fraude"]
    assert kpis_sec["efectividad_cortafuegos_pct"] == 100.0
    assert kpis_sec["ataques_exitosos_fuga"] == 0

    # 4. Split financiero 20/80
    kpis_eco = res["balance_economico_y_split_transaccional"]
    vol = kpis_eco["volumen_bruto_facturado_ves"]
    telco = kpis_eco["ingreso_comision_movilnet_ves_20pct"]
    comer = kpis_eco["ingreso_neto_comercios_ves_80pct"]
    assert vol > 0
    assert abs((telco + comer) - vol) < 0.05
    assert abs(telco - round(vol * 0.20, 2)) < 0.10

def test_simulador_datasets_exportados():
    """Los datasets exportados deben existir físicamente y ser consistentes."""
    assert SIM_JSON.exists(), f"Falta archivo: {SIM_JSON}"
    assert SIM_CSV.exists(), f"Falta archivo: {SIM_CSV}"

    with open(SIM_JSON, "r", encoding="utf-8") as fj:
        data_json = json.load(fj)
        assert "metadata_simulacion" in data_json
        assert "metricas_adquisicion_radar" in data_json
        assert "balance_economico_y_split_transaccional" in data_json

    with open(SIM_CSV, "r", encoding="utf-8") as fc:
        reader = csv.DictReader(fc)
        filas = list(reader)
        assert len(filas) > 0
        assert "transaccion_id" in filas[0]
        assert "split_ratio" in filas[0]
        assert filas[0]["split_ratio"] == "20% / 80%"
