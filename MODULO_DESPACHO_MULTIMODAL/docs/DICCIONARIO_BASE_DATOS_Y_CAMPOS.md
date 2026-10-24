# 🗄️ DICCIONARIO DE BASE DE DATOS, TABLAS, CAMPOS Y VARIABLES
**Proyecto:** Telecomunicaciones Movilnet C.A. — Módulo Autónomo de Despacho Multimodal  
**Gobernanza:** Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal  
**Motor de Persistencia:** SQLite 3 WAL (Write-Ahead Logging) con compatibilidad PostgreSQL 15+  
**Modo de Aislamiento:** Multi-Tenancy Lógico con Row-Level Security y Bóveda Particionada ($1 \leftrightarrow N$)  

---

## 1. 🧮 Demostración Matemática: ¿Por qué NO usar 1 Base de Datos por Usuario?

### Formulación del Problema:
Sea $N = 4.000.000$ el número total de abonados de la red. Supóngase la hipótesis de asignar un archivo de base de datos físico independiente $DB_i$ a cada usuario $u_i \in U$:

1. **Agotamiento de Descriptores de Ficheros (File Descriptors):**
   El límite estándar del kernel Linux para procesos no privilegiados es `ulimit -n = 1024` (o `65535` en servidores tuneados). Si sólo el 2% de los usuarios interactúan concurrentemente:
   $$C = 0.02 \times 4.000.000 = 80.000 \text{ conexiones simultáneas}$$
   $$FD_{requeridos} = 80.000 > FD_{máximos\_kernel} \implies \text{Error: Too many open files (Kernel Crash)}$$

2. **Sobrecarga de Memoria en Estructuras de Sistema de Ficheros (Inodos y VFS):**
   Cada base de datos SQLite abierta requiere una estructura en memoria de página caché mínima de 2 MB (64 páginas de 32 KB).
   $$RAM_{necesaria} = 80.000 \text{ instancias activas} \times 2 \text{ MB} = 160 \text{ GB de RAM solo en páginas vacías}$$

3. **Incapacidad Algorítmica de Detección de Fraude en Tiempo Real:**
   Para validar si una referencia bancaria de Pago Móvil $R_{c2p}$ ya fue usada por otro usuario, se requeriría un escaneo lineal sobre $N$ bases de datos:
   $$Complejidad(Busqueda) = O(N) = 4.000.000 \text{ lecturas de archivo} \approx 45 \text{ segundos por transacción}$$
   Bajo el modelo de base de datos relacional unificada con índice B-Tree:
   $$Complejidad(Busqueda) = O(\log_2 N) = \log_2(4.000.000) \approx 22 \text{ operaciones} \implies 0.04 \text{ ms}$$

**Conclusión Irrefutable:** El diseño de Base de Datos Relacional Unificada con Bóvedas Lógicas Particionadas es la **única solución Carrier-Grade viable**.

---

## 2. 🏛️ Esquema DDL Oficial (Data Definition Language)

