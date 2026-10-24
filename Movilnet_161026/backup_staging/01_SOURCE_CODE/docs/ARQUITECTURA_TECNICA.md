# 🏛️ Documento de Arquitectura Técnica del Sistema
## Proyecto: `AI_Movilnet_300926`
**Plataforma Base:** ACPO & CognitiveForge B2B Studio  
**Versión:** 2.1.0 (Actualización Fase 1 Certificada)  
**Fecha de Última Actualización:** 2026-10-01  
**Fase Previa:** FASE 0 — Discovery & Inception ✅ CERTIFICADA (`FASE0-CERT-6CFBDE45D91A`)  
**Fase Actual:** FASE 1 — Capa de Datos y Persistencia ✅ CERTIFICADA (`FASE1-CERT-B1ED910BFAC6`)  
**Fase Siguiente:** FASE 2 — Servicios API REST & Flujos n8n ⏳ SIGUIENTE A EJECUTAR  
**Entorno de Ejecución:** `/Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926`  

---

## 1. Fases del Proyecto

```mermaid
flowchart LR
    F0["🔍 FASE 0\nDiscovery & Inception\n✅ CERTIFICADA\nFASE0-CERT-6CFBDE45D91A"]
    F1["🏗️ FASE 1\nCapa de Datos y Persistencia\n✅ CERTIFICADA\nFASE1-CERT-B1ED910BFAC6"]
    F2["🤖 FASE 2\nServicios API REST & n8n\n⏳ SIGUIENTE A EJECUTAR"]
    F3["🧪 FASE 3\nIntegración de Canales y QA\n⏳ PENDIENTE"]
    F4["🚀 FASE 4\nDespliegue y Producción\n⏳ PENDIENTE"]

    F0 -- "Gatekeeper 0 APROBADO" --> F1
    F1 -- "Gatekeeper 1 APROBADO" --> F2
    F2 --> F3
    F3 --> F4
```

---

## 2. Diagrama de Arquitectura Enterprise Carrier-Grade (Vía 1: Function Calling & Telemetría en Vivo)

```mermaid
flowchart TD
    subgraph CANAL ["1. Canales Omnicanal & Pasarela n8n Cloud"]
        CLIENTS["📱 WhatsApp Oficial (+58 416 625 1587)<br/>Remitente Externo (+58 414 255 4590)"]
        N8N_GW["⚡ Webhook Evolution API (:443)<br/>• Captura Multimodal (Texto / Whisper / Visión)"]
        CLIENTS --> N8N_GW
    end

    subgraph COGNITIVE_TIER ["2. Cerebro Cognitivo con Function Calling (n8n Cloud)"]
        AI_AGENT["🧠 AI Agent (LangChain v2.2 / Gemini 2.5 Flash)<br/>• Clasificador Semántico de Lenguaje Natural<br/>• Cero Peajes Rígidos de Palabras Clave"]
        TOOLS_TIER{"🌳 Árbol de Decisión Semántico<br/>(Function Calling Automático)"}
        
        N8N_GW --> AI_AGENT
        AI_AGENT --> TOOLS_TIER
    end

    subgraph TELCO_TOOLS ["3. Batería de Herramientas Telco (@n8n/toolCode v1.3)"]
        T_PORT["🎯 Portabilidad<br/>eSIM gratis + Bono 10GB"]
        T_SALDO["⚡ ConsultarSaldo<br/>Balance Bs. 1.650,00 + 11.9 GB"]
        T_PLANES["📋 CatalogoPlanes<br/>Inteliplan 10GB / Conecta 5GB"]
        T_PAGO["💳 PagoC2P<br/>Débito BDV 0102 SUDEBAN"]
        T_IMEI["🚨 BloqueoIMEI<br/>Suspensión Preventiva EIR"]
        T_LIBRE["💬 Conversación Libre<br/>Lenguaje Empático Humano"]
    end

    TOOLS_TIER -->|"Intent: Portabilidad"| T_PORT
    TOOLS_TIER -->|"Intent: Saldo / Megas"| T_SALDO
    TOOLS_TIER -->|"Intent: Tarifas / Planes"| T_PLANES
    TOOLS_TIER -->|"Intent: Recarga / Pagar"| T_PAGO
    TOOLS_TIER -->|"Intent: Robo / Bloqueo"| T_IMEI
    TOOLS_TIER -->|"Saludo / General"| T_LIBRE

    subgraph SYNTHESIS ["4. Síntesis y Despacho WhatsApp"]
        HUMAN_REPLY["✍️ Síntesis en Lenguaje Natural Humano<br/>Respuestas personalizadas sin comandos rígidos"]
        DISPATCH["🚀 WhatsApp API SendText<br/>Entrega garantizada en móvil"]
        
        T_PORT --> HUMAN_REPLY
        T_SALDO --> HUMAN_REPLY
        T_PLANES --> HUMAN_REPLY
        T_PAGO --> HUMAN_REPLY
        T_IMEI --> HUMAN_REPLY
        T_LIBRE --> HUMAN_REPLY
        HUMAN_REPLY --> DISPATCH
        DISPATCH --> CLIENTS
    end

    subgraph LIVE_MONITOR ["5. Centro de Monitoreo y Telemetría en Vivo (:8010)"]
        SYNC_ENGINE["🔄 sync_with_n8n() en conversation_trace_engine.py<br/>Polling persistente /api/v1/executions"]
        UI_DASH["🌐 http://localhost:8010/ui/monitor/conversatorio.html<br/>• Auto-Scroll al fondo<br/>• Insignias de Tool Ejecutada<br/>• Traza E2E en Vivo"]
        
        N8N_GW -.->|"Telemetría n8n"| SYNC_ENGINE
        TOOLS_TIER -.->|"Traza de Tool"| SYNC_ENGINE
        SYNC_ENGINE --> UI_DASH
    end
```

