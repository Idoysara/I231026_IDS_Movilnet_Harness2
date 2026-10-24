"""
tests/test_caracas_40_superofertas_por_urbanizacion.py
======================================================
Valida que cada urbanización de cada alcaldía en Caracas cuente con
al menos 40 SuperOfertas activas en la base de datos local y cumpla
con el Invariante II de margen bruto (>=35%) y Stock positivo.
"""

import sqlite3
import pytest
from pathlib import Path

CLIENT_ROOT = Path(__file__).resolve().parent.parent / "services" / "cazador_ofertas"
DB_PATH = CLIENT_ROOT / "data" / "cazador_local.db"

URBANIZACIONES_ESPERADAS = [
    # Chacao (5)
    "Chacao", "Altamira", "Los Palos Grandes", "El Rosal", "Bello Campo / CCCT / Chuao",
    # Baruta (5)
    "Las Mercedes", "Colinas de Bello Monte", "La Trinidad", "El Cafetal / Santa Sofía", "Prados del Este / Santa Fe",
    # Sucre (5)
    "Los Dos Caminos / Millenium", "Boleíta / Los Ruices", "La California / CC Líder", "Sebucán / Los Chorros", "Terrazas del Ávila / El Marqués",
    # El Hatillo (4)
    "El Hatillo (Pueblo)", "Los Naranjos", "La Lagunita / Paseo El Hatillo", "La Boyera / El Cigarral",
    # Libertador (8)
    "Sabana Grande", "Plaza Venezuela", "La Candelaria", "Centro Histórico / El Silencio", "San Bernardino", "El Paraíso", "Montalbán / La Vega", "Catia (Pérez Bonalde)"
]

def test_base_de_datos_existe():
    assert DB_PATH.exists(), f"La base de datos no existe en {DB_PATH}"

def test_al_menos_40_superofertas_por_urbanizacion_caracas():
    """Verifica que cada una de las 27 urbanizaciones de Caracas tenga >= 40 ofertas activas con stock > 0."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for urb in URBANIZACIONES_ESPERADAS:
        query = """
            SELECT count(o.id)
            FROM ofertas o
            JOIN comercios c ON o.comercio_id = c.id
            WHERE c.zona_sector = ?
              AND o.activa = 1
              AND o.stock_disponible > 0
        """
        count = cur.execute(query, (urb,)).fetchone()[0]
        assert count >= 40, f"Fallo en urbanización {urb}: solo tiene {count} ofertas (esperadas >= 40)"

    conn.close()

def test_invariante_ii_margen_en_todas_las_ofertas_caracas():
    """Verifica que ninguna oferta de Caracas tenga margen menor al 35%."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = """
        SELECT o.id, o.titulo, o.precio_regular_ves, o.precio_oferta_ves, o.costo_directo_ves, o.margen_pct
        FROM ofertas o
        JOIN comercios c ON o.comercio_id = c.id
        WHERE c.zona_sector IN ({})
    """.format(",".join("?" for _ in URBANIZACIONES_ESPERADAS))

    rows = cur.execute(query, URBANIZACIONES_ESPERADAS).fetchall()
    assert len(rows) >= len(URBANIZACIONES_ESPERADAS) * 40

    for row in rows:
        ofe_id, titulo, p_reg, p_ofe, c_dir, marg_pct = row
        calc_margen = ((p_ofe - c_dir) / p_ofe) * 100.0
        assert calc_margen >= 35.0, f"Invariante II violada en {ofe_id} - {titulo}: {calc_margen:.2f}% < 35%"
        assert p_ofe < p_reg, f"Precio de oferta no menor al regular en {ofe_id}"

    conn.close()

def test_total_ofertas_caracas_supera_1000():
    """Verifica que el total agregado de ofertas de Caracas supere las 1.000 ofertas."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = """
        SELECT count(o.id)
        FROM ofertas o
        JOIN comercios c ON o.comercio_id = c.id
        WHERE c.zona_sector IN ({})
          AND o.activa = 1
          AND o.stock_disponible > 0
    """.format(",".join("?" for _ in URBANIZACIONES_ESPERADAS))

    total = cur.execute(query, URBANIZACIONES_ESPERADAS).fetchone()[0]
    assert total >= 1080, f"Total de ofertas ({total}) no alcanza la meta de 1.080"

    conn.close()
