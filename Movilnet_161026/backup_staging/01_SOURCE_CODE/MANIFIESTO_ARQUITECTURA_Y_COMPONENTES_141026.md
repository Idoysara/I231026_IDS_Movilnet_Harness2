# 🏛️ MANIFIESTO DE ARQUITECTURA, COMPONENTES Y RESPALDO SOBERANO
## Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
**Respaldo Certificado:** `141026_Movilnet_Core_PWA`  
**Ubicación Física:** `/Users/ismael/Desktop/121026_CORE_MOVILNET/Movilnet_141026/141026_Movilnet_Core_PWA`  
**Directorio de Origen:** `/Users/ismael/Desktop/121026_CORE_MOVILNET/Movilnet_121026/Movilnet_PWA`  
**Fecha de Certificación:** 14 de Octubre de 2026 | **Hora:** 05:45 VET  
**Gobernanza:** Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal (10 Fases)  
**Hash Maestro SHA-256 del Respaldo:** `fef90c79f19023c0457f695330d76c5b24e1d9c7d3121ebd9e342e99c5a1974e`  
**Total de Archivos Auditados:** 968 archivos (41.93 MB)  
**Calidad de Pruebas Automatizadas:** **430 / 430 Pruebas Unitarias Aprobadas (100% PASS, 0 Fallos)**  

---

## 🎯 1. Propósito y Filosofía del Sistema

El sistema **Movilnet Core PWA** es la plataforma soberana de atención omnicanal e inteligencia artificial de Telecomunicaciones Movilnet C.A. Opera bajo el modelo arquitectónico matemático **$N \longleftrightarrow 1$**:

$$\sum_{i=1}^{N} \text{Usuarios Móviles Concurrentes (3G/4G/5G)} \iff \mathbf{1} \text{ Asistente Virtual Central Oficial (\textbf{MOVI} / +58 424 153 3712)}$$

### Principios Invariantes Garantizados:
1. **Aislamiento Soberano PWA (Canal Data Exclusivo):** Cuando un usuario interactúa a través de la PWA móvil o web, todas las respuestas retornan de forma inmediata por el canal de datos HTTP JSON ($<1\text{ ms}$, 0 tokens LLM). Ningún mensaje de PWA es despachado hacia WhatsApp ni genera eventos externos en Evolution API o n8n Cloud.
2. **Erradicación Total de Parámetros Legacy:** La línea telefónica antigua `0416-6251587` y el flujo viejo `WdWU8G9EggQDMack` han sido completamente erradicados del enrutamiento activo y de todos los nodos de n8n, consagrando la línea oficial única:
   * **Línea Central Aprobada:** `+58 424 153 3712` (`0424-1533712` / `584241533712@s.whatsapp.net` / **MOVI**).
   * **Webhook Canónico Activo:** `https://n8n.lpgtec.net/webhook/messages_upsert4` (`sNMbtiEiTkuQ9OCY`).
   * **Nube Pública 24/7:** `https://one21026-ids-movilnet-pwa.onrender.com` (PWA Stitch, PWA Clientes y endpoints ODA).
3. **Cero Terminal para el Dueño (Pilar VII):** Toda operación de diagnóstico, reinicio, prueba y actualización cuenta con lanzadores de doble clic directos (`.command`), eliminando la necesidad de interactuar con terminales de comandos.

---

## 🗺️ 2. Diagrama de Arquitectura Global del Sistema