---

## 3. Arquitectura de Fase 0 (Discovery Suite — Activa)

```mermaid
flowchart LR
    subgraph DISCOVERY ["🔍 Fase 0 Discovery Suite (Certificada)"]
        SK["🌐 Skill GLOBAL<br/>telco-discovery-inception<br/>TM Forum / TOGAF ADM"]
        MCP_D["🔌 MCP Server<br/>discovery_tools.py<br/>5 herramientas JSON-RPC 2.0"]
        TESTS["🧪 Suite L1-L4<br/>test_discovery_mcp.py<br/>41/41 Tests — SAST Limpio"]
        CLI1["⚙️ CLI Script<br/>audit_perimeter_waf.py"]
        CLI2["⚙️ CLI Script<br/>generate_discovery_matrix.py"]
        CERT["🏅 Certificado<br/>FASE0-CERT-6CFBDE45D91A"]
        Q["📝 Cuestionario<br/>CUESTIONARIO_LEVANTAMIENTO<br/>_MOVILNET_VENEZUELA.md"]
    end

    MCP_D --> |audit_perimeter| WAF_RESULT["🔴 WAF Detectado<br/>movilnet.com.ve → 403<br/>Requiere IP Whitelist"]
    MCP_D --> |generate_matrix| Q
    TESTS --> CERT
    Q --> |"Enviar a TI Movilnet"| ESPERA["⏳ En espera de<br/>respuesta del cliente"]
    ESPERA --> |"Diligenciado"| GATE["mcp_discovery_gatekeeper<br/>APROBADO / BLOQUEADO"]
```

---

## 4. Inventario Completo de Componentes

### 4.1 Documentación (`docs/`)

| Archivo | Descripción | Estado |
|:---|:---|:---:|
| [`BITACORA_MOVILNET.md`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/docs/BITACORA_MOVILNET.md) | Memoria técnica continua — 8 capítulos | ✅ |
| [`CONVERSACION_INICIAL.md`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/docs/CONVERSACION_INICIAL.md) | Registro histórico del requerimiento original | ✅ |
| [`REQUERIMIENTOS_ASISTENTE_TELCO.md`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/docs/REQUERIMIENTOS_ASISTENTE_TELCO.md) | SRS con RF, RNF, ER y Dimensionamiento | ✅ |
| [`ARQUITECTURA_TECNICA.md`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/docs/ARQUITECTURA_TECNICA.md) | Diseño de 7 capas Enterprise + Fases | ✅ |
| [`FASE_0_LEVANTAMIENTO_INFORMACION.md`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/docs/FASE_0_LEVANTAMIENTO_INFORMACION.md) | Matriz de 5 Dimensiones + Suite de Tools | ✅ |
| [`CUESTIONARIO_LEVANTAMIENTO_MOVILNET_VENEZUELA_2026-09-30.md`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/docs/CUESTIONARIO_LEVANTAMIENTO_MOVILNET_VENEZUELA_2026-09-30.md) | Cuestionario para equipo TI de Movilnet | ✅ Listo |

