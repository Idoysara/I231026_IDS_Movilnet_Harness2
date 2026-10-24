-- ============================================================================
-- DDL MIGRATION SCRIPT — POSTGRESQL 16 + POSTGIS
-- Proyecto: Cliente 28 — Cazador de Ofertas Movilnet (IDS_CORE)
-- Sello de Arquitectura: CERT-CAZADOR-PENTARCHY-20261018-SHA256
-- ============================================================================

-- 1. Habilitar extensión geoespacial PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Tabla de Comercios Aliados (Directorio Físico)
CREATE TABLE IF NOT EXISTS comercios (
    id VARCHAR(36) PRIMARY KEY,
    rif VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,
    categoria VARCHAR(60) NOT NULL,
    lat DOUBLE PRECISION NOT NULL CHECK (lat >= -90.0 AND lat <= 90.0),
    lon DOUBLE PRECISION NOT NULL CHECK (lon >= -180.0 AND lon <= 180.0),
    geom GEOMETRY(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)) STORED,
    tier VARCHAR(20) NOT NULL DEFAULT 'BASICO',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);

-- Índices sobre comercios
CREATE INDEX IF NOT EXISTS idx_comercios_geom ON comercios USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_comercios_rif ON comercios (rif);
CREATE INDEX IF NOT EXISTS idx_comercios_categoria ON comercios (categoria);
CREATE INDEX IF NOT EXISTS idx_comercios_lat_lon ON comercios (lat, lon);

-- 3. Tabla de Ofertas y Promociones (Catálogo y Control de Stock)
CREATE TABLE IF NOT EXISTS ofertas (
    id VARCHAR(36) PRIMARY KEY,
    comercio_id VARCHAR(36) NOT NULL REFERENCES comercios(id) ON DELETE CASCADE,
    titulo VARCHAR(140) NOT NULL,
    precio_regular_ves DOUBLE PRECISION NOT NULL CHECK (precio_regular_ves > 0),
    precio_oferta_ves DOUBLE PRECISION NOT NULL CHECK (precio_oferta_ves > 0),
    costo_directo_ves DOUBLE PRECISION NOT NULL CHECK (costo_directo_ves >= 0),
    descuento_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    margen_pct DOUBLE PRECISION NOT NULL,
    stock_disponible INTEGER NOT NULL DEFAULT 10 CHECK (stock_disponible >= 0),
    horario_validez VARCHAR(60) NOT NULL DEFAULT '10:00 - 20:00',
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL,
    
    -- Invariante II y Guardas de Negocio
    CONSTRAINT chk_precio_menor_regular CHECK (precio_oferta_ves < precio_regular_ves),
    CONSTRAINT chk_invariante_margen_minimo CHECK (margen_pct >= 35.0)
);

-- Índices sobre ofertas
CREATE INDEX IF NOT EXISTS idx_ofertas_comercio ON ofertas (comercio_id);
CREATE INDEX IF NOT EXISTS idx_ofertas_activa ON ofertas (activa);
CREATE INDEX IF NOT EXISTS idx_ofertas_comercio_activa ON ofertas (comercio_id, activa);

-- 4. Tabla de Cupones Emitidos (FSM de Cuponería y Código Dinámico TOTP)
CREATE TABLE IF NOT EXISTS cupones (
    uuid VARCHAR(36) PRIMARY KEY,
    oferta_id VARCHAR(36) NOT NULL REFERENCES ofertas(id) ON DELETE RESTRICT,
    comercio_id VARCHAR(36) NOT NULL REFERENCES comercios(id) ON DELETE RESTRICT,
    usuario_msisdn VARCHAR(20) NOT NULL,
    codigo_dinamico VARCHAR(30) NOT NULL,
    firma_hmac VARCHAR(32) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'EMITIDO',
    time_step_emision INTEGER NOT NULL,
    canjeado_en DOUBLE PRECISION,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);

-- Índices sobre cupones
CREATE INDEX IF NOT EXISTS idx_cupones_usuario_msisdn ON cupones (usuario_msisdn);
CREATE INDEX IF NOT EXISTS idx_cupones_estado ON cupones (estado);
CREATE INDEX IF NOT EXISTS idx_cupones_usuario_estado ON cupones (usuario_msisdn, estado);
CREATE INDEX IF NOT EXISTS idx_cupones_comercio ON cupones (comercio_id);

-- 5. Tabla de Transacciones de Carrier Billing (Idempotencia y Split 20/80)
CREATE TABLE IF NOT EXISTS transacciones_billing (
    id VARCHAR(36) PRIMARY KEY,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    msisdn VARCHAR(20) NOT NULL,
    monto_ves DOUBLE PRECISION NOT NULL CHECK (monto_ves > 0),
    comision_telco_ves DOUBLE PRECISION NOT NULL CHECK (comision_telco_ves >= 0),
    neto_comercio_ves DOUBLE PRECISION NOT NULL CHECK (neto_comercio_ves >= 0),
    estatus VARCHAR(20) NOT NULL DEFAULT 'PROCESADO',
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);

-- Índices sobre facturación
CREATE INDEX IF NOT EXISTS idx_billing_idempotency ON transacciones_billing (idempotency_key);
CREATE INDEX IF NOT EXISTS idx_billing_msisdn ON transacciones_billing (msisdn);
CREATE INDEX IF NOT EXISTS idx_billing_msisdn_created ON transacciones_billing (msisdn, created_at);

-- 6. Tabla de Bóveda de Hashes Quemados (Anti-Replay / Anti-Doble Gasto)
CREATE TABLE IF NOT EXISTS boveda_hashes_quemados (
    fingerprint VARCHAR(64) PRIMARY KEY,
    cupon_uuid VARCHAR(36) NOT NULL,
    comercio_id VARCHAR(36) NOT NULL,
    quemado_en DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_boveda_cupon_comercio ON boveda_hashes_quemados (cupon_uuid, comercio_id);
