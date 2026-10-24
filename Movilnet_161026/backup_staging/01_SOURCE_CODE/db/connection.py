"""
connection.py — Motor de Conectividad y Resiliencia de Base de Datos
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.

Arquitectura Dual:
1. Modo Producción: PostgreSQL 15 Enterprise Partitioned con pooling (PgBouncer 6432 / 5432).
2. Modo Resiliente / Local: SQLite Embedded con schema idéntico, soporte HMAC y latencia < 2ms.
"""

import os
import sys
import hmac
import hashlib
import sqlite3
import threading
from typing import Optional, Any, Generator
from contextlib import contextmanager
from pathlib import Path

# Configuración por variables de entorno
PG_HOST = os.getenv("PGHOST", "127.0.0.1")
PG_PORT = int(os.getenv("PGPORT", "5432"))
PG_DATABASE = os.getenv("PGDATABASE", "movilnet_db")
PG_USER = os.getenv("PGUSER", "movilnet_admin")
PG_PASSWORD = os.getenv("PGPASSWORD", "movilnet_secure_pass_2026")
BLIND_INDEX_SALT = os.getenv("BLIND_INDEX_SALT", "MOVILNET_SECRET_SALT_2026_PROD_F1").encode("utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_DB_PATH = PROJECT_ROOT / "db" / "local_movilnet.db"

_POSTGRES_AVAILABLE = False
_ENGINE_TYPE = "UNKNOWN"

# Verificación de disponibilidad de psycopg2
try:
    import psycopg2
    import psycopg2.pool
    import psycopg2.extras
    _PSYCOPG2_INSTALLED = True
except ImportError:
    _PSYCOPG2_INSTALLED = False


class DatabaseConnectionManager:
    """Gestor singleton de conexiones con conmutación por fallo automática (Failover)."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnectionManager, cls).__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self.engine_type = "RESILIENT_SQLITE"
        self.pg_pool = None
        
        if _PSYCOPG2_INSTALLED and os.getenv("FORCE_OFFLINE") != "true":
            try:
                # Intentar conexión rápida con timeout de 1.5s
                conn = psycopg2.connect(
                    host=PG_HOST,
                    port=PG_PORT,
                    dbname=PG_DATABASE,
                    user=PG_USER,
                    password=PG_PASSWORD,
                    connect_timeout=2
                )
                conn.close()
                self.pg_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=20,
                    host=PG_HOST,
                    port=PG_PORT,
                    dbname=PG_DATABASE,
                    user=PG_USER,
                    password=PG_PASSWORD
                )
                self.engine_type = "POSTGRESQL_15"
            except Exception:
                # En sandbox o entorno local sin Postgres activo, conmutar a Resilient SQLite
                self.engine_type = "RESILIENT_SQLITE"
        
        if self.engine_type == "RESILIENT_SQLITE":
            self._init_sqlite_schema()

    def _init_sqlite_schema(self):
        """Inicializa las 10 tablas equivalentes en SQLite local si no existen."""
        LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(LOCAL_DB_PATH))
        cur = conn.cursor()
        
        # 1. subscribers
        cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id TEXT PRIMARY KEY,
            blind_index_cid TEXT NOT NULL UNIQUE,
            customer_type TEXT NOT NULL DEFAULT 'NATURAL',
            status TEXT NOT NULL DEFAULT 'ACTIVO',
            segment TEXT NOT NULL DEFAULT 'PREPAGO_MASIVO',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        
        # 2. pii_vault
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pii_vault (
            id TEXT PRIMARY KEY,
            subscriber_id TEXT NOT NULL UNIQUE,
            encrypted_cid TEXT NOT NULL,
            encrypted_full_name TEXT NOT NULL,
            encrypted_email TEXT,
            encrypted_address TEXT,
            key_version TEXT NOT NULL DEFAULT 'v1',
            updated_at TEXT NOT NULL,
            FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE
        );
        """)
        
        # 3. product_plans
        cur.execute("""
        CREATE TABLE IF NOT EXISTS product_plans (
            plan_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            commercial_code TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT 'PREPAGO',
            data_quota_mb INTEGER NOT NULL DEFAULT 0,
            voice_minutes INTEGER NOT NULL DEFAULT 0,
            sms_quota INTEGER NOT NULL DEFAULT 0,
            price_usd REAL NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """)
        
        # 4. telco_lines
        cur.execute("""
        CREATE TABLE IF NOT EXISTS telco_lines (
            msisdn TEXT PRIMARY KEY,
            subscriber_id TEXT NOT NULL,
            imsi TEXT NOT NULL,
            iccid TEXT NOT NULL,
            imei TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            cell_id TEXT NOT NULL DEFAULT 'CAR-CCS-ENB-001',
            status TEXT NOT NULL DEFAULT 'ACTIVO',
            last_sim_swap_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (subscriber_id) REFERENCES subscribers(id),
            FOREIGN KEY (plan_id) REFERENCES product_plans(plan_id)
        );
        """)
        
        # 5. balances_and_quotas
        cur.execute("""
        CREATE TABLE IF NOT EXISTS balances_and_quotas (
            msisdn TEXT NOT NULL,
            id TEXT NOT NULL,
            balance_ves REAL NOT NULL DEFAULT 0.00,
            balance_usd_equiv REAL NOT NULL DEFAULT 0.00,
            remaining_data_mb INTEGER NOT NULL DEFAULT 0,
            total_quota_mb INTEGER NOT NULL DEFAULT 0,
            billing_cutoff_date TEXT NOT NULL,
            days_overdue INTEGER NOT NULL DEFAULT 0,
            last_sync_at TEXT NOT NULL,
            PRIMARY KEY (msisdn, id)
        );
        """)
        
        # 6. usage_records_cdr
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_records_cdr (
            event_timestamp TEXT NOT NULL,
            id TEXT NOT NULL,
            msisdn TEXT NOT NULL,
            event_type TEXT NOT NULL,
            data_volume_bytes INTEGER NOT NULL DEFAULT 0,
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            cell_id TEXT NOT NULL,
            status_code TEXT NOT NULL DEFAULT 'SUCCESS',
            PRIMARY KEY (event_timestamp, id)
        );
        """)
        
        # 7. banks_sudeban
        cur.execute("""
        CREATE TABLE IF NOT EXISTS banks_sudeban (
            bank_code TEXT PRIMARY KEY,
            bank_name TEXT NOT NULL,
            short_name TEXT NOT NULL,
            c2p_enabled INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        """)
        
        # 8. financial_transactions
        cur.execute("""
        CREATE TABLE IF NOT EXISTS financial_transactions (
            executed_at TEXT NOT NULL,
            reference_id TEXT NOT NULL,
            msisdn TEXT NOT NULL,
            bank_code TEXT NOT NULL,
            amount_ves REAL NOT NULL,
            amount_usd REAL NOT NULL,
            bcv_rate_applied REAL NOT NULL,
            payment_method TEXT NOT NULL DEFAULT 'PAGO_MOVIL_C2P',
            status TEXT NOT NULL DEFAULT 'COMPLETADO',
            payer_cid_masked TEXT NOT NULL,
            PRIMARY KEY (executed_at, reference_id),
            FOREIGN KEY (bank_code) REFERENCES banks_sudeban(bank_code)
        );
        """)
        
        # 9. churn_metrics
        cur.execute("""
        CREATE TABLE IF NOT EXISTS churn_metrics (
            id TEXT PRIMARY KEY,
            msisdn TEXT NOT NULL,
            churn_score REAL NOT NULL,
            risk_segment TEXT NOT NULL,
            days_without_recharge INTEGER NOT NULL DEFAULT 0,
            complaints_count_30d INTEGER NOT NULL DEFAULT 0,
            data_drop_pct REAL NOT NULL DEFAULT 0.00,
            recommended_action TEXT NOT NULL DEFAULT 'NO_ACTION',
            coupon_code_offered TEXT,
            evaluated_at TEXT NOT NULL
        );
        """)
        
        # 10. eir_security_events
        cur.execute("""
        CREATE TABLE IF NOT EXISTS eir_security_events (
            ticket_id TEXT PRIMARY KEY,
            msisdn TEXT NOT NULL,
            imei TEXT NOT NULL,
            imsi TEXT NOT NULL,
            event_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            reporting_agent TEXT NOT NULL DEFAULT 'ANTIGRAVITY_MCP_AGENT',
            police_report_number TEXT,
            created_at TEXT NOT NULL
        );
        """)
        
        # Índices de Alto Rendimiento en SQLite
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sub_blind ON subscribers(blind_index_cid);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_telco_sub ON telco_lines(subscriber_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ft_ref ON financial_transactions(reference_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cdr_msisdn ON usage_records_cdr(msisdn);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_churn_msisdn ON churn_metrics(msisdn);")
        
        # Sembrado inicial de bancos y planes si están vacíos
        cur.execute("SELECT COUNT(*) FROM banks_sudeban")
        if cur.fetchone()[0] == 0:
            banks = [
                ('0102', 'Banco de Venezuela, S.A. Banco Universal', 'Banco de Venezuela', 1, 1),
                ('0104', 'Venezolano de Crédito, S.A. Banco Universal', 'Venezolano de Crédito', 1, 1),
                ('0105', 'Banco Mercantil, C.A. Banco Universal', 'Banco Mercantil', 1, 1),
                ('0108', 'Banco Provincial, S.A. Banco Universal', 'BBVA Provincial', 1, 1),
                ('0114', 'Bancaribe, C.A. Banco Universal', 'Bancaribe', 1, 1),
                ('0115', 'Banco Exterior, C.A. Banco Universal', 'Banco Exterior', 1, 1),
                ('0128', 'Banco Caroní, C.A. Banco Universal', 'Banco Caroní', 1, 1),
                ('0134', 'Banesco Banco Universal, C.A.', 'Banesco', 1, 1),
                ('0137', 'Banco Sofitasa Banco Universal, C.A.', 'Banco Sofitasa', 1, 1),
                ('0138', 'Banco Plaza, C.A. Banco Universal', 'Banco Plaza', 1, 1),
                ('0151', 'BFC Banco Fondo Común, C.A. Banco Universal', 'Banco Fondo Común', 1, 1),
                ('0156', '100% Banco, Banco Universal, C.A.', '100% Banco', 1, 1),
                ('0157', 'DelSur Banco Universal, C.A.', 'DelSur', 1, 1),
                ('0163', 'Banco del Tesoro, C.A. Banco Universal', 'Banco del Tesoro', 1, 1),
                ('0166', 'Banco Agrícola de Venezuela, C.A.', 'Banco Agrícola', 1, 1),
                ('0168', 'Bancrecer, S.A. Banco Microfinanciero', 'Bancrecer', 1, 1),
                ('0169', 'Mi Banco, Banco Microfinanciero, C.A.', 'Mi Banco', 1, 1),
                ('0171', 'Banco Activo, C.A. Banco Universal', 'Banco Activo', 1, 1),
                ('0172', 'Bancamiga Banco Universal, C.A.', 'Bancamiga', 1, 1),
                ('0174', 'Banplus Banco Universal, C.A.', 'Banplus', 1, 1),
                ('0175', 'Banco Bicentenario del Pueblo, Banco Universal C.A.', 'Banco Bicentenario', 1, 1),
                ('0177', 'Banco de la Fuerza Armada Nacional Bolivariana (BANFANB)', 'BANFANB', 1, 1),
                ('0191', 'Banco Nacional de Crédito, C.A. Banco Universal (BNC)', 'BNC', 1, 1)
            ]
            cur.executemany("INSERT INTO banks_sudeban VALUES (?, ?, ?, ?, ?)", banks)
            
        cur.execute("SELECT COUNT(*) FROM product_plans")
        if cur.fetchone()[0] == 0:
            plans = [
                ('PLAN_10GB_4GMAX', 'Inteliplan 10GB 4GMAX', 'MOV-INT-10G', 'PREPAGO', 10240, 500, 1000, 7.50, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_20GB_4GMAX', 'Inteliplan 20GB 4GMAX', 'MOV-INT-20G', 'PREPAGO', 20480, 1000, 2000, 12.00, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_5GB_BASICO', 'Plan Básico Conecta 5GB', 'MOV-CON-05G', 'PREPAGO', 5120, 250, 500, 4.00, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_3GB_LIGERO', 'Plan Ligero 3GB', 'MOV-LIG-03G', 'PREPAGO', 3072, 150, 300, 2.50, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_1GB_SOCIAL', 'Plan Social Conectividad', 'MOV-SOC-01G', 'PREPAGO', 1024, 100, 200, 1.00, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_50GB_CORP', 'Corporativo 4GMAX Ilimitado 50GB', 'MOV-CORP-50G', 'CORPORATIVO', 51200, 3000, 5000, 28.00, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_100GB_CORP', 'Corporativo Ultra 100GB', 'MOV-CORP-100G', 'CORPORATIVO', 102400, 6000, 10000, 45.00, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_POSPAGO_PLUS', 'Movilnet Pospago Conecta Plus', 'MOV-POS-PLUS', 'POSPAGO', 15360, 800, 1500, 10.50, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_POSPAGO_ELITE', 'Movilnet Pospago Élite 30GB', 'MOV-POS-ELIT', 'POSPAGO', 30720, 1500, 3000, 18.00, 1, '2026-09-30 00:00:00+00'),
                ('PACK_EXTRA_2GB', 'Extra Datos 2GB 4GMAX', 'MOV-EXT-02G', 'EXTRA_DATOS', 2048, 0, 0, 1.80, 1, '2026-09-30 00:00:00+00'),
                ('PACK_EXTRA_5GB', 'Extra Datos 5GB 4GMAX', 'MOV-EXT-05G', 'EXTRA_DATOS', 5120, 0, 0, 3.80, 1, '2026-09-30 00:00:00+00'),
                ('PACK_EXTRA_10GB', 'Extra Datos 10GB 4GMAX', 'MOV-EXT-10G', 'EXTRA_DATOS', 10240, 0, 0, 6.50, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_JUBILADO_PATRIA', 'Plan Solidario Patria Jubilados', 'MOV-JUB-PAT', 'PREPAGO', 2048, 300, 500, 0.50, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_ESTUDIANTE_CONECTA', 'Estudiante Conecta 4G', 'MOV-EST-CON', 'PREPAGO', 4096, 200, 400, 2.00, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_ROAMING_LATAM', 'Roaming Movilnet Andino/Latam', 'MOV-ROAM-LAT', 'EXTRA_DATOS', 3072, 60, 60, 15.00, 1, '2026-09-30 00:00:00+00'),
                ('PLAN_M2M_TELEMETRIA', 'Telemetría IoT M2M Industrial', 'MOV-IOT-M2M', 'CORPORATIVO', 512, 10, 50, 0.80, 1, '2026-09-30 00:00:00+00')
            ]
            cur.executemany("INSERT INTO product_plans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", plans)
            
        conn.commit()
        conn.close()

    @contextmanager
    def get_cursor(self) -> Generator[Any, None, None]:
        """Context manager unificado que entrega un cursor dict-like independiente del motor."""
        if self.engine_type == "POSTGRESQL_15" and self.pg_pool:
            conn = self.pg_pool.getconn()
            try:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                self.pg_pool.putconn(conn)
        else:
            # SQLite Resiliente con Reutilización de Conexión (High Performance Pooling & Thread Safety)
            if not hasattr(self, "_sqlite_conn") or self._sqlite_conn is None:
                self._sqlite_conn = sqlite3.connect(str(LOCAL_DB_PATH), check_same_thread=False, timeout=30.0)
                self._sqlite_conn.row_factory = sqlite3.Row
                self._sqlite_lock = threading.RLock()
            lock = getattr(self, "_sqlite_lock", None)
            if lock is None:
                lock = threading.RLock()
                self._sqlite_lock = lock
            with lock:
                try:
                    cur = self._sqlite_conn.cursor()
                    yield cur
                    if getattr(self._sqlite_conn, "in_transaction", False):
                        self._sqlite_conn.commit()
                except Exception:
                    if getattr(self._sqlite_conn, "in_transaction", False):
                        self._sqlite_conn.rollback()
                    raise


def compute_blind_index(cid: str) -> str:
    """Calcula el índice ciego determinista HMAC-SHA256 para búsquedas O(1) de Cédula."""
    clean = cid.upper().replace(" ", "").replace("-", "").replace(".", "").strip()
    return hmac.new(BLIND_INDEX_SALT, clean.encode("utf-8"), hashlib.sha256).hexdigest()