### 4.2 Scripts (`scripts/`)

| Archivo | Descripción | Alcance |
|:---|:---|:---:|
| [`update_bitacora.py`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/scripts/update_bitacora.py) | Motor autónomo de bitácora con SHA-256 | Proyecto |
| [`audit_perimeter_waf.py`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/scripts/audit_perimeter_waf.py) | CLI diagnóstico WAF/SSL/Latencia | Proyecto |
| [`generate_discovery_matrix.py`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/scripts/generate_discovery_matrix.py) | CLI generador de cuestionario Telco | Proyecto |

### 4.3 Servidor MCP (`mcp/`)

| Archivo | Herramientas Expuestas | Alcance |
|:---|:---|:---:|
| [`discovery_tools.py`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/mcp/discovery_tools.py) | `audit_perimeter`, `inspect_db_schema`, `parse_api_spec`, `generate_matrix`, `gatekeeper` | Proyecto |
| `telco_tools.py` *(Fase 1)* | `get_subscriber`, `get_statement`, `get_plan_details` | ⏳ Pendiente |

### 4.4 Pruebas (`tests/`)

| Archivo | Cobertura | Resultado |
|:---|:---|:---:|
| [`test_discovery_mcp.py`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/tests/test_discovery_mcp.py) | L1 Unitarias + L2 Integración + L3 SAST + L4 Certificación | ✅ 41/41 |

### 4.5 Reportes (`reports/`)

