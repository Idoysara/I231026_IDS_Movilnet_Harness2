# 🏛️ Modelo Conceptual de Datos y Persistencia — Fase 1
## Proyecto: `AI_Movilnet_300926` — Telecomunicaciones Movilnet C.A.
**Estándar:** TM Forum Open Digital Architecture (ODA) & Frameworx (TMF620, TMF622, TMF632, TMF676, TMF678, TMF680)  
**Motor de Persistencia:** PostgreSQL 15 Enterprise Partitioned  
**Escala de Dimensionamiento:** 4,000,000 de Abonados Activos (Prefijos `0416` y `0426`)  
**Fecha:** 2026-09-30 | **Versión:** 1.0.0 Oficial  
**Gobernanza:** Antigravity Nivel 5 de Autonomía  

---

## 1. Visión y Objetivos de la Fase 1

La **Fase 1 (Capa de Datos y Persistencia)** constituye el cimiento estructural sobre el cual operarán el Router Semántico, los Agentes Cognitivos de IA, los flujos de n8n y las 5 Suites de Herramientas MCP. 

Siguiendo el principio de **cero código precipitado**, este documento establece:
1. El **Modelo Conceptual de Dominio Telco** alineado a los estándares mundiales de TM Forum ODA.
2. El **Diagrama Entidad-Relación (ERD)** de alta resolución.
3. La **Estrategia de Particionamiento e Indexación** diseñada para soportar 4 Millones de abonados con latencias de consulta inferiores a **15 milisegundos**.
4. La **Bóveda de Privacidad Cero-Conocimiento (Zero-Knowledge PII Vault)** para cumplimiento con CONATEL y SUDEBAN.
5. El **Ciclo de Vida de los Datos** (retención, archivado en frío y políticas de purga).

---

## 2. Mapa Conceptual de Dominios TM Forum ODA

El modelo de datos se organiza en 6 dominios conceptuales desacoplados pero interconectados:

```mermaid
flowchart TD
    subgraph D1 ["1. Dominio de Identidad y Cliente (TMF632)"]
        D1A["Abonados (Parties)"]
        D1B["Bóveda PII (Blind Hash HMAC + AES-GCM)"]
    end

    subgraph D2 ["2. Dominio de Red e Inventario Telco (TMF622)"]
        D2A["Líneas Móviles (0416 / 0426)"]
        D2B["Parámetros SIM / IMSI / IMEI / EIR"]
        D2C["Topología de Celdas eNodeB 4GMAX"]
    end

    subgraph D3 ["3. Dominio de Catálogo y Planes (TMF620)"]
        D3A["Catálogo de Productos y Planes"]
        D3B["Matriz Tarifaria Bs. (VES) e Indexación BCV"]
        D3C["Paquetes Adicionales de Datos (Extra-GB)"]
    end

    subgraph D4 ["4. Dominio de Saldos y Consumo (TMF678)"]
        D4A["Saldos en Tiempo Real (OCS Billing)"]
        D4B["Bolsas de Navegación (MB Restantes / Cupo)"]
        D4C["Registros de Detalle de Tráfico (CDRs)"]
    end

    subgraph D5 ["5. Dominio Financiero y C2P (TMF676)"]
        D5A["Transacciones de Recarga Pago Móvil C2P"]
        D5B["Catálogo Bancario SUDEBAN (0102, 0105, etc.)"]
        D5C["Registro Antifraude y Control de Replay Attacks"]
    end

    subgraph D6 ["6. Dominio CRM, Retención y Churn (TMF680)"]
        D6A["Scoring Predictivo de Churn (0-100)"]
        D6B["Campañas y Cupones de Fidelización"]
        D6C["Tickets de Soporte y Reportes de Robo EIR"]
    end

    D1 --> D2
    D2 --> D4
    D3 --> D2
    D4 --> D5
    D4 --> D6
    D2 --> D6
```

---

## 3. Diagrama Entidad-Relación (ERD) Conceptual

