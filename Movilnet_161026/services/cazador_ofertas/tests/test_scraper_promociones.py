"""
Suite de Pruebas Automatizadas para el Scraper e Investigador Territorial de Promociones Reales en Venezuela.
Verifica:
1. Existencia física e integridad de los datasets exportados (JSON y CSV).
2. Cumplimiento universal de la Invariante II (Margen Bruto >= 35.0%).
3. Cumplimiento de la Invariante de Precios (Precio Oferta < Precio Regular).
4. Grounding Físico Geodésico WGS84 dentro del polígono metropolitano de Caracas.
5. Cobertura completa de las 6 áreas de negocio venezolanas.
"""
import sys
import json
import csv
from pathlib import Path
import pytest

CLIENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

for p in (str(PROJECT_ROOT), str(CLIENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.scraper_ofertas_promociones_venezuela import PromocionesScraperEngine, AREAS_DE_NEGOCIO

DATA_DIR = CLIENT_ROOT / "data"
JSON_FILE = DATA_DIR / "promociones_reales_venezuela.json"
CSV_FILE = DATA_DIR / "promociones_reales_venezuela.csv"

def test_scraper_engine_compilacion():
    """El motor debe compilar sin errores de dominio ni violaciones de tipos."""
    engine = PromocionesScraperEngine()
    dataset = engine.compilar_dataset_promocional()
    assert dataset is not None
    assert "metadata" in dataset
    assert "empresas" in dataset
    assert "promociones" in dataset
    assert len(dataset["promociones"]) >= 20
    assert len(dataset["empresas"]) >= 15

def test_scraper_dataset_archivos_fisicos():
    """Los archivos JSON y CSV deben existir físicamente y ser parseables."""
    assert JSON_FILE.exists(), f"Falta archivo: {JSON_FILE}"
    assert CSV_FILE.exists(), f"Falta archivo: {CSV_FILE}"

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["metadata"]["total_promociones_activas"] >= 20

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        filas = list(reader)
        assert len(filas) >= 20

def test_scraper_invariante_margen_minimo():
    """Todas las ofertas deben cumplir con la Invariante II: Margen Bruto >= 35.0%."""
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for p in data["promociones"]:
        p_ofe = p["precio_oferta_ves"]
        c_dir = p["costo_directo_ves"]
        margen_calculado = ((p_ofe - c_dir) / p_ofe) * 100.0
        assert p["margen_pct"] >= 35.0, f"Oferta {p['id']} tiene margen {p['margen_pct']}% < 35.0%"
        assert abs(p["margen_pct"] - round(margen_calculado, 2)) < 0.01

def test_scraper_precio_menor_regular():
    """El precio de oferta debe ser estrictamente menor al precio regular."""
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for p in data["promociones"]:
        assert p["precio_oferta_ves"] < p["precio_regular_ves"], f"Fallo precio en {p['id']}"
        assert p["descuento_pct"] > 0.0

def test_scraper_grounding_wgs84_caracas():
    """Las coordenadas deben estar confinadas al área metropolitana de Caracas."""
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for p in data["promociones"]:
        lat = p["lat"]
        lon = p["lon"]
        assert 10.35 <= lat <= 10.55, f"Latitud fuera de Caracas: {lat} en {p['empresa']}"
        assert -67.05 <= lon <= -66.75, f"Longitud fuera de Caracas: {lon} en {p['empresa']}"

def test_scraper_areas_negocio_cobertura():
    """Debe cubrir las 6 áreas comerciales clave de Venezuela."""
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    codigos_presentes = {p["codigo_area"] for p in data["promociones"]}
    for area in AREAS_DE_NEGOCIO.keys():
        assert area in codigos_presentes, f"Área de negocio no cubierta: {area}"