| Archivo | Tipo | Estado |
|:---|:---|:---:|
| [`CERTIFICATION_FASE0_6CFBDE45D91A.json`](file:///Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/reports/CERTIFICATION_FASE0_6CFBDE45D91A.json) | Certificado SHA-256 oficial | 🏅 |
| `gatekeeper_report_*.json` | Reportes de validación Fase 0 | Generados |
| `schema_inspection_*.json` | Reportes de inspección de BD | Generados |
| `api_spec_*.json` | Reportes de parseo de APIs | Generados |

### 4.6 Skills Globales (`/Users/Users/Skills_Antigravity/skills/`)

| Skill | Versión | Estándar | Alcance |
|:---|:---:|:---|:---:|
| [`telco-discovery-inception`](file:///Users/Users/Skills_Antigravity/skills/telco-discovery-inception/SKILL.md) | v1.0.0 | TM Forum Frameworx · TOGAF ADM | 🌐 GLOBAL |

### 4.7 Directorios Pendientes (Fase 1)

| Directorio | Contenido Planificado | Condición |
|:---|:---|:---:|
| `db/` | `schema.sql` (DDL real), `movilnet.db` | Espera Fase 0 completada |
| `api/` | `openapi.json` (contrato REST), `service.py` | Espera Fase 0 completada |
| `core/` | `agent.py` (motor conversacional), `prompts/` | Espera Fase 1 iniciada |
| `docker/` | `Dockerfile`, `docker-compose.yml` | Espera Fase 1 completada |

---

## 5. Principios de Diseño y Decisiones Arquitectónicas Irrevocables

| # | Principio | Justificación |
|:---:|:---|:---|
| 1 | **Solo Lectura Absoluta** | El asistente NUNCA escribe en la BD de Movilnet. Toda consulta pasa por `sql_sanitizer.py`. |
| 2 | **Autenticación Dual Obligatoria** | Teléfono + Cédula (mínimo). Sin excepción, sin bypass. Protege 4M de abonados. |
| 3 | **Fast-Path Primero** | 70% del tráfico se resuelve sin invocar el LLM. Reduce costo y latencia. |
| 4 | **Fase 0 Obligatoria** | No se escribe código ni schema sin el cuestionario diligenciado por TI de Movilnet. |
| 5 | **Costo < \$0.0005 USD/consulta** | Protocolo `ahorro-de-tokens` + KV-Cache + Enrutador Híbrido. |
| 6 | **Bitácora Inmutable SHA-256** | Toda sesión de trabajo queda sellada. Sin memoria no hay continuidad. |
| 7 | **WAF Detectado — Requiere VPN** | `www.movilnet.com.ve` devuelve 403. La integración requiere IP Whitelist o VPN Site-to-Site. |

---

## 6. Referencias Técnicas

| Estándar / Herramienta | URL | Uso |
|:---|:---|:---|
| TM Forum TMF620 | [Open_API_And_Data_Model](https://github.com/tmforum-rand/Open_API_And_Data_Model) | Catálogo de productos/planes |
| TM Forum TMF678 | [Open_API_And_Data_Model](https://github.com/tmforum-rand/Open_API_And_Data_Model) | Facturación y saldos |
| TM Forum TMF632 | [Open_API_And_Data_Model](https://github.com/tmforum-rand/Open_API_And_Data_Model) | Gestión de clientes |
| TM Forum TMF676 | [Open_API_And_Data_Model](https://github.com/tmforum-rand/Open_API_And_Data_Model) | Pagos y recargas |
| SchemaCrawler | [schemacrawler/SchemaCrawler](https://github.com/schemacrawler/SchemaCrawler) | Ingeniería inversa de BD |
| Prism Mock Server | [stoplightio/prism](https://github.com/stoplightio/prism) | Simulación de APIs |
| Playwright | [playwright.dev](https://playwright.dev/) | Web discovery JS rendering |

---

## 7. Módulo VAS de Alta Densidad: Club 4GMAX / Cazador de Ofertas (`services/cazador_ofertas/`)

Para extender la monetización Telco sin comprometer el núcleo transaccional, Movilnet Core integra el microservicio desacoplado **Cazador de Ofertas (Club 4GMAX)** bajo Arquitectura Hexagonal:

```mermaid
flowchart TD
    subgraph PWA ["PWA 4GMAX Stitch (:8010)"]
        UI_TAB["Pestaña #tab-deals<br/>Filtro Zonas & Cerca de Mí"]
        UI_MODAL["Modal #modal-merchant-onboarding<br/>Alta Comercial en 30s"]
    end

    subgraph FASTAPI_CORE ["Movilnet Core REST Gateway (:8010)"]
        ROUTER["api/routers/cazador_router.py<br/>(/api/v1/cazador/*)"]
        OCS_ADAPTER["MovilnetOCSAdapter<br/>local_movilnet.db (Balances & Quotas)"]
    end

    subgraph CAZADOR_MS ["Microservicio Cazador de Ofertas (:8030)"]
        RADAR["SpatialRadarEngine<br/>Haversine sub-ms & Run of Network"]
        VAULT["CryptoTokenVaultEngine<br/>TOTP 60s & HMAC-SHA256"]
        GATEWAY["IdempotentGatewayEngine<br/>Split Financiero 20% / 80%"]
        MEMORY["UniversalMemoryEngine<br/>SQLite FTS5 cazador_local.db"]
    end

    UI_TAB & UI_MODAL --> ROUTER
    ROUTER --> RADAR & VAULT & GATEWAY & MEMORY
    GATEWAY --> OCS_ADAPTER
```

### 7.1. Especificación de Componentes
1. **Aislamiento Físico y de Puertos:**
   - Movilnet Core API: `localhost:8010`.
   - Microservicio Cazador de Ofertas: `localhost:8030` (orquestado vía `cazador_service.py` y `cazador_router.py`).
2. **Modelo Espacial de Cero Fricción para Anunciantes:**
   - **Escenario 1 (Zona canónica):** Centroide geodésico automático sin ingreso de metros (`zones.py`).
   - **Escenario 2 (Run of Network):** Cobertura metropolitana de $50.000\text{ m}$ sin restricciones de geocerca.
   - **Escenario 3 (Punto de Interés):** Smart Default de $500\text{ m}$ cinemático para comercio a pie/vehículo.
   - **Guarda Anti-Spots Inaudibles:** Bloqueo de radios $< 50\text{ m}$ con HTTP 422.
3. **Carrier Billing & Invariantes:**
   - Margen Bruto Mínimo $\ge 35\%$.
   - Split Financiero: $20\%$ Movilnet / $80\%$ Comercio aliado.
   - Límite de 3 cupones activos por abonado.
4. **Batería de Pruebas Automatizadas:**
   - 65 pruebas unitarias en `services/cazador_ofertas/tests/` (100% PASS).
   - 13 pruebas de integración E2E en `tests/test_cazador_movilnet_integration.py` (100% PASS).
   - Total acumulado: **78 pruebas aprobadas al 100% sin regresiones**.