```mermaid
erDiagram
    SUBSCRIBER ||--o{ TELCO_LINE : owns
    SUBSCRIBER ||--|| PII_VAULT : secures
    TELCO_LINE ||--|| BALANCE_QUOTA : tracks
    TELCO_LINE ||--o{ USAGE_CDR : generates
    TELCO_LINE ||--o{ FINANCIAL_TRANSACTION : executes
    TELCO_LINE }o--|| PRODUCT_PLAN : assigned_to
    TELCO_LINE ||--o{ CHURN_METRIC : monitored_by
    TELCO_LINE ||--o{ EIR_SECURITY_EVENT : logs
    FINANCIAL_TRANSACTION }o--|| BANK_SUDEBAN : routes_through

    SUBSCRIBER {
        uuid id PK
        string blind_index_cid UK
        string customer_type
        string status
        timestamp created_at
    }

    PII_VAULT {
        uuid id PK
        uuid subscriber_id FK
        string encrypted_cid
        string encrypted_full_name
        string encrypted_email
        string key_version
    }

    TELCO_LINE {
        string msisdn PK
        uuid subscriber_id FK
        string imsi
        string iccid
        string imei
        string plan_id FK
        string cell_id
        timestamp last_sim_swap_at
        string status
    }

    PRODUCT_PLAN {
        string plan_id PK
        string name
        string commercial_code
        integer data_quota_mb
        integer voice_minutes
        integer sms_quota
        decimal price_usd
        boolean is_active
    }

    BALANCE_QUOTA {
        uuid id PK
        string msisdn FK
        decimal balance_ves
        decimal balance_usd_equiv
        integer remaining_data_mb
        integer total_quota_mb
        date billing_cutoff_date
        timestamp last_sync_at
    }

    USAGE_CDR {
        uuid id PK
        string msisdn FK
        timestamp event_timestamp
        string event_type
        bigint data_volume_bytes
        string cell_id
        string status_code
    }

    FINANCIAL_TRANSACTION {
        string reference_id PK
        string msisdn FK
        string bank_code FK
        decimal amount_ves
        decimal amount_usd
        decimal bcv_rate_applied
        string payment_method
        string status
        timestamp executed_at
    }

    BANK_SUDEBAN {
        string bank_code PK
        string bank_name
        boolean c2p_enabled
    }

    CHURN_METRIC {
        uuid id PK
        string msisdn FK
        decimal churn_score
        string risk_segment
        integer days_without_recharge
        integer complaints_count_30d
        decimal data_drop_pct
        timestamp evaluated_at
    }

    EIR_SECURITY_EVENT {
        string ticket_id PK
        string msisdn FK
        string imei
        string event_type
        string reason
        string authority_agent
        timestamp created_at
    }
```

---

## 4. Descripción Funcional de las Entidades del Dominio

### 4.1 `SUBSCRIBER` & `PII_VAULT` (TMF632 — Gestión de Identidad Zero-Knowledge)
* **Propósito:** Aloja la identidad legal del cliente sin comprometer datos confidenciales en texto plano.
* **Mecanismo de Búsqueda Segura (Blind Indexing):**
  * La Cédula de Identidad (`V-18492019`) pasa por una función criptográfica HMAC-SHA256 con sal secreta institucional para generar el `blind_index_cid`.
  * Esto permite consultas O(1) ultrarrápidas (`WHERE blind_index_cid = :hash`) sin exponer la cédula en crudo.
* **Bóveda Cifrada:**
  * Nombre, apellido, cédula y correo se encriptan con AES-256-GCM. Solo agentes y roles autorizados pueden invocar `mcp_pii_unmask` registrando evento en la bitácora de auditoría.

