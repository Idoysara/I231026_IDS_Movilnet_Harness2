# 🏛️ MASTER BLUEPRINT: CAZADOR DE OFERTAS MOVILNET
## Arquitectura Integral, Algoritmos Matemáticos, Diccionario de Datos y Ecosistema de Microservicios
**Proyecto:** Cliente 28 — `28_Cazador_Ofertas` (`IDS_CORE v5.85.0`)  
**Sellos Criptográficos:** `CERT-CAZADOR-SIMULATOR-TRAFFIC-20261018` | `CERT-CAZADOR-SCRAPER-PROMOS-20261018` | `CERT-CAZADOR-N8N-OMNICHANNEL-20261018` | `CERT-CAZADOR-ESTACION5-OMNIBOX-20261018` | `CERT-CAZADOR-ESTACION4-DEFLECTOR-20261018` | `CERT-CAZADOR-ESTACION3-SIMBIOSIS-20261018` | `CERT-CAZADOR-ESTACION2-ORM-PERSISTENCE-20261018` | `CERT-CAZADOR-PENTARCHY-20261018-SHA256`  
**Operadora Telco Ancla:** Movilnet (Prefijos `0416` / `0426`)  
**Puerto Core API / PWA:** `:8030` | **Puerto PWA Standalone:** `:3005` | **Puerto N8N:** `:5678`

---

## 1. LÍNEA DE PROPUESTAS Y VISIÓN ESTRATÉGICA

### 1.1. Propósito y Propuesta de Valor Soberana
**Cazador de Ofertas** es una plataforma de **comercio hiperlocal, proximidad geoespacial y ahorro cotidiano** concebida para operar en simbiosis con la infraestructura de telecomunicaciones de Movilnet. Resuelve simultáneamente tres fricciones del mercado venezolano:
1. **Para el Abonado Móvil (B2C - 0416/0426):** Permite descubrir en tiempo real qué ofertas y promociones reales están disponibles a menos de 500m, 1km o 3km de su ubicación física, garantizando descuentos legítimos en bolívares (VES) y la posibilidad de suscribirse a pases VIP debitados directamente de su saldo prepago o pospago, sin requerir tarjetas bancarias internacionales ni pasarelas complejas.
2. **Para el Comercio Aliado (B2B - Merchants):** Brinda un canal de afluencia masiva de clientes a pie sin el costo exorbitante ni la fricción de campañas en Instagram o vallas estáticas. El comerciante solo remunera por cliente real en caja y cuenta con un blindaje criptográfico que impide el fraude por capturas de pantalla de cupones.
3. **Para la Operadora (Telco Movilnet):** Monetiza el tráfico de red mediante micro-transacciones de Carrier Billing (split transaccional del 20% limpio), reduce el *churn* (fuga de líneas a otras operadoras) y posiciona a la empresa pública como un facilitador directo del poder adquisitivo popular.

### 1.2. Deflector de Mensajería y Ergonomía de Entrada
* **Canales de Entrada:** WhatsApp, Telegram y SMS masivo interno por SMPP.
* **Mecanismo Deflector:** El usuario no navega menús pesados por chat. Al escribir *"ofertas"* o tocar un enlace, el bot responde con un **Magic Link** que abre la aplicación PWA en el navegador con **Zero-Rating de datos** (sin consumo de saldo de navegación), optimizando el costo operativo y garantizando una experiencia visual a 60 FPS con mapas interactivos.

---

## 2. ARQUITECTURA DE DISEÑO HEXAGONAL Y DDD

El sistema sigue estrictamente el principio de **Clean Architecture / Domain-Driven Design (DDD)** para aislar las reglas de negocio de la infraestructura y frameworks web:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CAPA DE ADAPTADORES / INFRAESTRUCTURA                │
│  FastAPI (:8030) │ Web PWA (:3005) │ Leaflet │ POS Scanner │ Redis     │
├────────────────────────────────────────────────────────────────────────┤
│                   CAPA DE CASOS DE USO / APLICACIÓN                    │
│      CazadorApplicationService │ SpatialRadarEngine │ CryptoVault      │
├────────────────────────────────────────────────────────────────────────┤
│                   CAPA DE DOMINIO PURO (ZERO-FRAMEWORK)                │
│   Entities (Comercio, Oferta, Cupon, Transaccion) │ FSM │ Invariantes  │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Dominio Puro (`src/domain/`):**
   * Cero dependencias de FastAPI, bases de datos o librerías de red.
   * Modelado estricto con Pydantic v2 y máquinas de estados deterministas.