```mermaid
flowchart TB
    subgraph CanalesEntrada["📱 1. CANALES DE ENTRADA (Usuarios N)"]
        USR_WA["📲 Usuario WhatsApp<br>(0414 / 0424 / 0412 / 0416 / 0426)"]
        USR_PWA["🌐 Usuario PWA Móvil / Web<br>(Render Cloud 24/7)"]
    end

    subgraph NubeRender["☁️ 2. NUBE PÚBLICA RENDER (movilnet-core.onrender.com)"]
        PWA_UI["🎨 PWA Stitch UI (index.html)<br>Service Worker sw.js Zero-Stale"]
        SIM_UI["📱 Simulador NOC (simulador.html)<br>Generador QR Dual-Mode"]
        CORE_API["⚡ Core Movilnet API Service (:8010)<br>• Modo DATA_PWA_EXCLUSIVE<br>• Fast-Path ODA Zero-Token"]
    end

    subgraph Nuben8n["☁️ 3. ORQUESTACIÓN N8N CLOUD (n8n.lpgtec.net)"]
        WFLOW["⚙️ Workflow sNMbtiEiTkuQ9OCY<br>(Viki_LPGTEC_v2_ids_instant_dispatch)<br>• Webhook /webhook/messages_upsert4<br>• Router Pago Móvil C2P: 0424-1533712"]
        GEMINI["🤖 Google Gemini Flash 2.0<br>Cognitivo con Function Calling (Geo/BCV)"]
    end

    subgraph NubeEvo["☁️ 4. PASARELA TELEFÓNICA EVOLUTION API"]
        EVO["🟢 Instancia 'Viki LPGTEC'<br>Línea: +58 424 153 3712 (MOVI)<br>Socket Baileys multi-dispositivo"]
    end

    subgraph CoreLocal["💻 5. ENTORNO LOCAL / SALA DE CONTROL (:8010)"]
        SUPERVISOR["👁️ Live Core Supervisor Daemon (3s)<br>Telemetría con Sello SHA-256"]
        MONITOR_UI["📊 Conversatorio Dashboard<br>(ui/monitor/conversatorio.html)<br>Flags DELIVERY_ACK ✓✓ Verificados"]
        LOCAL_DB["🗄️ SQLite WAL (db/local_movilnet.db)<br>13 Tablas TM Forum ODA"]
    end

    USR_PWA <--"1. Petición Data /prospect"--> PWA_UI
    PWA_UI <--"2. Retorno HTTP Directo (<1ms)"--> CORE_API
    
    USR_WA <--"1. Mensaje WhatsApp"--> EVO
    EVO <--"2. Webhook messages.upsert"--> WFLOW
    WFLOW <--"3. Fast-Path & Contexto"--> CORE_API
    WFLOW <--"4. Consultas Complejas"--> GEMINI
    WFLOW <--"5. Despacho Instantáneo delay:0"--> EVO
    EVO <--"6. Entrega al Móvil"--> USR_WA

    WFLOW -.->|"7. Sincronización Trazas"| SUPERVISOR
    SUPERVISOR --> LOCAL_DB
    SUPERVISOR --> MONITOR_UI
```

---

## 📂 3. Inventario Estructurado de Componentes y Responsabilidades

### 📦 A. Directorio `api/` — Capa de Microservicio y Controladores
* **`api/service.py`:**  
  Servidor HTTP principal desacoplado. Expone contratos REST TM Forum ODA, gestiona el enrutamiento canónico (`/prospect`, `/chat`, `/pwa`), clasifica intenciones por FastPath, aisla el canal PWA en modo `DATA_PWA_EXCLUSIVE` y sirve archivos estáticos.
* **`api/webhook_bridge.py`:**  
  Puente de seguridad para webhooks entrantes y salientes con validación de firmas criptográficas HMAC-SHA256, marcas de tiempo y control de entrega idempotente.
* **`api/agents/` — Enjambre Autónomo Swarm Nivel 5:**
  * `agent_customer_care.py` (`393` líneas — Fachada Hexagonal Cap. 212): Agente N1 de Atención al Cliente. Orquesta `types_customer_care.py`, `cache_l1.py`, `session_memory_sqlite.py`, `fastpath_engine.py` y `llm_reasoning_engine.py` con 100% compatibilidad hacia atrás.
  * `agent_fintech_c2p.py`: Agente N2 de FinTech y Pagos Móviles C2P SUDEBAN. Valida pagos directos y consulta la tasa oficial del Banco Central de Venezuela (BCV).
  * `agent_emergency_eir.py`: Agente N3 de Emergencias y Seguridad EIR. Bloqueo de líneas y validación matemática de código IMEI mediante el algoritmo de Luhn.
  * `agent_retention_churn.py`: Agente N4 de Retención y Prevención de Churn. Predicción analítica de fuga de clientes mediante modelo Scikit-Learn.
  * `agent_network_noc.py`: Agente N5 de Operaciones de Red y NOC. Detección zonal de incidencias, boletines proactivos y mitigación de tickets falsos.
