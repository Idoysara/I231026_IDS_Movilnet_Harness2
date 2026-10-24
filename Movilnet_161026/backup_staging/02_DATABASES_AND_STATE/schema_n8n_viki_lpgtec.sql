-- ======================================================================================
-- ARQUITECTURA RELACIONAL DE DATOS: WORKFLOW n8n "Viki LPGTEC v2" (sNMbtiEiTkuQ9OCY)
-- ======================================================================================
-- Endpoint Canónico: https://n8n.lpgtec.net/workflow/sNMbtiEiTkuQ9OCY
-- Servidor de Gateway: Evolution API (WhatsApp Baileys Engine)
-- Motor de Persistencia: PostgreSQL 15+ / SQLite 3.38+ WAL
-- Cumplimiento: Universal Best Practices Engineering Rule (Pilar I, III, V)
-- ======================================================================================

PRAGMA foreign_keys = ON;

-- --------------------------------------------------------------------------------------
-- ESQUEMA 1: GATEWAY OMNICANAL & MENSAJERÍA INGRESS/EGRESS (Evolution API)
-- --------------------------------------------------------------------------------------

-- 1.1. Instancias Conectadas de Evolution API
-- Relación de Nodos n8n:
--   - Webhook (Ingress): body.instance, body.server_url
--   - Edit Fields: body.instance, body.server_url, body.apikey
--   - HTTP Request (Egress): URL /message/sendText/{instance}
CREATE TABLE IF NOT EXISTS evolution_instances (
    instance_id         VARCHAR(64) PRIMARY KEY,       -- Nombre de la instancia (ej: 'Viki LPGTEC')
    server_url          VARCHAR(255) NOT NULL,         -- URL base del gateway (ej: 'http://evolution:8080')
    apikey_hash         VARCHAR(128) NOT NULL,         -- Hash de la apikey para autenticación de headers
    bot_phone_jid       VARCHAR(64) NOT NULL,          -- JID de WhatsApp de la línea bot (ej: '584241533712@s.whatsapp.net')
    bot_phone_national  VARCHAR(20) NOT NULL,          -- Formato canónico nacional ('04241533712')
    status              VARCHAR(20) DEFAULT 'CONNECTED' CHECK(status IN ('CONNECTED', 'DISCONNECTED', 'CONNECTING', 'QRCODE')),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 1.2. Directorio de Contactos & Abonados WhatsApp
-- Relación de Nodos n8n:
--   - Edit Fields: body.data.key.remoteJid, body.data.pushName
--   - Postgres Chat Memory: sessionKey
--   - Call 'Sistema de Gestión de Contactos': consulta y sincronización de clientes
CREATE TABLE IF NOT EXISTS whatsapp_contacts (
    remote_jid          VARCHAR(64) PRIMARY KEY,       -- JID internacional (ej: '584142650088@s.whatsapp.net')
    phone_national      VARCHAR(20) NOT NULL,          -- Número nacional normalizado (ej: '04142650088')
    push_name           VARCHAR(128),                  -- Nombre reportado en perfil WhatsApp (ej: 'Francisco Landaeta')
    instance_id         VARCHAR(64) NOT NULL,          -- Instancia asociada
    contact_type        VARCHAR(20) DEFAULT 'NATURAL' CHECK(contact_type IN ('NATURAL', 'JURIDICO', 'VIP', 'EMPLEADO')),
    first_seen_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_interaction_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES evolution_instances(instance_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contacts_phone_nat ON whatsapp_contacts(phone_national);

-- 1.3. Registro de Eventos Inbound (Webhooks 'messages.upsert')
-- Relación de Nodos n8n:
--   - Webhook: Recibe payload crudo POST /webhook/messages_upsert
--   - If: Evalúa body.data.key.fromMe == false
--   - Edit Fields: Normaliza atributos canónicos
--   - Switch: Enruta según body.data.messageType ('texto', 'imagen', 'audio', 'video', 'pdf')
CREATE TABLE IF NOT EXISTS inbound_webhook_events (
    event_id            VARCHAR(36) PRIMARY KEY,       -- UUID autogenerado del evento
    message_id          VARCHAR(64) UNIQUE NOT NULL,   -- ID único del mensaje WhatsApp (body.data.key.id)
    instance_id         VARCHAR(64) NOT NULL,          -- Instancia receptora
    remote_jid          VARCHAR(64) NOT NULL,          -- Emisor del mensaje
    from_me             BOOLEAN DEFAULT 0,             -- Flag de mensaje propio (0=falso, 1=verdadero)
    message_type        VARCHAR(20) NOT NULL CHECK(message_type IN ('texto', 'imagen', 'audio', 'video', 'pdf', 'location', 'contact')),
    raw_text_content    TEXT,                          -- Contenido de texto / caption / extendedTextMessage
    date_time           TIMESTAMP NOT NULL,            -- Marca de tiempo oficial del mensaje
    routing_decision    VARCHAR(50) DEFAULT 'PENDING', -- Decisión: 'ROUTER_DETERMINISTICO', 'AI_AGENT', 'MOVILNET_CORE'
    raw_payload_json    TEXT,                          -- Serialización JSON completa del webhook para auditoría forense
    received_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES evolution_instances(instance_id),
    FOREIGN KEY (remote_jid) REFERENCES whatsapp_contacts(remote_jid)
);

CREATE INDEX IF NOT EXISTS idx_inbound_msg_id ON inbound_webhook_events(message_id);
CREATE INDEX IF NOT EXISTS idx_inbound_jid_date ON inbound_webhook_events(remote_jid, date_time);

-- 1.4. Catálogo de Archivos Multimedia (Audios, Imágenes, Videos, PDFs)
-- Relación de Nodos n8n:
--   - Capturar Audio / Imagen / Video / HTTP Request1: POST /chat/getBase64FromMediaMessage
--   - Convertir Audio / Imagen / Video: nodo convertToFile
--   - HTTP Request2 (pdf2text): https://www.lpgtec.net/pdf2text/index.php
--   - Transcribe a recording / Analyze image / Analyze video: Modelos Gemini
--   - Captura PDF: Asignación a content.parts[0].text
CREATE TABLE IF NOT EXISTS media_assets (
    asset_id            VARCHAR(36) PRIMARY KEY,       -- UUID del recurso multimedia
    message_id          VARCHAR(64) NOT NULL,          -- Mensaje al que pertenece
    media_type          VARCHAR(20) NOT NULL CHECK(media_type IN ('audio', 'imagen', 'video', 'pdf')),
    mimetype            VARCHAR(100) NOT NULL,         -- MIME (ej: 'audio/ogg; codecs=opus', 'application/pdf')
    media_url           TEXT,                          -- URL remota de descarga temporal de WhatsApp
    file_title          VARCHAR(255),                  -- Nombre de archivo (en PDFs / docs)
    page_count          INTEGER,                       -- Conteo de páginas (PDFs)
    base64_payload      TEXT,                          -- Carga base64 procesada
    transcription_text  TEXT,                          -- Transcripción o análisis OCR / LLM resultante
    processed_status    VARCHAR(20) DEFAULT 'PROCESSED' CHECK(processed_status IN ('PENDING', 'PROCESSED', 'FAILED')),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES inbound_webhook_events(message_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_message_id ON media_assets(message_id);

-- --------------------------------------------------------------------------------------
-- ESQUEMA 2: MEMORIA CONVERSACIONAL LANGCHAIN (PostgreSQL Native Store)
-- --------------------------------------------------------------------------------------

-- 2.1. Historial de Chat Multiturno LangChain
-- Relación de Nodos n8n:
--   - Postgres Chat Memory (@n8n/n8n-nodes-langchain.memoryPostgresChat):
--       sessionKey: body.data.pushName ?? body.data.key.remoteJid
--       contextWindowLength: 50
--   - AI Agent (@n8n/n8n-nodes-langchain.agent): Inyecta el buffer conversacional al modelo Gemini
CREATE TABLE IF NOT EXISTS chat_histories (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT, -- Identificador secuencial (SERIAL en Postgres)
    session_id          VARCHAR(255) NOT NULL,             -- Clave de sesión (remoteJid o pushName)
    message             TEXT NOT NULL,                     -- JSON LangChain: {"type": "human"|"ai", "data": {"content": "..."}}
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_histories_session ON chat_histories(session_id);

-- --------------------------------------------------------------------------------------
-- ESQUEMA 3: INTELIGENCIA CAMBIARIA & TASAS FINANCIERAS (BCV / Paralelo / Euro)
-- --------------------------------------------------------------------------------------

-- 3.1. Caché Histórico de Tasas de Cambio
-- Relación de Nodos n8n:
--   - BCV oficial / BCV oficial v2: https://ve.dolarapi.com/v1/dolares/oficial
--   - BCV paralelo / BCV paralelo v2: https://ve.dolarapi.com/v1/dolares/paralelo
--   - BCV Euros / BCV Euros v2: https://ve.dolarapi.com/v1/euros/oficial
--   - Edit Fields - Oficial: tasa_bcv, fecha_bcv, fuente_bcv
--   - Edit Fields - Paralelo: tasa_paralela, fecha_paralela, fuente_paralela
CREATE TABLE IF NOT EXISTS exchange_rates_cache (
    rate_id             VARCHAR(36) PRIMARY KEY,       -- UUID del registro de tasa
    currency_code       VARCHAR(10) NOT NULL CHECK(currency_code IN ('USD', 'EUR')),
    market_type         VARCHAR(20) NOT NULL CHECK(market_type IN ('OFICIAL_BCV', 'PARALELO')),
    rate_value          NUMERIC(14, 4) NOT NULL,       -- Valor numérico en Bolívares (promedio/venta)
    rate_date_iso       VARCHAR(35) NOT NULL,          -- Fecha de publicación informada por la API
    source_url          VARCHAR(255) NOT NULL,         -- Endpoint consultado
    fetched_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rates_market_curr ON exchange_rates_cache(currency_code, market_type, fetched_at);

-- 3.2. Bitácora de Conversiones y Diferenciales Cambiarios
-- Relación de Nodos n8n:
--   - Router - Consultas determinísticas: Detecta 'conversion_bcv', 'conversion_paralela', 'diferencial_cambiario'
--   - Calcular conversión BCV (Code Node): Extrae monto USD mediante regex y multiplica por tasa_bcv
--   - Calcular conversión Paralela (Code Node): Multiplica por tasa_paralela (requiere clave '2306')
--   - Calcular diferencial cambiario (Code Node): diferencial = (paralela - oficial) / oficial * 100
CREATE TABLE IF NOT EXISTS exchange_calculations_log (
    calc_id             VARCHAR(36) PRIMARY KEY,       -- UUID del cálculo realizado
    message_id          VARCHAR(64),                   -- Mensaje originador de la consulta
    calculation_type    VARCHAR(40) NOT NULL CHECK(calculation_type IN ('CONVERSION_BCV', 'CONVERSION_PARALELA', 'DIFERENCIAL_CAMBIARIO', 'CONSULTA_TASA')),
    input_amount_usd    NUMERIC(14, 2),                -- Monto en USD extraído del mensaje (ej: 50.00)
    rate_bcv_applied    NUMERIC(14, 4) NOT NULL,       -- Tasa oficial BCV aplicada
    rate_paralela_applied NUMERIC(14, 4),              -- Tasa paralela aplicada (si aplica)
    result_bs           NUMERIC(16, 2),                -- Resultado final en Bolívares
    differential_pct    NUMERIC(6, 2),                 -- % Diferencial cambiario calculado
    differential_bs     NUMERIC(14, 2),                -- Diferencial nominal en Bs.
    auth_pin_verified   BOOLEAN DEFAULT 1,             -- 1=Clave 2306 válida o no requerida, 0=Sin clave
    calculated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES inbound_webhook_events(message_id)
);

CREATE INDEX IF NOT EXISTS idx_calc_msg ON exchange_calculations_log(message_id);

-- --------------------------------------------------------------------------------------
-- ESQUEMA 4: HERRAMIENTAS DE NEGOCIO Y SUBFLUJOS (Google Sheets & Workflows)
-- --------------------------------------------------------------------------------------

-- 4.1. Catálogo de Lista de Precios de Productos
-- Relación de Nodos n8n:
--   - ListadePrecios (@n8n/n8n-nodes-langchain.googleSheetsTool):
--       DocumentId: 1nMP8_xw7D-2VQCACWc8hlROyADPjdIjt9SxGxIX2CQM
--       Sheet: ListaPrecios (gid=0)
CREATE TABLE IF NOT EXISTS catalog_price_list (
    sku_id              VARCHAR(32) PRIMARY KEY,       -- Código único de producto / SKU
    product_name        VARCHAR(255) NOT NULL,         -- Nombre descriptivo del producto
    category            VARCHAR(100) NOT NULL,         -- Categoría o rubro comercial
    price_usd           NUMERIC(12, 2) NOT NULL,       -- Precio base en Dólares americanos
    unit_measure        VARCHAR(20) DEFAULT 'UNIDAD',  -- Unidad ('UNIDAD', 'KG', 'LITRO', 'PAQUETE')
    is_active           BOOLEAN DEFAULT 1,             -- Disponibilidad comercial
    last_sync_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_price_list_cat ON catalog_price_list(category, is_active);

-- 4.2. Registro de Invocación de Subflujos LangChain
-- Relación de Nodos n8n:
--   - Call 'Sistema de Gestión de Contactos'1 (WorkflowId: lTTTFJh5l79115yZ)
--   - Recetas (WorkflowId: m2hmP7U1aAyuUmew)
CREATE TABLE IF NOT EXISTS subworkflow_executions (
    sub_exec_id         VARCHAR(36) PRIMARY KEY,       -- UUID de ejecución
    parent_message_id   VARCHAR(64) NOT NULL,          -- Mensaje padre
    target_workflow_id  VARCHAR(32) NOT NULL,          -- ID del subworkflow en n8n
    subworkflow_name    VARCHAR(128) NOT NULL,         -- 'Sistema de Gestión de Contactos' o 'Recetas'
    input_query         TEXT NOT NULL,                 -- Parámetro enviado en {{ $json.query }}
    output_result       TEXT,                          -- Resultado retornado por el subflujo
    status              VARCHAR(20) DEFAULT 'SUCCESS' CHECK(status IN ('SUCCESS', 'ERROR', 'TIMEOUT')),
    executed_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_message_id) REFERENCES inbound_webhook_events(message_id)
);

-- --------------------------------------------------------------------------------------
-- ESQUEMA 5: SALIDAS Y EGRESO INSTITUCIONAL (WhatsApp Outbound Egress)
-- --------------------------------------------------------------------------------------

-- 5.1. Cola de Mensajes de Salida Egress
-- Relación de Nodos n8n:
--   - Merge - Respuestas 2, 3, 4, 5, 6, 7, 8: Concentran las respuestas deterministas y de IA
--   - Code (Sanitizador): Limpia sintaxis Markdown, saltos y formatos
--   - HTTP Request: POST {server_url}/message/sendText/{instance}
CREATE TABLE IF NOT EXISTS outbound_messages (
    outbound_id         VARCHAR(36) PRIMARY KEY,       -- UUID del mensaje de salida
    inbound_event_id    VARCHAR(36),                   -- Evento entrante que motivó la respuesta (nullable)
    instance_id         VARCHAR(64) NOT NULL,          -- Instancia transmisora
    recipient_jid       VARCHAR(64) NOT NULL,          -- JID de WhatsApp de destino
    reply_text          TEXT NOT NULL,                 -- Texto depurado a enviar
    source_branch       VARCHAR(64) NOT NULL,          -- Rama generadora (ej: 'TASA_OFICIAL', 'DIFERENCIAL', 'AI_AGENT')
    dispatch_delay_ms   INTEGER DEFAULT 1200,          -- Retardo humano simulado en milisegundos
    http_status_code    INTEGER DEFAULT 200,           -- Código HTTP de respuesta de Evolution API
    dispatch_status     VARCHAR(20) DEFAULT 'SENT' CHECK(dispatch_status IN ('SENT', 'DELIVERED', 'FAILED')),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inbound_event_id) REFERENCES inbound_webhook_events(event_id),
    FOREIGN KEY (instance_id) REFERENCES evolution_instances(instance_id)
);

CREATE INDEX IF NOT EXISTS idx_outbound_recipient ON outbound_messages(recipient_jid, created_at);

-- --------------------------------------------------------------------------------------
-- ESQUEMA 6: ENLACE TELCO MOVILNET (Fast-Path Integrado en Nodo 67)
-- --------------------------------------------------------------------------------------

-- 6.1. Vinculación de Abonados con el Núcleo ODA Movilnet
-- Relación de Nodos n8n:
--   - Movilnet Core - Fast-Path ODA: Inyectado entre Router y Merge - Respuestas 5
CREATE TABLE IF NOT EXISTS movilnet_n8n_bridge_logs (
    bridge_id           VARCHAR(36) PRIMARY KEY,       -- UUID de transacción en puente
    message_id          VARCHAR(64) NOT NULL,          -- Mensaje disparador
    msisdn              VARCHAR(20) NOT NULL,          -- Teléfono nacional Movilnet (ej: '04142650088')
    intent_detected     VARCHAR(40) NOT NULL,          -- 'CONTRACT_INFO', 'BALANCE_CHECK', 'RECHARGE_C2P'
    plan_id             VARCHAR(64),                   -- Plan detectado en Core ODA
    balance_ves         NUMERIC(14, 2),                -- Saldo en Bolívares retornado
    data_remaining_mb   INTEGER,                       -- Megas disponibles
    latency_ms          NUMERIC(8, 2),                 -- Latencia de resolución en Core (<15ms)
    tokens_cost_usd     NUMERIC(8, 4) DEFAULT 0.0000,  -- Costo en tokens ($0.00 en fast-path determinista)
    resolved_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES inbound_webhook_events(message_id)
);

CREATE INDEX IF NOT EXISTS idx_bridge_msisdn ON movilnet_n8n_bridge_logs(msisdn);