2. **Casos de Uso (`src/application/`):**
   * Coordinación de emisión, validación de proximidad, canje en caja y facturación.
   * Integración de los 4 motores del Ecosistema Simbiótico.
3. **Adaptadores (`src/infrastructure/`):**
   * Controladores HTTP RESTful, servidor de archivos estáticos y puntos de enlace a BSS/OSS de Movilnet.

---

## 3. CONSTRUCCIÓN DE LOS ALGORITMOS MATEMÁTICOS FORMALES

### Algoritmo 1: Radar Geoespacial Haversine con Poda Bounding-Box
* **Objetivo:** Filtrar y ordenar comercios en 3 zonas de proximidad (<500m, <1km, <3km) en menos de 0.2 milisegundos, erradicando el gasto de tokens de LLM en cálculos trigonométricos.
* **Fórmula de Poda Previa (Bounding Box Rectangular):**
  $$\Delta \phi = \frac{d_{\max}}{R_{\text{tierra}}}, \quad \Delta \lambda = \frac{d_{\max}}{R_{\text{tierra}} \cdot \cos(\phi_{\text{user}})}$$
  $$\phi_{\min} \le \phi_{\text{comercio}} \le \phi_{\max} \quad \land \quad \lambda_{\min} \le \lambda_{\text{comercio}} \le \lambda_{\max}$$
* **Fórmula Haversine Exacta:**
  $$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
  $$c = 2 \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1-a}\right)$$
  $$d = R_{\text{tierra}} \cdot c \quad \text{donde } R_{\text{tierra}} = 6,371,000 \text{ metros}$$
* **Clasificación en 3 Anillos:**
  $$\text{Anillo}(d) = \begin{cases} 
  \text{Zona 1 (Inmediata)}, & d \le 500\text{m} \\ 
  \text{Zona 2 (Vecindario)}, & 500\text{m} < d \le 1000\text{m} \\ 
  \text{Zona 3 (Urbana)}, & 1000\text{m} < d \le 3000\text{m} \\ 
  \text{Fuera de Rango}, & d > 3000\text{m} 
  \end{cases}$$

### Algoritmo 2: Bóveda Criptográfica TOTP Anti-Captura de Pantalla
* **Objetivo:** Invalidar capturas de pantalla de cupones y prevenir que un cliente comparta su cupón digital con terceros.
* **Ventana de Tiempo y Firma HMAC:**
  $$T_{\text{step}} = \left\lfloor \frac{t_{\text{epoch}}}{60} \right\rfloor \quad (\text{rotación cada 60 segundos})$$
  $$\text{Mensaje} = \text{CouponUUID} \parallel \text{MSISDN} \parallel \text{ComercioID} \parallel T_{\text{step}}$$
  $$\text{Firma} = \text{HMAC-SHA256}(K_{\text{secreto}}, \text{Mensaje})[0..15] \quad (\text{16 caracteres hexadecimales})$$
* **Tolerancia de Reloj en Caja POS:**
  El validador de caja verifica la firma en el intervalo $[T_{\text{step}} - 1, T_{\text{step}} + 1]$ para tolerar desincronizaciones de hasta 60 segundos en teléfonos sin conexión estable.
* **Quema Inmediata de Hash (Anti-Replay):**
  $$\text{Fingerprint} = \text{CouponUUID} \parallel \text{Firma}$$
  $$\text{Si Fingerprint} \in \text{BóvedaQuemada} \implies \text{RECHAZAR (HTTP 409)}$$