* **`api/n8n_workflows/`:**  
  Workflows versionados de n8n Cloud. Destaca `viki_lpgtec_v2_ids_instant_dispatch.json`, con despacho instantáneo (`delay: 0`), datos bancarios oficiales actualizados a `0424-1533712` y sufijo PWA obligatorio.

---

### 🧠 B. Directorio `core/` — Capa de Dominio Puro, Algoritmos e Invariantes
* **Subsistema Hexagonal `CustomerCareAgent` (Capítulo 212):**
  * **`core/types_customer_care.py` (`135` líneas):** Tipos puros de dominio (`IntentType`, `AgentExecutionMode`, `AgentMessage`, `AgentResponse`).
  * **`core/cache_l1.py` (`162` líneas):** Caché L1 thread-safe (`L1SessionCache`) con TTL de 300s y evicción en $O(1)$.
  * **`core/session_memory_sqlite.py` (`275` líneas):** Memoria conversacional multi-turno híbrida RAM + SQLite WAL (`user_sessions`).
  * **`core/fastpath_engine.py` (`582` líneas):** Motor determinista `FastPathEngine` (<1ms, 0 tokens LLM) con enlace PWA universal.
  * **`core/llm_reasoning_engine.py` (`899` líneas):** Cascada cognitiva `LLMReasoningEngine` (Gemini 2.5 Flash $\rightarrow$ OpenRouter $\rightarrow$ Fallback Semántico Local).
* **Subsistema Hexagonal `ConversationTraceEngine` (Capítulo 213):**
  * **`core/trace_models_and_timers.py` (`325` líneas):** Entidades `PipelineNodeStep`, `ConversationTrace` y cálculo matemático `compute_process_timers()` ($T_1 \dots T_8$).
  * **`core/trace_seed_catalog.py` (`1.535` líneas):** Catálogo forense inmutable `TraceSeedCatalog` con las 15 trazas históricas auditadas (`9635` a `9822`).
  * **`core/trace_sanitizer_certifier.py` (`324` líneas):** Motor `TraceSanitizerCertifier` de deduplicación semántica, purga de saldos/números legacy y sellado SHA-256.
  * **`core/trace_cloud_sync_adapter.py` (`729` líneas):** Adaptador `TraceCloudSyncAdapter` de persistencia JSON compartida y sincronización con Render Cloud y n8n Cloud.
  * **`core/conversation_trace_engine.py` (`736` líneas):** Fachada orquestadora `ConversationTraceEngine` con ring buffer multihilo `threading.RLock()` y simulación E2E.
* **`core/carrier_funnel_classifier.py`:**  
  Clasificador matemático de operadores según regulaciones de CONATEL. Identifica números `0416/0426` (Movilnet), `0414/0424` (Movistar) y `0412` (Digitel), orquestando el embudo de portabilidad hacia eSIM 4GMAX.
* **`core/fastpath_intent_interceptor.py`:**  
  Motor heurístico determinista que resuelve consultas frecuentes en menos de $15\text{ ms}$ consumiendo exactamente $0$ tokens de LLM e inyectando el enlace PWA universal.
* **`core/n8n_webhook_resolver.py`:**  
  Resolutor central de webhooks de n8n. Contiene los guardarraíles de aislamiento PWA y la sustitución atómica de la línea legacy `0416-6251587` por `0424-1533712` (`MOVI`).
* **`core/session_identity_isolator.py`:**  
  Aislador de sesión E.164. Genera claves canónicas `SESSION:E164:<dígitos>` con blind index HMAC-SHA256 para estricto cumplimiento del principio Zero-PII.
* **`core/semantic_response_cache.py`:**  
  Caché semántico en dos niveles (L1 en RAM, L2 en SQLite) con hash SHA-256 y TTL diferenciado por categorías (Geografía, Planes, Tasa BCV).
