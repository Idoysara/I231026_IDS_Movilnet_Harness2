# 🌐 Arquitectura de Ecosistema Multi-Servicio y Super-App Telco (B2B2C)
## Proyecto: `AI_Movilnet_300926` — Telecomunicaciones Movilnet C.A.
**Fundamento Estratégico:** *"La cuenta y línea Movilnet como Llave de Identidad y Pasarela de Servicios Propios y de Terceros (Banca, Turismo, Sitios Históricos, Servicios Públicos y Comercio)."*  
**Estándar:** TM Forum Open Digital Architecture (ODA) & Smart MCP Routing  
**Fecha:** 2026-09-30  
**Versión:** 1.0.0 Maestro  

---

## 1. ¿Por qué esto se DEBE considerar desde la FASE 0?

Si un proyecto de telecomunicaciones no concibe la extensibilidad multi-servicio desde su concepción (**Fase 0**), incurre en tres **fallas críticas de diseño (Deuda Técnica Fatal)**:

1. **Aislamiento de Datos y Privacidad Multi-Inquilino (Multi-Tenancy Zero-Trust):**  
   Una empresa aliada (un banco, una aerolínea o el Ministerio de Turismo) **jamás debe tener acceso a las tablas de facturación o contratos de Movilnet**. El modelo de datos debe diseñarse desde el inicio con particiones estrictas y muros de privacidad (*Privacy Walls*).
2. **Saturación de Contexto de la IA (Context Pollution):**  
   Si inyectas herramientas de saldo, pagos, turismo, parques y comercio en un solo prompt, el modelo de IA alucina, pierde precisión y el costo de tokens se dispara. Se requiere un **Enrutador Semántico de Dominios (Semantic Domain Router)** que active únicamente las herramientas del tema que el abonado está consultando.
3. **Escalabilidad de Alianzas Comerciales (Plugin-Play B2B):**  
   Nuevas empresas deben poder integrarse mediante contratos OpenAPI y servidores MCP estandarizados sin que tengamos que reescribir ni una sola línea del núcleo de Movilnet.

---

## 2. Benchmark Mundial: Casos de Éxito de Telco Super-Apps con IA

A nivel global, las operadoras líderes han dejado de ser simples "tuberías de datos" para convertirse en el **centro de vida digital de sus países**:

| Operadora / Aplicación | País / Usuarios | Modelo de Integración Multi-Servicio | Servicios de Terceros que Ofrece |
|:---|:---|:---|:---|
| **Reliance Jio (`MyJio / JioAI`)** | 🇮🇳 India<br/>*(450M abonados)* | **Super-App Conversacional:** La línea móvil es la identidad universal para servicios propios y aliados. | • `JioMart` (Compras en tiendas de barrio)<br/>• `JioUPI` (Pagos interbancarios)<br/>• Guía de turismo, templos y reservas de trenes<br/>• Salud digital y streaming |
| **Safaricom (`M-Pesa / Zuri AI`)** | 🇰🇪 Kenia / África<br/>*(32M abonados)* | **Chatbot Transaccional en WhatsApp y App:** Gestiona más del 50% del PIB del país en transacciones. | • Pago de servicios públicos (Agua, Electricidad)<br/>• Compra de entradas a Parques Nacionales (Safari)<br/>• Microcréditos bancarios y remesas<br/>• Pagos a pequeños comerciantes |
| **Telefónica / Movistar (`Aura`)** | 🇪🇸 España / LatAm<br/>*(100M+ abonados)* | **Ecosistema de "Living Apps":** La IA conecta el hogar y el móvil con marcas aliadas. | • Alianzas con Iberia (vuelos y turismo)<br/>• Banco Santander (finanzas)<br/>• El Corte Inglés (comercio electrónico)<br/>• Eventos culturales y carteleras locales |
| **Globe Telecom (`GCash / Gie AI`)** | 🇵🇭 Filipinas<br/>*(80M abonados)* | **Marketplace de Estilo de Vida:** De saldo celular a billetera de turismo y consumo nacional. | • Guía turística de islas y monumentos históricos<br/>• Delivery de comida con comercios aliados<br/>• Seguros de viaje y pagos QR en transporte |
| **Tencent (`WeChat Mini-Programs`)** | 🇨🇳 China<br/>*(1.3B usuarios)* | **Referente Universal de Super-App:** Identidad del número celular para interactuar con todo el país. | • Entradas a museos y sitios patrimoniales<br/>• Servicios gubernamentales y trámites<br/>• Comercio y transporte sin salir del chat |

---

## 3. Algoritmos y Patrones Clave en GitHub para este Enfoque