```sql
-- ============================================================================
-- TABLA 1: user_multimodal_vault (Bóvedas Privadas por Abonado)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_multimodal_vault (
    vault_id VARCHAR(64) PRIMARY KEY,                    -- UUID v4 de la bóveda
    msisdn_hash VARCHAR(64) NOT NULL UNIQUE,             -- HMAC-SHA256 del número (Blind Index O(1))
    phone_display VARCHAR(20) NOT NULL,                  -- Número formateado (+58 416-XXXXXXX)
    vault_directory VARCHAR(255) NOT NULL,               -- Ruta relativa en disco: vaults/usr_{hash}/
    quota_limit_bytes BIGINT NOT NULL DEFAULT 52428800,  -- Límite de cuota: 50 MB (52.428.800 bytes)
    quota_used_bytes BIGINT NOT NULL DEFAULT 0,          -- Espacio actualmente ocupado en bytes
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',        -- ACTIVE, SUSPENDED, EXCEEDED
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_interaction TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vault_msisdn_hash ON user_multimodal_vault(msisdn_hash);
CREATE INDEX IF NOT EXISTS idx_vault_status ON user_multimodal_vault(status);

-- ============================================================================
-- TABLA 2: multimodal_media_asset (Catálogo de Archivos Multimedia)
-- ============================================================================
CREATE TABLE IF NOT EXISTS multimodal_media_asset (
    asset_id VARCHAR(64) PRIMARY KEY,                    -- UUID v4 del archivo multimedia
    vault_id VARCHAR(64) NOT NULL,                       -- Clave foránea a user_multimodal_vault
    direction VARCHAR(10) NOT NULL,                      -- INBOUND (Recibido) o OUTBOUND (Despachado)
    media_type VARCHAR(20) NOT NULL,                     -- AUDIO, IMAGE, DOCUMENT, VIDEO
    mime_type VARCHAR(100) NOT NULL,                     -- audio/ogg, image/jpeg, application/pdf, etc.
    original_filename VARCHAR(255) NOT NULL,             -- Nombre original sanitizado
    stored_filename VARCHAR(255) NOT NULL,               -- Nombre seguro en disco (UUID + extensión)
    file_size_bytes BIGINT NOT NULL,                     -- Peso exacto en bytes
    sha256_checksum VARCHAR(64) NOT NULL,                -- Hash criptográfico SHA-256 del archivo
    file_rel_path VARCHAR(255) NOT NULL,                 -- Ruta relativa completa en disco
    processing_status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSED, FAILED
    transcription_text TEXT DEFAULT NULL,                -- Texto extraído (Whisper STT / OCR)
    analysis_metadata TEXT DEFAULT NULL,                 -- JSON estructurado con entidades y montos
    expires_at TIMESTAMP NOT NULL,                       -- Fecha límite de retención (TTL 30 días)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vault_id) REFERENCES user_multimodal_vault(vault_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_asset_vault_id ON multimodal_media_asset(vault_id);
CREATE INDEX IF NOT EXISTS idx_asset_checksum ON multimodal_media_asset(sha256_checksum);
CREATE INDEX IF NOT EXISTS idx_asset_expires_at ON multimodal_media_asset(expires_at);
CREATE INDEX IF NOT EXISTS idx_asset_status ON multimodal_media_asset(processing_status);

-- ============================================================================
-- TABLA 3: multimodal_session_transcripts (Trazabilidad y Conversación)
-- ============================================================================
CREATE TABLE IF NOT EXISTS multimodal_session_transcripts (
    session_id VARCHAR(64) PRIMARY KEY,                  -- UUID v4 de la sesión
    vault_id VARCHAR(64) NOT NULL,                       -- Bóveda asociada
    channel VARCHAR(20) NOT NULL DEFAULT 'WHATSAPP',     -- WHATSAPP, TELEGRAM, PWA
    input_asset_id VARCHAR(64) DEFAULT NULL,             -- Archivo que disparó la interacción
    recognized_intent VARCHAR(50) DEFAULT NULL,          -- CONSULTA_SALDO, PAGO_C2P, REPORTE_FALLA
    agent_response_text TEXT NOT NULL,                   -- Respuesta textual emitida
    output_asset_id VARCHAR(64) DEFAULT NULL,            -- Archivo multimedia despachado (ej: recibo)
    latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,    -- Latencia total de atención en ms
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vault_id) REFERENCES user_multimodal_vault(vault_id) ON DELETE CASCADE,
    FOREIGN KEY (input_asset_id) REFERENCES multimodal_media_asset(asset_id),
    FOREIGN KEY (output_asset_id) REFERENCES multimodal_media_asset(asset_id)
);

CREATE INDEX IF NOT EXISTS idx_session_vault ON multimodal_session_transcripts(vault_id);
CREATE INDEX IF NOT EXISTS idx_session_created ON multimodal_session_transcripts(created_at DESC);
```

---

## 3. 📖 Diccionario Detallado de Campos

### 3.1. Tabla: `user_multimodal_vault`
| Campo | Tipo SQL | Nulo | Por Defecto | Descripción y Reglas de Negocio |
| :--- | :--- | :---: | :--- | :--- |
| `vault_id` | `VARCHAR(64)` | ❌ NO | `uuid4()` | Identificador universal inmutable de la bóveda del abonado. |
| `msisdn_hash` | `VARCHAR(64)` | ❌ NO | — | Hash ciego `HMAC_SHA256(msisdn, secret)`. Permite búsqueda en tiempo $O(1)$ sin almacenar el número de teléfono en texto plano en índices públicos. |
| `phone_display` | `VARCHAR(20)` | ❌ NO | — | Representación visual ofuscada para interfaces de soporte (ej. `+58 416-***587`). |
| `vault_directory` | `VARCHAR(255)` | ❌ NO | — | Subdirectorio físico de almacenamiento asignado al usuario dentro de `vaults/`. |
| `quota_limit_bytes` | `BIGINT` | ❌ NO | `52428800` | Cuota máxima en bytes. Límite: 50 Megabytes. |
| `quota_used_bytes` | `BIGINT` | ❌ NO | `0` | Sumatoria matemática del peso de todos los archivos vivos en la bóveda. |
| `status` | `VARCHAR(20)` | ❌ NO | `'ACTIVE'` | Estado operacional: `ACTIVE` (Permite subidas), `EXCEEDED` (Rechaza nuevas subidas), `SUSPENDED` (Bloqueo administrativo). |
| `created_at` | `TIMESTAMP` | ❌ NO | `CURRENT_TIMESTAMP` | Marca temporal UTC de creación de la bóveda. |
| `updated_at` | `TIMESTAMP` | ❌ NO | `CURRENT_TIMESTAMP` | Última actualización de cuotas o metadatos. |
| `last_interaction` | `TIMESTAMP` | ❌ NO | `CURRENT_TIMESTAMP` | Fecha de la última solicitud atendida. Utilizado para políticas de hibernación. |

---