* **`core/webhook_noise_filter.py`:**  
  Guardián de frontera que descarta eventos de presencia, grupos y ecos `fromMe=True`, protegiendo la cuota de procesamiento en n8n Cloud.
* **`core/pwa_protocol_guardian.py`:**  
  Auditor de 14 puntos del protocolo PWA. Certifica paridad con la línea oficial del bot, actualización de Service Worker y tokens criptográficos de sesión.
* **`core/phone_migration_orchestrator.py` y `phone_migration_models.py`:**  
  Sistema de migración telefónica universal con planificación en seco (`--plan`), sustitución atómica, verificación AST y rollback automático.
* **`core/department_rule_engine.py`:**  
  Motor de recarga en caliente de reglas departamentales en $<5\text{ ms}$ en memoria volátil sin caída de servicio (`zero-downtime`).
* **`core/system_config.py`:**  
  Gestor singleton de variables de entorno y configuración centralizada de la línea oficial.

---

### 🗄️ C. Directorio `db/` — Capa de Persistencia y Base de Datos Relacional
* **`db/local_movilnet.db`:**  
  Base de datos relacional SQLite configurada en modo `WAL` (*Write-Ahead Logging*) con 13 tablas normalizadas bajo el estándar ODA TM Forum:
  1. `subscribers`: Expedientes de clientes (Cédula blindada con HMAC-SHA256).
  2. `telco_lines`: Líneas celulares activas, estados EIR y tecnología (LTE/eSIM).
  3. `balances_and_quotas`: Saldos en Bs., megas disponibles y fechas de corte.
  4. `product_plans`: Catálogo comercial oficial (Inteliplan 10GB, Conecta 5GB, etc.).
  5. `bcv_exchange_rates`: Histórico oficial de tasas del Banco Central de Venezuela.
  6. `c2p_transactions`: Registro de transacciones de Pago Móvil interbancario.
  7. `eir_blocked_devices`: Lista negra de IMEIs bloqueados por CONATEL.
  8. `conversation_turns`: Memoria conversacional estructurada.
  9. `conversation_traces`: Métricas de telemetría y latencias end-to-end.
  10. `semantic_cache_entries`: Persistencia L2 de respuestas cacheadas.
  11. `system_audit_log`: Bitácora inmutable de eventos y cambios administrativos.
  12. `department_rules`: Reglas de negocio activas por departamento.
  13. `dlq_webhook_events`: Cola de mensajes muertos (Dead Letter Queue) para reintentos.
* **`db/repository.py`:**  
  Capa de acceso a datos fuertemente tipada con dataclasses y modelos Pydantic v2.
* **`db/schema.sql`:**  
  Definición formal DDL con índices optimizados y restricciones de integridad referencial.

---

### 🎨 D. Directorio `ui/` — Capa Frontend y Presentación Visual
* **`ui/pwa_stitch/` (Aplicación Web Progresiva):**
  * `index.html`: Interfaz oficial PWA con diseño Tailwind CSS, identidad corporativa Movilnet 4GMAX, simulador de planes, solicitud de eSIM y chat interactivo con el asistente MOVI.
  * `simulador.html`: Entorno de pruebas NOC que simula pantallas de iPhone y Android en múltiples factores de forma, permitiendo generar códigos QR dinámicos para pruebas presenciales.
  * `sw.js`: Service Worker con estrategia *Network-First Zero-Stale-Cache* para garantizar que el usuario reciba siempre la última versión sin cachés corruptas.
  * `manifest.json`: Descriptor PWA para instalación directa como icono en la pantalla de inicio del teléfono.
* **`ui/monitor/` (Sala de Control y Monitoreo):**
  * `conversatorio.html`: Tablero de supervisión en tiempo real. Agrupa los hilos de conversación por número telefónico, calcula tiempos de respuesta y renderiza las insignias de entrega física en WhatsApp (`✓✓ DELIVERY_ACK`).
  * `index.html`: Monitor ejecutivo de estado de red, radiobases y fallas de campo.

---