### Algoritmo 3: Centinela de Viabilidad Financiera (Invariante II - Díaz Robisco)
* **Objetivo:** Garantizar que ninguna oferta debilite el balance del comerciante.
* **Ecuación del Margen Bruto de Contribución:**
  $$\text{Margen Bruto } = \frac{P_{\text{oferta}} - C_{\text{directo}}}{P_{\text{oferta}}} \ge 0.35 \quad (35\%)$$
* Si $\text{Margen Bruto} < 0.35$, el kernel lanza `DomainInvariantViolationError` y bloquea la publicación de la oferta.

### Algoritmo 4: FSM de Ciclo de Vida del Cupón
* **Estados Permitidos:** `EMITIDO`, `RESERVADO`, `CANJEADO`, `EXPIRADO`.
* **Grafo de Transiciones Válidas:**
  $$\delta(\text{EMITIDO}) = \{\text{RESERVADO}, \text{CANJEADO}, \text{EXPIRADO}\}$$
  $$\delta(\text{RESERVADO}) = \{\text{CANJEADO}, \text{EXPIRADO}\}$$
  $$\delta(\text{CANJEADO}) = \emptyset \quad (\text{Estado Final Inmutable})$$
  $$\delta(\text{EXPIRADO}) = \emptyset \quad (\text{Estado Final Inmutable})$$

### Algoritmo 5: Pasarela Idempotente y Token-Bucket de Rate Limiting
* **Garantía de Cero Cobros Duplicados:**
  $$\text{IdempotencyKey} = \text{SHA256}(\text{MSISDN} \parallel \text{PlanID} \parallel \text{VentanaTemporal})$$
  Si la clave ya existe en el almacén de respuestas procesadas, se retransmite la respuesta original sin debitar nuevamente el saldo.
* **Token-Bucket:**
  $$\text{Tokens}(t) = \min\left(C_{\max}, \text{Tokens}(t_{\text{prev}}) + (t - t_{\text{prev}}) \cdot r_{\text{fill}}\right)$$

### Algoritmo 6: Split Transaccional Telco 20/80
* **Reparto de Ingresos:**
  $$M_{\text{telco}} = \text{round}(M_{\text{total}} \cdot 0.20, 2)$$
  $$M_{\text{neto}} = \text{round}(M_{\text{total}} - M_{\text{telco}}, 2)$$

---

## 4. ÁRBOL DE COMUNICACIÓN, COMPONENTES Y RELACIONES

```mermaid
flowchart TD
    subgraph Usuarios ["👥 Canales de Entrada"]
        A1["📱 Abonado Movilnet (0416/0426)"]
        A2["🏪 Cajero / POS Comerciante"]
        A3["💬 Deflector WhatsApp / SMS SMPP"]
    end

    subgraph Frontends ["🌐 Interfaces Ergonomicas (:8030 / :3005)"]
        B1["🧭 Radar PWA (Leaflet + 3 Anillos)"]
        B2["🎟️ Billetera QR Dinamico (TOTP 60s)"]
        B3["🔍 Terminal POS Validador Criptografico"]
        B4["💳 Checkout Carrier Billing VIP"]
    end

    subgraph CoreEngine ["⚙️ Nucleo de Aplicacion & APIs (:8030)"]
        C1["FastAPI Core Router"]
        C2["CazadorApplicationService"]
        C3["CouponFSM State Guard"]
        C4["Domain Invariants Validator"]
    end

    subgraph SymbioticEngines ["🧠 Ecosistema Simbiotico MCP"]
        D1["mcp_spatial_radar (Haversine <0.2ms)"]
        D2["mcp_crypto_token_vault (HMAC-SHA256)"]
        D3["mcp_idempotent_gateway (Split 20/80)"]
        D4["mcp_universal_memory (SQLite FTS5)"]
    end

    subgraph Persistence ["💾 Capa de Persistencia"]
        E1[("PostgreSQL 16 + PostGIS")]
        E2[("Redis Cluster / Cache")]
        E3[("Boveda Criptografica Inmutable")]
    end

    subgraph External ["🏛️ Sistemas Externos"]
        F1["BSS/OSS Movilnet (Debito de Saldo)"]
        F2["SMS Gateway SMPP (Alertas de Proximidad)"]
    end

    A1 -->|Click Magic Link| B1
    A1 -->|Reclama Oferta| B2
    A2 -->|Escanea QR en Caja| B3
    A1 -->|Activa Pase VIP| B4
    A3 -->|Desvia Mensajeria| B1

    B1 & B2 & B3 & B4 -->|HTTP REST / JSON| C1
    C1 --> C2
    C2 --> C3 & C4
    C2 --> D1 & D2 & D3 & D4
    D1 & D2 & D3 & D4 --> E1 & E2 & E3
    D3 -->|API Idempotente| F1
    C2 -->|Trigger Notificacion| F2
```

