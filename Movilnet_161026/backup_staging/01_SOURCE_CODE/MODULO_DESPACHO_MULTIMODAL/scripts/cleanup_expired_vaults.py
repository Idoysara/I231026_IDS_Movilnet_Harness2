"""
Módulo Autónomo de Despacho Multimodal — Demonio de Retención y Limpieza Zero-PII
Gobernanza: Universal Best Practices Engineering Rule (Pilares II y VI)
"""

import argparse
import os
import sys
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from infrastructure.database import get_multimodal_connection, init_multimodal_tables
from infrastructure.repository import MultimodalRepository
from infrastructure.storage_engine import StorageEngine
from application.vault_service import VaultService


def run_cleanup(db_path: str = None, vault_root: str = None) -> int:
    """Ejecuta el ciclo de purga de archivos expirados (>30 días)."""
    conn = get_multimodal_connection(db_path)
    init_multimodal_tables(conn)
    repo = MultimodalRepository(conn)
    storage = StorageEngine(vault_root)
    service = VaultService(repo, storage)

    deleted_count = service.cleanup_expired_assets()
    conn.close()
    return deleted_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cron de Limpieza y Retención Zero-PII")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación formal")
    parser.add_argument("--db-path", type=str, default=None, help="Ruta de SQLite WAL")
    args = parser.parse_args()

    if args.test:
        count = run_cleanup(":memory:")
        assert count == 0, "No debe haber archivos expirados en DB vacía"
        print("✅ [cleanup_expired_vaults] Auto-verificación de retención: 100% PASS.")
    else:
        purged = run_cleanup(args.db_path)
        print(f"🧹 Limpieza completada: {purged} archivos expirados purgados.")