| Algoritmo / Repositorio | Tipo / Enfoque | Cómo se Aplica en Movilnet AI |
|:---|:---|:---|
| **`Semantic Router / MCPlex`**<br/>*(spak2005/smart-mcp, ModernOps888/mcplex)* | Enrutador Semántico de Herramientas MCP | Clasifica la intención del usuario en milisegundos mediante embeddings locales y conecta **exclusivamente el MCP del dominio pertinente** (Telco, Banca o Turismo). |
| **`TM Forum Open Digital Architecture (ODA)`**<br/>*(tmforum-rand/Open_API_And_Data_Model)* | Estándares Abiertos de Telecomunicaciones | Implementa los contratos universales:<br/>• **TMF620:** Catálogo de Productos y Servicios aliados.<br/>• **TMF680:** Motor de Recomendación contextual.<br/>• **TMF678:** Facturación unificada de servicios de valor agregado. |
| **`LangGraph Multi-Agent Supervisor`** | Orquestación Jerárquica de Agentes | Un agente supervisor determina si la consulta es de Movilnet o de un partner, delegando al subagente especialista sin mezclar contextos. |
| **`Outlines / Typesafe AI`** | Validación Estricta de Esquemas JSON | Asegura que las respuestas de empresas aliadas cumplan con el contrato de datos antes de ser mostradas al usuario en WhatsApp. |

---

## 4. Diagrama del Ecosistema B2B2C Movilnet AI Marketplace

```mermaid
flowchart TD
    subgraph CANAL ["Canal Único de Atención"]
        USER["📱 Abonado Movilnet (WhatsApp / Web)"]
    end

    subgraph ENRUTADOR ["Orquestador Semántico de Dominios (Semantic Domain Gateway)"]
        NLU["Capa de Percepción & Clasificación de Dominio"]
        ROUTER{"¿Qué necesita el usuario?"}
        NLU --> ROUTER
    end

    subgraph DOMINIO_TELCO ["1. Dominio Telecomunicaciones (Movilnet Core)"]
        MCP_TELCO["🔌 mcp_telco_tools<br/>(Saldo, Megas 4GMAX, Corte, Planes)"]
        DB_TELCO[("🗄️ BSS/OSS Movilnet (4M Abonados)")]
        MCP_TELCO --> DB_TELCO
    end

    subgraph DOMINIO_FINTECH ["2. Dominio Fintech & Pagos (Bancos Aliados)"]
        MCP_FIN["🔌 mcp_fintech_c2p<br/>(Pago Móvil, Débito en Cuenta)"]
        BANK_API["🏦 APIs Banco de Venezuela, Banesco, Patria"]
        MCP_FIN --> BANK_API
    end

    subgraph DOMINIO_TURISMO ["3. Dominio Turismo & Cultura (Guía Venezuela)"]
        MCP_TOUR["🔌 mcp_tourism_guide<br/>(Parques Nacionales, Sitios Históricos, Eventos)"]
        TOUR_DB[("🏛️ Inatur, Parques Nacionales (El Ávila, Mochima, Roraima), Museos")]
        MCP_TOUR --> TOUR_DB
    end

    subgraph DOMINIO_PARTNERS ["4. Dominio Comercio Aliado (VAS & Beneficios)"]
        MCP_VAS["🔌 mcp_partner_marketplace<br/>(Descuentos, Cupones, Servicios Públicos)"]
        PARTNERS_API["🛍️ Comercios, Cantv, Corpoelec, Cines"]
        MCP_VAS --> PARTNERS_API
    end

    USER --> NLU
    ROUTER -- "Saldo / Línea" --> MCP_TELCO
    ROUTER -- "Recarga / Pagos" --> MCP_FIN
    ROUTER -- "Qué visitar / Historia / Parques" --> MCP_TOUR
    ROUTER -- "Promociones / Servicios" --> MCP_VAS
```

---

## 5. Ejemplo Real de Interacción Multidominio en el Mismo Chat

```text
Usuario: "Hola, ¿cuántos megas me quedan?"
🤖 Asistente: "Le quedan 4.2 GB de su plan Inteliplan 10GB."

Usuario: "¿Y qué sitios turísticos me recomiendas visitar este fin de semana en Caracas?"
🤖 Asistente: (El Router activa el dominio de Turismo sin perder la sesión)
"En Caracas le recomiendo:
 🌿 Parque Nacional Warairarepano (El Ávila): Ideal para senderismo o teleférico.
 🏛️ Casco Histórico y Casa Natal del Libertador: Museos abiertos con entrada libre.
 🎭 Complejo Cultural Teresa Carreño: Cartelera cultural y exposiciones activas.
 ¿Desea conocer las rutas de transporte o eventos programados?"

Usuario: "Excelente, y por cierto, ¿hay alguna promoción con aliados Movilnet para entradas de cine?"
🤖 Asistente: (El Router activa el dominio VAS/Comercios)
"¡Sí! Como abonado 4GMAX Movilnet, tiene 2x1 en entradas los días jueves en Cines Unidos presentando el código #MOV-CINE..."
```