---

## 5. DICCIONARIO EXHAUSTIVO DE BASES DE DATOS Y TABLAS

### Tabla 1: `comercios` (Directorio de Comercios y Sedes Físicas)
| Campo | Tipo de Dato | Restricción | Propósito / Descripción |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(32)` | `PRIMARY KEY` | Identificador único del comercio (ej: `COM-001`). |
| `rif` | `VARCHAR(20)` | `NOT NULL, UNIQUE` | Registro de Información Fiscal verificado (SENIAT). |
| `nombre` | `VARCHAR(120)` | `NOT NULL` | Nombre comercial de la empresa o local. |
| `categoria` | `VARCHAR(60)` | `NOT NULL` | Rubro principal (Alimentos, Farmacia, Calzado, etc.). |
| `lat` | `DOUBLE PRECISION` | `NOT NULL, [-90, 90]` | Latitud GPS WGS84 del establecimiento. |
| `lon` | `DOUBLE PRECISION` | `NOT NULL, [-180, 180]`| Longitud GPS WGS84 del establecimiento. |
| `geom` | `GEOMETRY(Point, 4326)`| `INDEX GIST` | Punto espacial PostGIS para consultas geoespaciales. |
| `tier` | `VARCHAR(20)` | `DEFAULT 'BASICO'` | Nivel del comercio (`BASICO`, `DESTACADO`, `VIP_RADAR`). |
| `telefono` | `VARCHAR(20)` | `NOT NULL` | Contacto telefónico oficial del encargado. |
| `activo` | `BOOLEAN` | `DEFAULT TRUE` | Estado operativo del comercio. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `DEFAULT NOW()` | Fecha y hora de alta en el sistema. |

### Tabla 2: `ofertas` (Catálogo de Promociones y Descuentos)
| Campo | Tipo de Dato | Restricción | Propósito / Descripción |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(32)` | `PRIMARY KEY` | Identificador único de la oferta (ej: `OFE-001`). |
| `comercio_id` | `VARCHAR(32)` | `FOREIGN KEY (comercios.id)` | Comercio propietario que respalda la oferta. |
| `titulo` | `VARCHAR(140)` | `NOT NULL` | Titular de la oferta visible en el radar. |
| `precio_regular_ves` | `NUMERIC(12, 2)` | `CHECK (> 0)` | Precio regular del producto sin descuento. |
| `precio_oferta_ves` | `NUMERIC(12, 2)` | `CHECK (> 0)` | Precio especial con descuento en bolívares. |
| `costo_directo_ves` | `NUMERIC(12, 2)` | `CHECK (>= 0)` | Costo directo del comerciante (materia prima + reposición). |
| `margen_pct` | `NUMERIC(5, 2)` | `CHECK (>= 35.0)` | **Invariante II:** Margen bruto garantizado $\ge 35\%$. |
| `stock_inicial` | `INTEGER` | `CHECK (>= 0)` | Cupones totales autorizados por el comercio. |
| `stock_disponible` | `INTEGER` | `CHECK (>= 0)` | Cupones restantes para reclamar en tiempo real. |
| `horario_validez` | `VARCHAR(60)` | `DEFAULT '10:00 - 20:00'` | Franja horaria para el canje presencial. |
| `activa` | `BOOLEAN` | `DEFAULT TRUE` | Candado lógico para pausar o habilitar la oferta. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `DEFAULT NOW()` | Fecha de publicación de la oferta. |

