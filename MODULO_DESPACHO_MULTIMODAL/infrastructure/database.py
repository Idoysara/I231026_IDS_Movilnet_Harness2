"""
Módulo Autónomo de Despacho Multimodal — Capa de Infraestructura: Base de Datos SQLite WAL
Gobernanza: Universal Best Practices Engineering Rule (Pilar IV: Resiliencia)
"""

import os
import sqlite3
from typing import Generator
from contextlib import contextmanager

DEFAULT_DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "multimodal_vault.db")


def get_multimodal_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Crea una conexión de alto rendimiento a SQLite con Write-Ahead Logging (WAL).
    """
    path = db_path or os.environ.get("MULTIMODAL_DB_PATH", DEFAULT_DB_FILE)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    
    conn = sqlite3.connect(path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # Pragma tuning para Carrier-Grade Telco
    with conn:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        
    return conn


@contextmanager
def db_session(db_path: str = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager para operaciones transaccionales seguras."""
    conn = get_multimodal_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_multimodal_tables(conn: sqlite3.Connection) -> None:
    """Inicializa el esquema DDL si las tablas no existen."""
    schema = """
    CREATE TABLE IF NOT EXISTS user_multimodal_vault (
        vault_id TEXT PRIMARY KEY,
        msisdn_hash TEXT NOT NULL UNIQUE,
        phone_display TEXT NOT NULL,
        vault_directory TEXT NOT NULL,
        quota_limit_bytes INTEGER NOT NULL DEFAULT 52428800,
        quota_used_bytes INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_interaction TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_vault_msisdn_hash ON user_multimodal_vault(msisdn_hash);
    CREATE INDEX IF NOT EXISTS idx_vault_status ON user_multimodal_vault(status);

    CREATE TABLE IF NOT EXISTS multimodal_media_asset (
        asset_id TEXT PRIMARY KEY,
        vault_id TEXT NOT NULL,
        direction TEXT NOT NULL,
        media_type TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        stored_filename TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL,
        sha256_checksum TEXT NOT NULL,
        file_rel_path TEXT NOT NULL,
        processing_status TEXT NOT NULL DEFAULT 'PENDING',
        transcription_text TEXT,
        analysis_metadata TEXT,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (vault_id) REFERENCES user_multimodal_vault(vault_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_asset_vault_id ON multimodal_media_asset(vault_id);
    CREATE INDEX IF NOT EXISTS idx_asset_checksum ON multimodal_media_asset(sha256_checksum);
    CREATE INDEX IF NOT EXISTS idx_asset_expires_at ON multimodal_media_asset(expires_at);

    CREATE TABLE IF NOT EXISTS multimodal_session_transcripts (
        session_id TEXT PRIMARY KEY,
        vault_id TEXT NOT NULL,
        channel TEXT NOT NULL DEFAULT 'WHATSAPP',
        input_asset_id TEXT,
        recognized_intent TEXT,
        agent_response_text TEXT NOT NULL,
        output_asset_id TEXT,
        latency_ms REAL NOT NULL DEFAULT 0.0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (vault_id) REFERENCES user_multimodal_vault(vault_id) ON DELETE CASCADE,
        FOREIGN KEY (input_asset_id) REFERENCES multimodal_media_asset(asset_id),
        FOREIGN KEY (output_asset_id) REFERENCES multimodal_media_asset(asset_id)
    );

    CREATE INDEX IF NOT EXISTS idx_session_vault ON multimodal_session_transcripts(vault_id);
    """
    with conn:
        conn.executescript(schema)