### 3.2. Tabla: `multimodal_media_asset`
| Campo | Tipo SQL | Nulo | Por Defecto | Descripción y Reglas de Negocio |
| :--- | :--- | :---: | :--- | :--- |
| `asset_id` | `VARCHAR(64)` | ❌ NO | `uuid4()` | Identificador universal único del activo multimedia. |
| `vault_id` | `VARCHAR(64)` | ❌ NO | — | Llave foránea vinculante con la bóveda del usuario propietario. |
| `direction` | `VARCHAR(10)` | ❌ NO | — | Flujo de tráfico: `INBOUND` (Recibido del usuario) o `OUTBOUND` (Emitido por el asistente). |
| `media_type` | `VARCHAR(20)` | ❌ NO | — | Clasificación canónica: `AUDIO`, `IMAGE`, `DOCUMENT`, `VIDEO`. |
| `mime_type` | `VARCHAR(100)` | ❌ NO | — | Tipo MIME verificado por Magic Bytes (`audio/ogg`, `image/png`, `application/pdf`). |
| `original_filename`| `VARCHAR(255)` | ❌ NO | — | Nombre enviado por el cliente, sanitizado sin secuencias `../` o caracteres especiales. |
| `stored_filename` | `VARCHAR(255)` | ❌ NO | — | Nombre físico en disco: `{asset_id}_{timestamp}.{ext}`. |
| `file_size_bytes` | `BIGINT` | ❌ NO | — | Tamaño exacto en bytes del archivo verificado tras la descarga. |
| `sha256_checksum` | `VARCHAR(64)` | ❌ NO | — | Hash SHA-256 del contenido binario para garantizar inmutabilidad y evitar duplicados. |
| `file_rel_path` | `VARCHAR(255)` | ❌ NO | — | Ruta relativa segura desde la raíz de bóvedas (`vaults/usr_{hash}/audio/...`). |
| `processing_status`| `VARCHAR(20)`| ❌ NO | `'PENDING'` | Estado de pipeline: `PENDING`, `PROCESSING`, `PROCESSED`, `FAILED`. |
| `transcription_text`| `TEXT` | ✔️ SÍ | `NULL` | Texto transcrito por Whisper STT (para audios) o texto OCR extraído (para imágenes/PDF). |
| `analysis_metadata`| `TEXT` | ✔️ SÍ | `NULL` | Objeto JSON con entidades detectadas (ej. `{"banco": "0102", "referencia": "123456", "monto": 150.0}`). |
| `expires_at` | `TIMESTAMP` | ❌ NO | — | Timestamp UTC en el que el archivo debe ser eliminado por el cron de limpieza (30 días tras su creación). |
| `created_at` | `TIMESTAMP` | ❌ NO | `CURRENT_TIMESTAMP` | Fecha de creación del registro. |

---

## 4. ⚙️ Variables de Entorno y Configuración Declarativa

El módulo se parametriza de forma 100% independiente a través del archivo `.env` o variables de entorno del sistema operativo:

```ini
# ==============================================================================
# CONFIGURACIÓN DEL SERVIDOR AUTÓNOMO MULTIMODAL
# ==============================================================================
MULTIMODAL_PORT=8025
MULTIMODAL_HOST=0.0.0.0
MULTIMODAL_DEBUG=False
MULTIMODAL_ENVIRONMENT=staging  # staging | production | testing

# ==============================================================================
# PERSISTENCIA Y BÓVEDAS PRIVADAS
# ==============================================================================
MULTIMODAL_DB_PATH=./multimodal_vault.db
MULTIMODAL_VAULT_ROOT=./vaults
MULTIMODAL_SECRET_KEY=movilnet_carrier_grade_secret_vault_hmac_2026
MULTIMODAL_USER_QUOTA_BYTES=52428800  # 50 MB por usuario
MULTIMODAL_RETENTION_DAYS=30          # Purga automática de archivos tras 30 días

# ==============================================================================
# LÍMITES MÁXIMOS POR TIPO DE ARCHIVO (EN BYTES)
# ==============================================================================
MAX_AUDIO_SIZE_BYTES=16777216    # 16 MB
MAX_IMAGE_SIZE_BYTES=5242880     # 5 MB
MAX_DOCUMENT_SIZE_BYTES=104857600 # 100 MB
MAX_VIDEO_SIZE_BYTES=16777216    # 16 MB

# ==============================================================================
# INTEGRACIÓN IA Y MOTORES DE PROCESAMIENTO
# ==============================================================================
WHISPER_ENGINE_TYPE=mock         # mock (desarrollo local) | openai_api | local_whisper
OCR_ENGINE_TYPE=auto             # auto | tesseract | apple_vision | none  (valores desconocidos fallan cerrado; el modo 'heuristic' con datos fijos fue ELIMINADO — ver BITACORA_TECNICA H-03)
GEMINI_API_KEY=                  # Clave para análisis visual avanzado (opcional)

# ==============================================================================
# GOBERNANZA Y REGLAS CONSTITUCIONALES
# ==============================================================================
ENFORCE_PWA_UNIVERSAL_LINK=True
OFFICIAL_PWA_URL=https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html
```