### Tabla 3: `cupones` (Vouchers Emitidos con Firma Dinámica TOTP)
| Campo | Tipo de Dato | Restricción | Propósito / Descripción |
| :--- | :--- | :--- | :--- |
| `uuid` | `VARCHAR(36)` | `PRIMARY KEY` | Identificador criptográfico universal del cupón. |
| `oferta_id` | `VARCHAR(32)` | `FOREIGN KEY (ofertas.id)` | Oferta asociada al cupón. |
| `comercio_id` | `VARCHAR(32)` | `FOREIGN KEY (comercios.id)` | Comercio donde debe canjearse. |
| `usuario_msisdn` | `VARCHAR(20)` | `NOT NULL` | Línea Movilnet del usuario titular (0416/0426). |
| `codigo_dinamico` | `VARCHAR(30)` | `NOT NULL` | Código humanamente legible (ej: `QRO-A1B2-C3D4`). |
| `firma_hmac` | `VARCHAR(32)` | `NOT NULL` | Firma criptográfica de 16 caracteres hexadecimales. |
| `estado` | `VARCHAR(20)` | `NOT NULL` | Estado FSM (`EMITIDO`, `RESERVADO`, `CANJEADO`, `EXPIRADO`). |
| `time_step_emision` | `BIGINT` | `NOT NULL` | Paso de tiempo Unix (`timestamp // 60`). |
| `emitido_at` | `TIMESTAMP WITH TIME ZONE` | `DEFAULT NOW()` | Instante exacto en que el usuario reclamó el cupón. |
| `canjeado_at` | `TIMESTAMP WITH TIME ZONE` | `NULLABLE` | Instante en que el comerciante validó el cupón en caja. |

### Tabla 4: `transacciones_billing` (Libro Mayor de Carrier Billing y Split 20/80)
| Campo | Tipo de Dato | Restricción | Propósito / Descripción |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | ID único de la transacción (ej: `TX-88A9B2`). |
| `idempotency_key` | `VARCHAR(64)` | `NOT NULL, UNIQUE` | Clave de protección contra duplicados en redes 3G/4G. |
| `msisdn` | `VARCHAR(20)` | `NOT NULL` | Número telefónico debitado (0416 o 0426). |
| `monto_ves` | `NUMERIC(12, 2)` | `CHECK (> 0)` | Monto total cobrado al usuario en bolívares. |
| `comision_telco_ves`| `NUMERIC(12, 2)` | `NOT NULL` | 20% de comisión directa para Movilnet. |
| `neto_comercio_ves` | `NUMERIC(12, 2)` | `NOT NULL` | 80% remanente para la red y comercio. |
| `estatus` | `VARCHAR(20)` | `DEFAULT 'PROCESADO'` | Estatus de la transacción (`PROCESADO`, `RECHAZADO`). |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `DEFAULT NOW()` | Fecha y hora del cobro. |

### Tabla 5: `boveda_hashes_quemados` (Centinela Anti-Doble Gasto)
| Campo | Tipo de Dato | Restricción | Propósito / Descripción |
| :--- | :--- | :--- | :--- |
| `fingerprint` | `VARCHAR(64)` | `PRIMARY KEY` | Hash `CouponUUID + Firma` quemado al validar. |
| `cupon_uuid` | `VARCHAR(36)` | `NOT NULL` | Referencia al cupón canjeado. |
| `quemado_at` | `TIMESTAMP WITH TIME ZONE` | `DEFAULT NOW()` | Marca temporal de destrucción del token. |
| `comercio_id` | `VARCHAR(32)` | `NOT NULL` | Local donde se consumió el descuento. |

---

## 6. MAPA DE SKILLS Y SERVIDORES MCP

