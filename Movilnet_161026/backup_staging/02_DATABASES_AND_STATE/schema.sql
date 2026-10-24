-- ============================================================================
-- 📜 DDL MAESTRO DE PERSISTENCIA Y MODELO DE DATOS — FASE 1
-- Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
-- Motor: PostgreSQL 15 Enterprise Partitioned (Conforme TM Forum ODA / Zero-Cost)
-- Particionamiento: Hash (8 Shards) + Range Mensual + Índices BRIN + Criptografía
-- ============================================================================

-- 1. Extensiones Criptográficas e Identificadores Universales
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Limpieza Segura (Idempotente)
-- (Orden inverso de dependencias para evitar violaciones de clave foránea)
DROP TABLE IF EXISTS usage_records_cdr CASCADE;
DROP TABLE IF EXISTS financial_transactions CASCADE;
DROP TABLE IF EXISTS balances_and_quotas CASCADE;
DROP TABLE IF EXISTS churn_metrics CASCADE;
DROP TABLE IF EXISTS eir_security_events CASCADE;
DROP TABLE IF EXISTS telco_lines CASCADE;
DROP TABLE IF EXISTS product_plans CASCADE;
DROP TABLE IF EXISTS pii_vault CASCADE;
DROP TABLE IF EXISTS subscribers CASCADE;
DROP TABLE IF EXISTS banks_sudeban CASCADE;

-- ============================================================================
-- MÓDULO 1: IDENTIDAD, PARTIES Y PRIVACIDAD ZERO-KNOWLEDGE (TMF632)
-- ============================================================================

