#!/usr/bin/env python3
"""
Herramienta Autónoma de Migración DDL y Carga Semilla B2C.
Proyecto: Cliente 28 — Cazador de Ofertas Movilnet.
Cumple con el Pilar II (Universal Best Practices: Ejecución Autónoma y Auto-Test).
"""
import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path

# Configurar path para alcanzar módulos del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[6]
CLIENT_ROOT = Path(__file__).resolve().parents[4]

for p in (str(PROJECT_ROOT), str(CLIENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.infrastructure.persistence.database import init_db, SessionFactory, DEFAULT_DB_PATH
from src.infrastructure.persistence.models import (
    ComercioModel, OfertaModel, CuponModel, TransaccionBillingModel, BovedaHashesQuemadosModel
)

SEED_JSON_PATH = os.path.join(CLIENT_ROOT, "data", "seed_data.json")

def ejecutar_migracion_sqlite(db_path: str = DEFAULT_DB_PATH) -> bool:
    """Ejecuta el script SQL DDL directamente sobre SQLite."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    ddl_file = os.path.join(os.path.dirname(__file__), "schema_sqlite.sql")
    
    with open(ddl_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql_content)
        conn.commit()
        return True
    finally:
        conn.close()

def sembrar_datos_auditados(db_session=None) -> int:
    """Carga los comercios y ofertas del seed JSON auditado en la base de datos."""
    session = db_session or SessionFactory()
    close_at_end = db_session is None

    try:
        if not os.path.exists(SEED_JSON_PATH):
            raise FileNotFoundError(f"Archivo semilla no encontrado en: {SEED_JSON_PATH}")

        with open(SEED_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        total_insertados = 0

        # Comercios
        for c in data.get("comercios", []):
            existente = session.query(ComercioModel).filter_by(id=c["id"]).first()
            if not existente:
                comercio = ComercioModel(
                    id=c["id"],
                    rif=c["rif"],
                    nombre=c["nombre"],
                    categoria=c["categoria"],
                    lat=c["lat"],
                    lon=c["lon"],
                    tier=c.get("tier", "BASICO"),
                    activo=c.get("activo", True)
                )
                session.add(comercio)
                total_insertados += 1
            else:
                existente.nombre = c["nombre"]
                existente.rif = c["rif"]
                existente.categoria = c["categoria"]
                existente.lat = c["lat"]
                existente.lon = c["lon"]
                existente.tier = c.get("tier", "BASICO")
                existente.activo = c.get("activo", True)

        session.commit()

        # Ofertas
        for o in data.get("ofertas", []):
            existente = session.query(OfertaModel).filter_by(id=o["id"]).first()
            margen = ((o["precio_oferta_ves"] - o["costo_directo_ves"]) / o["precio_oferta_ves"]) * 100.0
            if not existente:
                oferta = OfertaModel(
                    id=o["id"],
                    comercio_id=o["comercio_id"],
                    titulo=o["titulo"],
                    precio_regular_ves=o["precio_regular_ves"],
                    precio_oferta_ves=o["precio_oferta_ves"],
                    costo_directo_ves=o["costo_directo_ves"],
                    descuento_pct=o.get("descuento_pct", 0.0),
                    margen_pct=round(margen, 2),
                    stock_disponible=o.get("stock_disponible", 10),
                    horario_validez=o.get("horario_validez", "10:00 - 20:00"),
                    activa=o.get("activa", True)
                )
                session.add(oferta)
                total_insertados += 1
            else:
                existente.comercio_id = o["comercio_id"]
                existente.titulo = o["titulo"]
                existente.precio_regular_ves = o["precio_regular_ves"]
                existente.precio_oferta_ves = o["precio_oferta_ves"]
                existente.costo_directo_ves = o["costo_directo_ves"]
                existente.descuento_pct = o.get("descuento_pct", 0.0)
                existente.margen_pct = round(margen, 2)
                existente.stock_disponible = o.get("stock_disponible", 10)
                existente.horario_validez = o.get("horario_validez", "10:00 - 20:00")
                existente.activa = o.get("activa", True)

        session.commit()
        return total_insertados
    finally:
        if close_at_end:
            session.close()

def obtener_estadisticas_db() -> dict:
    """Retorna conteos de registros de todas las tablas de persistencia."""
    session = SessionFactory()
    try:
        return {
            "comercios": session.query(ComercioModel).count(),
            "ofertas": session.query(OfertaModel).count(),
            "cupones": session.query(CuponModel).count(),
            "transacciones_billing": session.query(TransaccionBillingModel).count(),
            "hashes_quemados": session.query(BovedaHashesQuemadosModel).count()
        }
    finally:
        session.close()

def run_self_tests() -> None:
    """Auto-verificación matemática y estructural con aserciones."""
    print("🧪 Ejecutando auto-test de migración y persistencia...")
    test_db = os.path.join(CLIENT_ROOT, "data", "test_migration.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    # 1. Test DDL
    assert ejecutar_migracion_sqlite(test_db) is True, "Fallo al ejecutar DDL en SQLite"

    # 2. Test Tablas creadas
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tablas = {r[0] for r in cursor.fetchall()}
    conn.close()

    tablas_esperadas = {"comercios", "ofertas", "cupones", "transacciones_billing", "boveda_hashes_quemados"}
    assert tablas_esperadas.issubset(tablas), f"Faltan tablas esperadas: {tablas_esperadas - tablas}"

    # Limpieza
    if os.path.exists(test_db):
        os.remove(test_db)

    print("✅ Auto-test de migración DDL superado con éxito (0 fallos).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gestor de Migraciones DDL — Cazador de Ofertas Movilnet")
    parser.add_argument("--init", action="store_true", help="Crea todas las tablas en la base de datos local")
    parser.add_argument("--seed", action="store_true", help="Carga datos semilla auditados en la base de datos")
    parser.add_argument("--stats", action="store_true", help="Muestra estadísticas de registros en base de datos")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación formal del script")

    args = parser.parse_args()

    if args.test:
        run_self_tests()
    elif args.init:
        print(f"📦 Inicializando base de datos en: {DEFAULT_DB_PATH}")
        init_db()
        print("✅ Tablas creadas exitosamente.")
        if args.seed:
            print("🌱 Sembrando datos auditados...")
            n = sembrar_datos_auditados()
            print(f"✅ {n} registros insertados.")
    elif args.seed:
        print("🌱 Sembrando datos auditados...")
        n = sembrar_datos_auditados()
        print(f"✅ {n} registros insertados.")
    elif args.stats:
        stats = obtener_estadisticas_db()
        print("📊 Estadísticas de Base de Datos:")
        for tabla, cantidad in stats.items():
            print(f"  • {tabla}: {cantidad} registros")
    else:
        parser.print_help()