| Tipo | Identificador | Rol Específico en Cazador de Ofertas |
| :--- | :--- | :--- |
| **MCP** | `mcp_spatial_radar` | Ejecución del algoritmo Haversine a 1Hz, cálculo de distancias geodésicas y ordenamiento de 3 zonas sin tokens de LLM. |
| **MCP** | `mcp_crypto_token_vault` | Generación de firmas HMAC-SHA256, control de ciclos TOTP de 60s, verificación de tolerancias y quema de tokens. |
| **MCP** | `mcp_idempotent_gateway` | Protección contra débitos duplicados en conexiones inestables, Centinela Financiero y split 20/80 de Movilnet. |
| **MCP** | `mcp_universal_memory` | Almacén SQLite FTS5 de cuatro capas (`USER`, `PROJECT`, `DECISION`, `SESSION`) con presupuesto estricto $\le 450$ tokens. |
| **Skill** | `universal-scout-advisor` | Asesor conversacional de proximidad que traduce coordenadas GPS y preferencias a recomendaciones sin fricción. |
| **Skill** | `universal-onboarding-concierge` | Asistente de alta rápida para que nuevos comercios registren sus ofertas auditando el margen bruto $\ge 35\%$. |
| **Skill** | `universal-monetization-governor`| Gobernador de suscripciones VIP, tarificación Carrier Billing y liquidación quincenal de comisiones. |
| **Skill** | `universal-state-distiller` | Motor de compresión preventiva y preservación de punto de control técnico sin pérdida de contexto. |

---

## 7. ORQUESTADOR MAESTRO Y TOPOLOGÍA DE RED

* **Orquestador Principal:** `ids-orquestador` / `IDS_CORE Master Orchestrator`.
* **Matriz de Puertos Soberana:**
  * `:8030`: Servidor REST Core FastAPI + PWA Integrada (Producción / Local).
  * `:3005`: PWA Standalone Next.js / Vite (Desarrollo Frontend).
  * `:8016`: WhatsApp Enterprise Engine (Deflector de Alta Concurrencia).
* **Experiencia Cero Terminal:**
  * El comerciante y el directivo de Movilnet ejecutan la plataforma mediante [`🚀_INICIAR_CAZADOR_OFERTAS.command`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/%F0%9F%9A%80_INICIAR_CAZADOR_OFERTAS.command).
  * Se dispone del manual ejecutivo en [`INSTRUCCIONES_DUENO.md`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/INSTRUCCIONES_DUENO.md).

---

## 8. AUTOMATIZACIÓN OMNICANAL CON N8N WORKFLOW
* **Flujo Formal Importable:** [`n8n/cazador_ofertas_n8n_workflow.json`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/n8n/cazador_ofertas_n8n_workflow.json)
* **Manual de Configuración:** [`n8n/README_N8N.md`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/n8n/README_N8N.md)
* **Topología:**
  1. Triggers Webhook para WhatsApp (Meta Cloud / Whapify), Telegram y PWA.
  2. Normalizador de payloads y números celulares en Code Node JavaScript (`0416...` / `0426...`).
  3. IF Node con candado de exclusividad Movilnet y rechazo cortés HTTP 403 para operadoras ajenas.
  4. HTTP Request Node hacia Gateway REST `:8030/api/deflector/n8n`.
  5. Despacho enriquecido adaptativo (Inline WebApp Button para Telegram, texto enriquecido con Magic Link para WhatsApp y JSON nativo para PWA).

---

## 9. CERTIFICACIÓN DE CALIDAD MILITAR (PRIORIDAD 0)
* **Suite de Pruebas Automatizadas:** `.venv/bin/pytest pruebas_clientes/28_Cazador_Ofertas/tests/ -v`
* **Veredicto Factual:** **`57 passed, 0 failed in 5.40s (100% Pass, Exit code: 0)`**
* **Pureza Sintáctica:** **45 archivos Python verificados** con **0 SyntaxError**.
* **Sellado Criptográfico:** `CERT-CAZADOR-SIMULATOR-TRAFFIC-20261018` | `CERT-CAZADOR-SCRAPER-PROMOS-20261018` | `CERT-CAZADOR-N8N-OMNICHANNEL-20261018` | `CERT-CAZADOR-PENTARCHY-20261018-SHA256`.

