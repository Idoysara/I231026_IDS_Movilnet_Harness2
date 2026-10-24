"""
Módulo Autónomo de Despacho Multimodal — Script de Inicialización de Base de Datos
Gobernanza: Universal Best Practices Engineering Rule (Pilar II: Autonomía de Módulos)
"""

import argparse
import os
import sys

# Agregar raíz del módulo al path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from infrastructure.database import get_multimodal_connection, init_multimodal_tables
from infrastructure.repository import MultimodalRepository


def init_database(db_path: str = None) -> bool:
    """Inicializa el esquema DDL y valida las tablas."""
    conn = get_multimodal_connection(db_path)
    init_multimodal_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    conn.close()

    expected = ["user_multimodal_vault", "multimodal_media_asset", "multimodal_session_transcripts"]
    all_present = all(t in tables for t in expected)
    return all_present


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicializador DDL de Base de Datos Multimodal")
    parser.add_argument("--db-path", type=str, default=None, help="Ruta de SQLite WAL")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación formal con aserciones")
    args = parser.parse_args()

    if args.test:
        test_db = ":memory:"
        ok = init_database(test_db)
        assert ok is True, "Error en inicialización DDL en memoria"
        print("✅ [init_multimodal_db] Auto-verificación de tablas DDL: 100% PASS.")
    else:
        success = init_database(args.db_path)
        if success:
            print(f"✅ Base de datos inicializada exitosamente en: {args.db_path or 'multimodal_vault.db'}")
        else:
            print("❌ Error al crear tablas DDL.")
            sys.exit(1)