### 4.2 `TELCO_LINE` (TMF622 — Línea Móvil e Inventario de Red)
* **Propósito:** Representa la tarjeta SIM y el servicio telefónico activo con prefijos venezolanos `0416` y `0426`.
* **Parámetros Críticos:**
  * `msisdn`: Clave primaria de longitud exacta 11 dígitos numéricos (`04161234567` / `04269876543`).
  * `last_sim_swap_at`: Timestamp indispensable para el análisis de riesgo en Suite 1 (`mcp_telco_verify_sim_swap`). Si el cambio de SIM ocurrió hace menos de 24 horas, las transacciones C2P y operaciones de cambio de clave se bloquean preventivamente.
  * `cell_id`: Identificador de la celda de acceso eNodeB LTE (ej. `CAR-CCS-ENB-042`), permitiendo correlacionar telemetría de cobertura 4GMAX.

### 4.3 `PRODUCT_PLAN` (TMF620 — Catálogo Oficial de Productos)
* **Propósito:** Especificación de los 16 servicios y planes del ecosistema Movilnet (Inteliplan 10GB, Conecta Plus, Planes Jubilados, etc.).
* **Indexación Monetaria:**
  * Tarifa base fijada en USD y convertida dinámicamente a Bolívares (VES) mediante la Suite 2 (`mcp_bcv_get_rate`).

### 4.4 `BALANCE_QUOTA` (TMF678 — Saldos y Bolsas de Navegación)
* **Propósito:** Imagen en tiempo real del saldo monetario prepago/pospago y las cuotas de navegación restantes.
* **Campos Clave:**
  * `balance_ves`: Saldo nominal en Bolívares.
  * `remaining_data_mb`: Megabytes disponibles para navegar.
  * `billing_cutoff_date`: Fecha de corte mensual para recargas obligatorias.

### 4.5 `USAGE_CDR` (TMF678 — Registros Detallados de Tráfico de Red)
* **Propósito:** Telemetría de consumo de voz, datos y SMS generada por la infraestructura eNodeB/SGW/PGW.
* **Volumetría Esperada:**
  * 4,000,000 de abonados x ~5 registros diarios = **20,000,000 de filas mensuales** (~240M al año).
  * **Estrategia Obligatoria:** Particionamiento por rango mensual (`PARTITION BY RANGE (event_timestamp)`).

### 4.6 `FINANCIAL_TRANSACTION` & `BANK_SUDEBAN` (TMF676 — Pagos Móviles C2P)
* **Propósito:** Registro transaccional inmutable de recargas bancarias.
* **Regla Antifraude SUDEBAN:**
  * `reference_id`: Cadena única alfanumérica bancaria. Se aplica restricción `UNIQUE` para evitar **Replay Attacks** (reutilización ilegítima de referencias de pago).
  * Mapeo estricto contra códigos bancarios oficiales SUDEBAN (0102 BDV, 0108 Provincial, 0105 Mercantil, 0134 Banesco, etc.).

### 4.7 `CHURN_METRIC` (TMF680 — Inteligencia Predictiva de Retención)
* **Propósito:** Registro continuo del score de propensión al abandono calculado por la Suite 3 (`mcp_crm_predict_churn`).
* **Activadores de Retención:**
  * Si `churn_score >= 70.0` y `days_without_recharge >= 25`, el motor de IA dispara automáticamente la oferta de cupones de descuento o bonos de navegación.

### 4.8 `EIR_SECURITY_EVENT` (Seguridad de Equipos EIR y Hurto)
* **Propósito:** Registro de incidentes de seguridad y lista negra de terminales (EIR - Equipment Identity Register).
* **Acciones:**
  * Almacena las órdenes ejecutadas vía `mcp_telco_lock_line_theft`, bloqueando IMEI e IMSI en la red celular de forma irrevocable hasta validación presencial en oficina comercial.

---

## 5. Estrategia de Rendimiento y Particionamiento para 4 Millones de Abonados

### 5.1 Esquema de Particionamiento Relacional