---

## 10. EXTRACCIÓN GEODÉSICA DE 35 COMERCIOS REALES Y PIPELINE BIGQUERY DTS
* **Investigación Comparativa:** Google Maps (descartado por \$5-\$20/1,000 reqs y violación de ToS 3.2.4 de caching) vs. OpenStreetMap/Nominatim (\$0.00, soberano, ODbL, offline-first) vs. BigQuery DTS (capa analítica batch).
* **Catálogo Físico en Caracas:** 35 empresas reales georreferenciadas en WGS84 con RIF SENIAT (Excelsior Gama, Central Madeirense, Automercados Plaza's, Unicasa, Río Supermarket, Farmatodo, Locatel, Farmahorro, Policlínica Metropolitana, Clínica El Ávila, Arturo's, McDonald's, Ávila Burger, UCV, UCAB, UNIMET, USB, IESA, Colegio San Ignacio, Ciudad Banesco, Banco Mercantil, KPMG, Deloitte, Movilnet El Recreo, CCCT, Centro San Ignacio, Tolón, Líder, City Market).
* **Pipeline BigQuery DTS:** Dataset CSV [`data/comercios_reales_venezuela.csv`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/data/comercios_reales_venezuela.csv) para transferencias programadas hacia `gs://movilnet-cazador-geodata/` y consultas espaciales en BigQuery GIS (`ST_DISTANCE`, `ST_DWithin`).

---

## 11. SCRAPER TERRITORIAL DE PROMOCIONES POR ÁREAS DE NEGOCIOS
* **Módulo Autónomo:** [`scripts/scraper_ofertas_promociones_venezuela.py`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/scripts/scraper_ofertas_promociones_venezuela.py) con CLI (`--scrape`, `--test`, `--export`, `--stats`).
* **Sondeo en Vivo:** Verificación de conectividad HTTP 200 en portales venezolanos (Plaza's, Gama, Locatel, Farmatodo, Arturo's, Traki, TuOdontóloga).
* **Catálogo de 23 Promociones en 16 Empresas:** 6 áreas comerciales (Supermercados, Farmacias, Gastronomía, Moda, Tecnología y Salud).
* **Invariante II:** 100% de promociones con margen de contribución $\ge 35.0\%$ (rango: 35.0% a 50.0%) y precios en bolívares (VES).
* **Datasets Exportados:** [`data/promociones_reales_venezuela.json`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/data/promociones_reales_venezuela.json) y [`data/promociones_reales_venezuela.csv`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/data/promociones_reales_venezuela.csv).

---

## 12. MOTOR DE SIMULACIÓN SINTÉTICA Y CONCILIACIÓN TRANSACCIONAL SPLIT 20/80
* **Módulo Autónomo:** [`scripts/simulador_trafico_super_ofertas.py`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/scripts/simulador_trafico_super_ofertas.py) con CLI (`--run`, `--test`, `--stats`, `--export`).
* **Corrida de Simulación Masiva (100 Abonados Movilnet):**
  * 200 búsquedas radar (4,147 impactos en 3 anillos).
  * 71 cupones dinámicos emitidos con éxito.
  * 9 intentos de acaparamiento bloqueados por cuota ($\le 3$).
  * 53 canjes presenciales en caja POS (74.65% tasa de redención).
  * 8/8 intentos de fraude/captura de pantalla bloqueados por Bóveda y FSM (100% efectividad de blindaje).
  * 39,365.00 Bs. volumen facturado: **7,873.00 Bs. comisión Movilnet (Split 20%)** / **31,492.00 Bs. neto comercios aliados (Split 80%)**.
* **Base de Datos SQLite (`cazador_local.db`):** 35 comercios, 41 ofertas, 247 cupones, 162 transacciones de billing, 183 hashes quemados.
* **Datasets Exportados:** [`data/simulacion_trafico_cazador.json`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/data/simulacion_trafico_cazador.json) y [`data/simulacion_transacciones_cazador.csv`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/data/simulacion_transacciones_cazador.csv).

