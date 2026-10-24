-- ============================================================================
-- DDL MIGRATION SCRIPT — SQLITE 3 (LOCAL OFFLINE-FIRST)
-- Proyecto: Cliente 28 — Cazador de Ofertas Movilnet (IDS_CORE)
-- ============================================================================

-- 1. Tabla de Comercios Aliados
CREATE TABLE IF NOT EXISTS comercios (
    id TEXT PRIMARY KEY,
    rif TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    tier TEXT NOT NULL DEFAULT 'BASICO',
    activo INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_comercios_rif ON comercios (rif);
CREATE INDEX IF NOT EXISTS idx_comercios_categoria ON comercios (categoria);
CREATE INDEX IF NOT EXISTS idx_comercios_lat_lon ON comercios (lat, lon);

-- 2. Tabla de Ofertas y Promociones
CREATE TABLE IF NOT EXISTS ofertas (
    id TEXT PRIMARY KEY,
    comercio_id TEXT NOT NULL REFERENCES comercios(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    precio_regular_ves REAL NOT NULL,
    precio_oferta_ves REAL NOT NULL,
    costo_directo_ves REAL NOT NULL,
    descuento_pct REAL NOT NULL DEFAULT 0.0,
    margen_pct REAL NOT NULL,
    stock_disponible INTEGER NOT NULL DEFAULT 10,
    horario_validez TEXT NOT NULL DEFAULT '10:00 - 20:00',
    activa INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    
    CHECK (precio_oferta_ves < precio_regular_ves),
    CHECK (margen_pct >= 35.0),
    CHECK (stock_disponible >= 0)
);

CREATE INDEX IF NOT EXISTS idx_ofertas_comercio ON ofertas (comercio_id);
CREATE INDEX IF NOT EXISTS idx_ofertas_activa ON ofertas (activa);
CREATE INDEX IF NOT EXISTS idx_ofertas_comercio_activa ON ofertas (comercio_id, activa);

-- 3. Tabla de Cupones Emitidos
CREATE TABLE IF NOT EXISTS cupones (
    uuid TEXT PRIMARY KEY,
    oferta_id TEXT NOT NULL REFERENCES ofertas(id),
    comercio_id TEXT NOT NULL REFERENCES comercios(id),
    usuario_msisdn TEXT NOT NULL,
    codigo_dinamico TEXT NOT NULL,
    firma_hmac TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'EMITIDO',
    time_step_emision INTEGER NOT NULL,
    canjeado_en REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cupones_usuario_msisdn ON cupones (usuario_msisdn);
CREATE INDEX IF NOT EXISTS idx_cupones_estado ON cupones (estado);
CREATE INDEX IF NOT EXISTS idx_cupones_usuario_estado ON cupones (usuario_msisdn, estado);

-- 4. Tabla de Transacciones de Carrier Billing
CREATE TABLE IF NOT EXISTS transacciones_billing (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    msisdn TEXT NOT NULL,
    monto_ves REAL NOT NULL,
    comision_telco_ves REAL NOT NULL,
    neto_comercio_ves REAL NOT NULL,
    estatus TEXT NOT NULL DEFAULT 'PROCESADO',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,

    CHECK (monto_ves > 0)
);

CREATE INDEX IF NOT EXISTS idx_billing_idempotency ON transacciones_billing (idempotency_key);
CREATE INDEX IF NOT EXISTS idx_billing_msisdn ON transacciones_billing (msisdn);

-- 5. Tabla de Bóveda de Hashes Quemados (Anti-Replay)
CREATE TABLE IF NOT EXISTS boveda_hashes_quemados (
    fingerprint TEXT PRIMARY KEY,
    cupon_uuid TEXT NOT NULL,
    comercio_id TEXT NOT NULL,
    quemado_en REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_boveda_cupon_comercio ON boveda_hashes_quemados (cupon_uuid, comercio_id);