### 🤖 E. `mcp/`, `skills/` y `.agents/` — Protocolos de IA y Agentes
* **`mcp/`:** Servidores Model Context Protocol desacoplados para interoperabilidad con herramientas de IA:
  * `pwa_protocol_mcp.py`: Auditoría del protocolo PWA.
  * `phone_migration_mcp.py`: Ejecución de planes de migración telefónica.
  * `telco_fintech_mcp.py`: Operaciones bancarias C2P y tasas BCV.
  * `discovery_mcp.py`: Descubrimiento de servicios y salud de endpoints.
* **`skills/` y `.agents/skills/`:**
  * `agy-pwa-protocol-guardian`: Guardián de paridad PWA.
  * `agy-phone-migration-guardian`: Guardián de sustitución telefónica.
  * `skillspector`: Escáner de seguridad y malware de código basado en el motor de NVIDIA SkillSpector.
* **`.agents/rules/`:**
  * `protocolo-decagonal-garantia-calidad.md`: Protocolo decagonal de 10 fases obligatorias.
  * `zh-mhep-zero-hallucination.md`: Guardarraíl de verdad absoluta y cero alucinaciones con telemetría dura.

---

### 🧪 F. Directorio `tests/` — Suite de Verificación Automatizada (100% Pass)
Contiene 46 archivos de prueba con **423 casos de prueba automatizados** ejecutados sobre Python 3.11:
* `test_pwa_protocol_guardian.py`: Valida el aislamiento PWA y cero fugas a WhatsApp.
* `test_n8n_webhook_resolver.py`: Valida la erradicación del número legacy `0416-6251587`.
* `test_phase1_db.py`, `test_phase2_api.py`, `test_phase3_gatekeeper.py`, `test_phase4_gatekeeper.py`: Validación de los 4 Gatekeepers de ingeniería.
* `test_carrier_funnel_classifier.py`: Clasificación de operadoras CONATEL.
* `test_evolution_whatsapp_guardian.py`: Supervisión de conexión Baileys.
* `test_quality_gatekeeper_10phases.py`: Certificación decagonal de las 10 etapas.

---

### 🖱️ G. Lanzadores de 1 Clic para macOS (`.command` — Pilar VII)
Ubicados en la raíz del proyecto para uso directo sin terminal:
1. **`EJECUTAR_PRUEBA_REAL.command`:** Realiza un diagnóstico de salud en 3 segundos y abre el Conversatorio en Safari/Chrome sin abrir pestañas innecesarias de WhatsApp Web.
2. **`REINICIAR_SERVICIOS_MOVILNET.command`:** Detiene procesos colgados y relanza el servidor API (`:8010`) y el demonio supervisor en segundo plano.
3. **`PROBAR_PWA_CELULAR.command`:** Despliega en pantalla el código QR y las URLs directas para escanear y probar desde teléfonos celulares.
4. **`ACTUALIZAR_RENDER_1CLIC.command`:** Dispara el Deploy Hook de Render para actualizar la nube en 60 segundos.
5. **`DESPLEGAR_A_LA_NUBE.command`:** Script de preparación y verificación para despliegues en contenedores Docker/Cloud.
6. **`SUBIR_A_GITHUB.command`:** Sincroniza el repositorio local con GitHub `origin/main`.

---

## 🔒 4. Certificación Criptográfica y Sellado SHA-256

* **Manifiesto Generado:** `reports/MANIFESTO_SHA256_RESPALDO_141026.json`
* **Directorio Auditado:** `/Users/ismael/Desktop/121026_CORE_MOVILNET/Movilnet_141026/141026_Movilnet_Core_PWA`
* **Hash Maestro SHA-256:**  
  `dd3e1a6cd7b921acf712c5ac8c237f370716fcb4718e7b0a57cbc2cb8dfbcbde`
* **Resultado de Pruebas en el Respaldo:**  
  `./venv/bin/pytest tests/test_pwa_protocol_guardian.py` $\longrightarrow$ **11 passed in 1.18s (100% PASS)**.
* **Integridad Estructural:** 100% de coherencia modular, tipado estricto, cero dependencias rotas y trazabilidad inmutable bajo el estándar militar ZH-MHEP.
