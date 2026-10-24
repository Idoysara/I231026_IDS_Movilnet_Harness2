-- =============================================================================
-- ESQUEMA SQL DDL: TABLA DE INCIDENTES Y DESPACHO DE EMERGENCIA 911
-- Base de Datos: db/emergency_logs.db (SQLite WAL Mode / PostgreSQL Compatible)
-- Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
-- Gobernanza: Universal Best Practices Engineering Rule (Pilares I y III)
-- =============================================================================

PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS emergency_dispatch_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    msisdn TEXT NOT NULL,
    carrier_detected TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    maps_url TEXT,
    incident_description TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    dispatch_status TEXT CHECK(dispatch_status IN ('RECIBIDO', 'LOCALIZADO', 'DERIVADO_VEN911')) DEFAULT 'RECIBIDO'
);

-- Índices de consulta rápida en O(1) / O(log N) para soporte a CCO/VEN911
CREATE INDEX IF NOT EXISTS idx_emergency_msisdn ON emergency_dispatch_records(msisdn);
CREATE INDEX IF NOT EXISTS idx_emergency_status ON emergency_dispatch_records(dispatch_status);
CREATE INDEX IF NOT EXISTS idx_emergency_time ON emergency_dispatch_records(timestamp);