-- Tabla 1: subscribers (Abonados Legales sin PII en claro)
CREATE TABLE subscribers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blind_index_cid VARCHAR(64) NOT NULL UNIQUE,
    customer_type VARCHAR(20) NOT NULL DEFAULT 'NATURAL' 
        CHECK (customer_type IN ('NATURAL', 'JURIDICO', 'GOBIERNO', 'EMPLEADO')),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVO' 
        CHECK (status IN ('ACTIVO', 'SUSPENDIDO', 'INACTIVO', 'EN_MORA')),
    segment VARCHAR(30) NOT NULL DEFAULT 'PREPAGO_MASIVO' 
        CHECK (segment IN ('PREPAGO_MASIVO', 'POSPAGO_CONECTA', 'CORPORATIVO_4GMAX', 'JUBILADO')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscribers_blind_cid ON subscribers (blind_index_cid);
CREATE INDEX idx_subscribers_status ON subscribers (status);

-- Tabla 2: pii_vault (Bóveda Segura Cifrada AES-256-GCM - Aislada de n8n)
CREATE TABLE pii_vault (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscriber_id UUID NOT NULL UNIQUE REFERENCES subscribers(id) ON DELETE CASCADE,
    encrypted_cid TEXT NOT NULL,
    encrypted_full_name TEXT NOT NULL,
    encrypted_email TEXT,
    encrypted_address TEXT,
    key_version VARCHAR(10) NOT NULL DEFAULT 'v1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- MÓDULO 2: INVENTARIO, CATÁLOGO Y LÍNEAS MÓVILES (TMF620 / TMF622)
-- ============================================================================

-- Tabla 3: product_plans (Catálogo Comercial de 16 Planes Homologados)
CREATE TABLE product_plans (
    plan_id VARCHAR(30) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    commercial_code VARCHAR(20) NOT NULL UNIQUE,
    category VARCHAR(20) NOT NULL DEFAULT 'PREPAGO' 
        CHECK (category IN ('PREPAGO', 'POSPAGO', 'EXTRA_DATOS', 'CORPORATIVO')),
    data_quota_mb INTEGER NOT NULL DEFAULT 0,
    voice_minutes INTEGER NOT NULL DEFAULT 0,
    sms_quota INTEGER NOT NULL DEFAULT 0,
    price_usd NUMERIC(8,2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla 4: telco_lines (Particionada por Hash de MSISDN - 8 Shards Físicos)
CREATE TABLE telco_lines (
    msisdn VARCHAR(15) NOT NULL,
    subscriber_id UUID NOT NULL,
    imsi VARCHAR(20) NOT NULL,
    iccid VARCHAR(22) NOT NULL,
    imei VARCHAR(18) NOT NULL,
    plan_id VARCHAR(30) NOT NULL REFERENCES product_plans(plan_id),
    cell_id VARCHAR(30) NOT NULL DEFAULT 'CAR-CCS-ENB-001',
    status VARCHAR(25) NOT NULL DEFAULT 'ACTIVO' 
        CHECK (status IN ('ACTIVO', 'SUSPENDIDO_SALDO', 'BLOQUEADO_ROBO', 'PORTADO_OUT')),
    last_sim_swap_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() - INTERVAL '30 days'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (msisdn)
) PARTITION BY HASH (msisdn);

-- 8 Particiones Físicas para Distribución Uniforme O(1) de 4M Abonados
CREATE TABLE telco_lines_p00 PARTITION OF telco_lines FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE telco_lines_p01 PARTITION OF telco_lines FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE telco_lines_p02 PARTITION OF telco_lines FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE telco_lines_p03 PARTITION OF telco_lines FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE telco_lines_p04 PARTITION OF telco_lines FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE telco_lines_p05 PARTITION OF telco_lines FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE telco_lines_p06 PARTITION OF telco_lines FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE telco_lines_p07 PARTITION OF telco_lines FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX idx_telco_lines_subscriber ON telco_lines (subscriber_id);
CREATE INDEX idx_telco_lines_status ON telco_lines (status);
CREATE INDEX idx_telco_lines_imei ON telco_lines (imei);

-- ============================================================================
-- MÓDULO 3: SALDOS EN TIEMPO REAL Y TRÁFICO OCS (TMF678)
-- ============================================================================

-- Tabla 5: balances_and_quotas (Particionada por Hash de MSISDN - 8 Shards)
CREATE TABLE balances_and_quotas (
    msisdn VARCHAR(15) NOT NULL,
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    balance_ves NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    balance_usd_equiv NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    remaining_data_mb INTEGER NOT NULL DEFAULT 0,
    total_quota_mb INTEGER NOT NULL DEFAULT 0,
    billing_cutoff_date DATE NOT NULL,
    days_overdue INTEGER NOT NULL DEFAULT 0,
    last_sync_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (msisdn, id)
) PARTITION BY HASH (msisdn);

CREATE TABLE balances_and_quotas_p00 PARTITION OF balances_and_quotas FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE balances_and_quotas_p01 PARTITION OF balances_and_quotas FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE balances_and_quotas_p02 PARTITION OF balances_and_quotas FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE balances_and_quotas_p03 PARTITION OF balances_and_quotas FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE balances_and_quotas_p04 PARTITION OF balances_and_quotas FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE balances_and_quotas_p05 PARTITION OF balances_and_quotas FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE balances_and_quotas_p06 PARTITION OF balances_and_quotas FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE balances_and_quotas_p07 PARTITION OF balances_and_quotas FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX idx_balances_sync ON balances_and_quotas (last_sync_at);

-- Tabla 6: usage_records_cdr (Particionada por Rango Mensual - Índices BRIN)
CREATE TABLE usage_records_cdr (
    event_timestamp TIMESTAMPTZ NOT NULL,
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    msisdn VARCHAR(15) NOT NULL,
    event_type VARCHAR(20) NOT NULL 
        CHECK (event_type IN ('DATA_4G', 'VOICE_CALL', 'SMS_OUT', 'RECHARGE')),
    data_volume_bytes BIGINT NOT NULL DEFAULT 0,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    cell_id VARCHAR(30) NOT NULL,
    status_code VARCHAR(10) NOT NULL DEFAULT 'SUCCESS',
    PRIMARY KEY (event_timestamp, id)
) PARTITION BY RANGE (event_timestamp);

-- Particiones Mensuales Range
CREATE TABLE cdr_2026_09 PARTITION OF usage_records_cdr
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');
CREATE TABLE cdr_2026_10 PARTITION OF usage_records_cdr
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');
CREATE TABLE cdr_2026_11 PARTITION OF usage_records_cdr
    FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');
CREATE TABLE cdr_2026_12 PARTITION OF usage_records_cdr
    FOR VALUES FROM ('2026-12-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');
CREATE TABLE cdr_default PARTITION OF usage_records_cdr DEFAULT;

-- Índice BRIN de alta densidad para telemetría masiva
CREATE INDEX idx_cdr_timestamp_brin ON usage_records_cdr USING BRIN (event_timestamp);
CREATE INDEX idx_cdr_msisdn ON usage_records_cdr (msisdn);

-- ============================================================================
-- MÓDULO 4: FINTECH, BANCOS SUDEBAN Y PAGOS MÓVILES C2P (TMF676)
-- ============================================================================

-- Tabla 7: banks_sudeban (Catálogo Homologado del Sistema Bancario Nacional)
CREATE TABLE banks_sudeban (
    bank_code VARCHAR(4) PRIMARY KEY,
    bank_name VARCHAR(100) NOT NULL,
    short_name VARCHAR(30) NOT NULL,
    c2p_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Tabla 8: financial_transactions (Particionada por Rango Mensual - Anti Replay)
CREATE TABLE financial_transactions (
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reference_id VARCHAR(64) NOT NULL,
    msisdn VARCHAR(15) NOT NULL,
    bank_code VARCHAR(4) NOT NULL REFERENCES banks_sudeban(bank_code),
    amount_ves NUMERIC(14,2) NOT NULL,
    amount_usd NUMERIC(10,2) NOT NULL,
    bcv_rate_applied NUMERIC(10,4) NOT NULL,
    payment_method VARCHAR(25) NOT NULL DEFAULT 'PAGO_MOVIL_C2P' 
        CHECK (payment_method IN ('PAGO_MOVIL_C2P', 'PORTAL_BDV', 'TRANSFERENCIA')),
    status VARCHAR(25) NOT NULL DEFAULT 'COMPLETADO' 
        CHECK (status IN ('PENDIENTE_OTP', 'COMPLETADO', 'RECHAZADO_SALDO', 'RECHAZADO_FRAUDE', 'RECHAZADO_DUPLICADO')),
    payer_cid_masked VARCHAR(20) NOT NULL,
    PRIMARY KEY (executed_at, reference_id)
) PARTITION BY RANGE (executed_at);

CREATE TABLE ft_2026_09 PARTITION OF financial_transactions
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');
CREATE TABLE ft_2026_10 PARTITION OF financial_transactions
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');
CREATE TABLE ft_2026_11 PARTITION OF financial_transactions
    FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');
CREATE TABLE ft_2026_12 PARTITION OF financial_transactions
    FOR VALUES FROM ('2026-12-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');
CREATE TABLE ft_default PARTITION OF financial_transactions DEFAULT;

-- Índice BRIN en transacciones y B-Tree en referencia para verificación instantánea
CREATE INDEX idx_ft_executed_brin ON financial_transactions USING BRIN (executed_at);
CREATE INDEX idx_ft_reference ON financial_transactions (reference_id);
CREATE INDEX idx_ft_msisdn ON financial_transactions (msisdn);

-- ============================================================================
-- MÓDULO 5: CRM, CHURN PREDICTIVO Y SEGURIDAD EIR (TMF680)
-- ============================================================================

-- Tabla 9: churn_metrics (Scoring Heurístico y Cupones de Retención)
CREATE TABLE churn_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    msisdn VARCHAR(15) NOT NULL,
    churn_score NUMERIC(5,2) NOT NULL CHECK (churn_score >= 0.00 AND churn_score <= 100.00),
    risk_segment VARCHAR(20) NOT NULL 
        CHECK (risk_segment IN ('LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK', 'CRITICAL_RISK')),
    days_without_recharge INTEGER NOT NULL DEFAULT 0,
    complaints_count_30d INTEGER NOT NULL DEFAULT 0,
    data_drop_pct NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    recommended_action VARCHAR(50) NOT NULL DEFAULT 'NO_ACTION',
    coupon_code_offered VARCHAR(30),
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_churn_msisdn ON churn_metrics (msisdn);
CREATE INDEX idx_churn_score ON churn_metrics (churn_score);

-- Tabla 10: eir_security_events (Registro Inmutable EIR de Bloqueos por Hurto/Fraude)
CREATE TABLE eir_security_events (
    ticket_id VARCHAR(30) PRIMARY KEY,
    msisdn VARCHAR(15) NOT NULL,
    imei VARCHAR(18) NOT NULL,
    imsi VARCHAR(20) NOT NULL,
    event_type VARCHAR(25) NOT NULL 
        CHECK (event_type IN ('THEFT_LOCK', 'SIM_SWAP_ALERT', 'UNAUTHORIZED_ACCESS', 'UNBLOCK_ORDER')),
    reason TEXT NOT NULL,
    reporting_agent VARCHAR(50) NOT NULL DEFAULT 'ANTIGRAVITY_MCP_AGENT',
    police_report_number VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_eir_msisdn ON eir_security_events (msisdn);
CREATE INDEX idx_eir_imei ON eir_security_events (imei);

-- ============================================================================
-- SEGURIDAD Y PERMISOLOGÍA: ROL n8n APP (ZERO-ACCESS A BÓVEDA PII)
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'usr_n8n_app') THEN
        CREATE ROLE usr_n8n_app WITH LOGIN PASSWORD 'n8n_app_secure_pass_2026';
    END IF;
END $$;

-- Permisos operacionales para n8n en el esquema público
GRANT CONNECT ON DATABASE current_database() TO usr_n8n_app;
GRANT USAGE ON SCHEMA public TO usr_n8n_app;
GRANT SELECT, INSERT, UPDATE ON TABLE 
    subscribers,
    product_plans,
    telco_lines,
    balances_and_quotas,
    usage_records_cdr,
    banks_sudeban,
    financial_transactions,
    churn_metrics,
    eir_security_events
TO usr_n8n_app;

-- REVOCACIÓN ESTRICTA: El rol de n8n NO PUEDE acceder a la bóveda cifrada PII
REVOKE ALL ON TABLE pii_vault FROM usr_n8n_app;

-- ============================================================================
-- SEMILLAS MAESTRAS DE CATÁLOGO (BANCOS SUDEBAN Y PLANES COMERCIALES)
-- ============================================================================

-- Inserción de los 16 Bancos del Sistema Bancario Nacional
INSERT INTO banks_sudeban (bank_code, bank_name, short_name, c2p_enabled, is_active) VALUES
    ('0102', 'Banco de Venezuela, S.A. Banco Universal', 'Banco de Venezuela', TRUE, TRUE),
    ('0104', 'Venezolano de Crédito, S.A. Banco Universal', 'Venezolano de Crédito', TRUE, TRUE),
    ('0105', 'Banco Mercantil, C.A. Banco Universal', 'Banco Mercantil', TRUE, TRUE),
    ('0108', 'Banco Provincial, S.A. Banco Universal', 'BBVA Provincial', TRUE, TRUE),
    ('0114', 'Bancaribe, C.A. Banco Universal', 'Bancaribe', TRUE, TRUE),
    ('0115', 'Banco Exterior, C.A. Banco Universal', 'Banco Exterior', TRUE, TRUE),
    ('0128', 'Banco Caroní, C.A. Banco Universal', 'Banco Caroní', TRUE, TRUE),
    ('0134', 'Banesco Banco Universal, C.A.', 'Banesco', TRUE, TRUE),
    ('0137', 'Banco Sofitasa Banco Universal, C.A.', 'Banco Sofitasa', TRUE, TRUE),
    ('0138', 'Banco Plaza, C.A. Banco Universal', 'Banco Plaza', TRUE, TRUE),
    ('0151', 'BFC Banco Fondo Común, C.A. Banco Universal', 'Banco Fondo Común', TRUE, TRUE),
    ('0156', '100% Banco, Banco Universal, C.A.', '100% Banco', TRUE, TRUE),
    ('0157', 'DelSur Banco Universal, C.A.', 'DelSur', TRUE, TRUE),
    ('0163', 'Banco del Tesoro, C.A. Banco Universal', 'Banco del Tesoro', TRUE, TRUE),
    ('0166', 'Banco Agrícola de Venezuela, C.A.', 'Banco Agrícola', TRUE, TRUE),
    ('0168', 'Bancrecer, S.A. Banco Microfinanciero', 'Bancrecer', TRUE, TRUE),
    ('0169', 'Mi Banco, Banco Microfinanciero, C.A.', 'Mi Banco', TRUE, TRUE),
    ('0171', 'Banco Activo, C.A. Banco Universal', 'Banco Activo', TRUE, TRUE),
    ('0172', 'Bancamiga Banco Universal, C.A.', 'Bancamiga', TRUE, TRUE),
    ('0174', 'Banplus Banco Universal, C.A.', 'Banplus', TRUE, TRUE),
    ('0175', 'Banco Bicentenario del Pueblo, Banco Universal C.A.', 'Banco Bicentenario', TRUE, TRUE),
    ('0177', 'Banco de la Fuerza Armada Nacional Bolivariana (BANFANB)', 'BANFANB', TRUE, TRUE),
    ('0191', 'Banco Nacional de Crédito, C.A. Banco Universal (BNC)', 'BNC', TRUE, TRUE)
ON CONFLICT (bank_code) DO NOTHING;

-- Inserción de los 16 Planes Comerciales Oficiales
INSERT INTO product_plans (plan_id, name, commercial_code, category, data_quota_mb, voice_minutes, sms_quota, price_usd, is_active) VALUES
    ('PLAN_10GB_4GMAX', 'Inteliplan 10GB 4GMAX', 'MOV-INT-10G', 'PREPAGO', 10240, 500, 1000, 7.50, TRUE),
    ('PLAN_20GB_4GMAX', 'Inteliplan 20GB 4GMAX', 'MOV-INT-20G', 'PREPAGO', 20480, 1000, 2000, 12.00, TRUE),
    ('PLAN_5GB_BASICO', 'Plan Básico Conecta 5GB', 'MOV-CON-05G', 'PREPAGO', 5120, 250, 500, 4.00, TRUE),
    ('PLAN_3GB_LIGERO', 'Plan Ligero 3GB', 'MOV-LIG-03G', 'PREPAGO', 3072, 150, 300, 2.50, TRUE),
    ('PLAN_1GB_SOCIAL', 'Plan Social Conectividad', 'MOV-SOC-01G', 'PREPAGO', 1024, 100, 200, 1.00, TRUE),
    ('PLAN_50GB_CORP', 'Corporativo 4GMAX Ilimitado 50GB', 'MOV-CORP-50G', 'CORPORATIVO', 51200, 3000, 5000, 28.00, TRUE),
    ('PLAN_100GB_CORP', 'Corporativo Ultra 100GB', 'MOV-CORP-100G', 'CORPORATIVO', 102400, 6000, 10000, 45.00, TRUE),
    ('PLAN_POSPAGO_PLUS', 'Movilnet Pospago Conecta Plus', 'MOV-POS-PLUS', 'POSPAGO', 15360, 800, 1500, 10.50, TRUE),
    ('PLAN_POSPAGO_ELITE', 'Movilnet Pospago Élite 30GB', 'MOV-POS-ELIT', 'POSPAGO', 30720, 1500, 3000, 18.00, TRUE),
    ('PACK_EXTRA_2GB', 'Extra Datos 2GB 4GMAX', 'MOV-EXT-02G', 'EXTRA_DATOS', 2048, 0, 0, 1.80, TRUE),
    ('PACK_EXTRA_5GB', 'Extra Datos 5GB 4GMAX', 'MOV-EXT-05G', 'EXTRA_DATOS', 5120, 0, 0, 3.80, TRUE),
    ('PACK_EXTRA_10GB', 'Extra Datos 10GB 4GMAX', 'MOV-EXT-10G', 'EXTRA_DATOS', 10240, 0, 0, 6.50, TRUE),
    ('PLAN_JUBILADO_PATRIA', 'Plan Solidario Patria Jubilados', 'MOV-JUB-PAT', 'PREPAGO', 2048, 300, 500, 0.50, TRUE),
    ('PLAN_ESTUDIANTE_CONECTA', 'Estudiante Conecta 4G', 'MOV-EST-CON', 'PREPAGO', 4096, 200, 400, 2.00, TRUE),
    ('PLAN_ROAMING_LATAM', 'Roaming Movilnet Andino/Latam', 'MOV-ROAM-LAT', 'EXTRA_DATOS', 3072, 60, 60, 15.00, TRUE),
    ('PLAN_M2M_TELEMETRIA', 'Telemetría IoT M2M Industrial', 'MOV-IOT-M2M', 'CORPORATIVO', 512, 10, 50, 0.80, TRUE)
ON CONFLICT (plan_id) DO NOTHING;

-- =============================================================================
-- 13. CONTROL DE LÍMITES FREEMIUM PARA PROSPECTOS DE OTRAS OPERADORAS (0412/0414/0424)
-- =============================================================================
CREATE TABLE IF NOT EXISTS prospect_trial_limits (
    msisdn TEXT PRIMARY KEY,
    carrier TEXT NOT NULL,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    monthly_queries INTEGER NOT NULL DEFAULT 0,
    last_query_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prospect_trial_carrier ON prospect_trial_limits(carrier);