---

## 6. Integración Soberana de Club 4GMAX (Cazador de Ofertas, Cuponería TOTP y Carrier Billing)

Como parte de la evolución Super-App Telco, Movilnet integra de manera desacoplada (**Opción A: Microservicio Hexagonal**) el ecosistema **Club 4GMAX / Cazador de Ofertas**, conectando los saldos de los 4 millones de abonados con una red de comercios y anunciantes geolocalizados.

```mermaid
flowchart LR
    subgraph ABONADO ["Abonado 4GMAX (WhatsApp / PWA)"]
        CLI["Cliente Telco"]
    end

    subgraph CORE_MOVILNET ["Movilnet Core (:8010)"]
        FP["FastPath (<15ms, 0 tokens)"]
        ROUTER["CazadorRouter (/api/v1/cazador/*)"]
        OCS["MovilnetOCSAdapter (local_movilnet.db)"]
    end

    subgraph CAZADOR_SERVICE ["Cazador de Ofertas (:8030)"]
        RADAR["SpatialRadarEngine (Haversine 3 Anillos)"]
        VAULT["CryptoTokenVaultEngine (TOTP 60s + QR)"]
        GW["IdempotentGatewayEngine (Carrier Billing Split 20/80)"]
        FTS["UniversalMemoryEngine (SQLite FTS5)"]
    end

    subgraph COMERCIO ["Punto de Venta Aliado (POS / DOOH)"]
        POS["Caja Comercial / Validación TOTP"]
    end

    CLI -->|Consulta Promos| FP
    FP --> ROUTER --> RADAR
    CLI -->|Reclamar Cupón| ROUTER --> VAULT
    VAULT -->|Genera Token 6 Dígitos| CLI
    CLI -->|Presenta Cupón en Local| POS
    POS -->|Canje y Cobro| ROUTER --> GW
    GW -->|Débito OCS| OCS
    GW -->|Liquidación 80%| POS
```

### 6.1. Invariantes Financieras de Carrier Billing (Split 20/80)
1. **Invariante II (Margen Bruto Mínimo):** Ninguna oferta aliada puede publicarse con un margen bruto menor al **$35\%$** sobre el precio regular del servicio o producto.
2. **Invariante VI (Split de Liquidación):** Del valor final del cupón canjeado:
   - **$20\%$:** Comisión retenida automáticamente por Telecomunicaciones Movilnet C.A. por concepto de Carrier Billing e intermediación digital.
   - **$80\%$:** Liquidación directa a la cuenta comercial del negocio aliado mediante Pago Móvil C2P / transferencia bancaria.
3. **Idempotencia Transaccional:** Cada canje se rige por UUID de transacción y `Idempotency-Key` para impedir cobros dobles o débitos duplicados en el saldo OCS.

### 6.2. Modelo Espacial de Cero Fricción para Comercios y Anunciantes
El sistema erradica cualquier cálculo manual geodésico para el comerciante mediante 3 escenarios automáticos:
- **Escenario 1 (Zona / Sector):** El comercio selecciona su sector (ej. *Las Mercedes*, *Chacao*, *Altamira*). El límite lo fija el polígono canónico sectorial ($1.200\text{ m} - 1.500\text{ m}$) sin ingresar metros.
- **Escenario 2 (Run of Network):** Cobertura metropolitana libre de $50.000\text{ m}$ para rotación en todas las pantallas y tablets de la ciudad.
- **Escenario 3 (Punto de Interés):** El anunciante solo indica la dirección de su local y el algoritmo inyecta un **Smart Default cinemático de $500\text{ metros}$**.
- **Guarda Anti-Spots Inaudibles:** Radios manuales $< 50\text{ m}$ (que durarían $<1.8\text{ s}$ en auto a 40 km/h) son rechazados automáticamente con error `422`.

### 6.3. Especificación Técnica de Endpoints (CazadorRouter)
- `GET /api/v1/cazador/radar`: Búsqueda de ofertas por cercanía GPS (`lat`, `lon`, `radio_m`).
- `GET /api/v1/cazador/zonas`: Catálogo canónico de sectores normalizados (NFKD).
- `POST /api/v1/cazador/comercio/registro-rapido`: Alta de comercio en $<30\text{ segundos}$ bajo los 3 escenarios espaciales.
- `POST /api/v1/cazador/cupon/reclamar`: Reserva de cupón con límite de 3 cupones activos por abonado.
- `POST /api/v1/cazador/cupon/canjear`: Canje en caja con código TOTP dinámico de 6 dígitos (válido por 60s).
- `POST /api/v1/cazador/conciliacion/carrier-billing`: Liquidación y split financiero 20/80 contra saldo OCS.