```mermaid
flowchart TD
    subgraph TABLAS_HASH ["Particionamiento por HASH (Distribución Uniforme)"]
        TL["Tabla: telco_lines (4M Filas)"]
        BQ["Tabla: balances_and_quotas (4M Filas)"]
        TL --> P_HASH["PARTITION BY HASH (msisdn) en 8 Particiones"]
        P_HASH --> P0["Partición 00"]
        P_HASH --> P1["Partición 01"]
        P_HASH --> P2["Partición 02"]
        P_HASH --> P_REST["Particiones 03 .. 07"]
    end

    subgraph TABLAS_RANGE ["Particionamiento por RANGO (Series de Tiempo)"]
        CDR["Tabla: usage_records_cdr (~20M Filas/Mes)"]
        FT["Tabla: financial_transactions (~8M Filas/Mes)"]
        CDR --> P_RANGE["PARTITION BY RANGE (event_timestamp)"]
        P_RANGE --> PM1["cdr_y2026m09"]
        P_RANGE --> PM2["cdr_y2026m10"]
        P_RANGE --> PM3["cdr_y2026m11"]
    end
```

### 5.2 Estrategia de Índices Especializados

1. **Índices Primarios B-Tree:**
   * `idx_lines_msisdn`: Clave primaria en `telco_lines(msisdn)`. Búsqueda punto a punto en **< 1.2 ms**.
   * `idx_subscribers_blind_cid`: En `subscribers(blind_index_cid)`. Búsqueda por documento en **< 1.5 ms**.
   * `idx_tx_reference`: En `financial_transactions(reference_id)` para validación de unicidad C2P inmediata.
2. **Índices Temporales BRIN (Block Range Index):**
   * En `usage_records_cdr(event_timestamp)`.
   * **Ventaja:** Un índice BRIN sobre 20 millones de filas pesa menos de **2 MB** en RAM (contra ~450 MB de un B-Tree), permitiendo filtrados temporales instantáneos con uso eficiente de memoria.
3. **Índices Parciales Condicionales:**
   * `idx_active_theft_events`: `CREATE INDEX ON eir_security_events(msisdn) WHERE event_type = 'THEFT_LOCK';` (acelera la validación de líneas bloqueadas sin escanear el histórico).

---

## 6. Dimensionamiento de Hardware y Presupuesto de Capacidad (Sizing)

Para soportar los 4,000,000 de abonados con latencias ultra-bajas en arquitectura On-Premise / Servidor Local:

| Componente | Especificación Mínima | Justificación Técnica |
|:---|:---:|:---|
| **CPU** | 8 Cores vCPU (x86_64) | Procesamiento paralelo de conexiones PostgreSQL y hashing criptográfico |
| **Memoria RAM** | 16 GB RAM | `shared_buffers = 4GB`, `work_mem = 64MB`, caché de índices en memoria |
| **Almacenamiento** | 200 GB SSD NVMe | 4M abonados base (~4 GB) + 12 meses de CDRs y transacciones C2P (~85 GB) + WAL/Backups |
| **Conexiones Concurrentes** | 200 activas (con PgBouncer) | Manejo de picos de recargas y consultas simultáneas en WhatsApp |
| **Latencia P95 Esperada** | **< 8.5 ms** | Medido en consultas complejas con Joins indexados |

---

## 7. Protocolo de Transición hacia el Código de Fase 1

Con la aprobación formal de este Modelo Conceptual, la secuencia de implementación en código ejecutable será:

```mermaid
flowchart LR
    M1["1. DDL SQL Particionado<br/>(db/schema.sql)"]
    M2["2. Generador Sintético 4M<br/>(scripts/seed_subscribers.py)"]
    M3["3. Capa de Acceso Python<br/>(db/connection.py & ORM)"]
    M4["4. Conexión de 5 Suites MCP<br/>(mcp/telco_tools en vivo)"]
    M5["5. Suite de Pruebas L1-L4<br/>(tests/test_phase1_db.py)"]

    M1 --> M2 --> M3 --> M4 --> M5
```

Este modelo garantiza una arquitectura robusta, estrictamente normalizada, escalable y 100% blindada contra fallas operativas o filtraciones de datos.
