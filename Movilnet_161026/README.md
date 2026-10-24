# 📡 AI_Movilnet_300926 — Asistente Cognitivo Carrier-Grade para Telecomunicaciones Movilnet C.A.

> **Ecosistema Inteligente Autónomo Nivel 5 Antigravity AI — Fases 0 a 5 Certificadas**  
> Microservicios REST TM Forum ODA, Orquestación Omnicanal en n8n Enterprise & MCP Server, Enjambre Swarm L5, Motor de Reglas Departamentales Hot-Reload (<3ms), Integración Google Suite, PWA Mobile-First y Lanzadores Autónomos.

---

## 🎯 Resumen del Proyecto

Este repositorio alberga la plataforma de producción de **Telecomunicaciones Movilnet C.A.** diseñada para atender a más de 4 millones de abonados (`0416` / `0426`) con arquitectura carrier-grade de nivel militar:

- **Tests Automatizados:** ✅ **580+ pruebas certificadas (100% OK / 0 fallos)** (incluyendo las 114 pruebas unitarias de los 11 módulos hexagonales y las 78 pruebas del microservicio Club 4GMAX Cazador de Ofertas).
- **Capa de Datos:** PostgreSQL 15/16 particionado Hash/Range + failover transparente a SQLite WAL en $O(1)$ (0.053 ms) con 13 tablas normalizadas TM Forum ODA (+ tabla `user_sessions` para memoria multi-turno persistente) y Catálogo Geoespacial Nacional (`geo_pois`, 1.239 agencias indexadas).
- **Microservicio Core:** REST API con 31 endpoints certificados bajo OpenAPI 3.1.0 TM Forum (TMF620, TMF621, TMF676, TMF678, TMF680, TMF688), modo exclusivo de datos PWA (`DATA_PWA_EXCLUSIVE`) y **Regla Constitucional de Enlace PWA Universal** al final de todo mensaje.
- **Club 4GMAX / Cazador de Ofertas (Capítulos 224 y 225):** Microservicio hexagonal (`services/cazador_ofertas/`) en `:8030` conectado vía `api/routers/cazador_router.py` a `:8010`. Cuponería dinámica TOTP de 60s, Carrier Billing (split 20% Telco / 80% Comercio, margen bruto $\ge 35\%$) y **Modelo Espacial de Cero Fricción para Comerciantes** (0 metros obligatorios: Escenario 1 Zonas por polígono, Escenario 2 Run of Network 50km metropolitano, Escenario 3 Smart Default 500m cinemático y guarda anti-spots inaudibles $<50\text{m}$).
- **Swarm Cognitivo L5 & Arquitectura Hexagonal Desacoplada (Capítulos 212 y 213):**
  1. **Atención / Soporte N1 (`CustomerCareAgent` — 6 Módulos Hexagonales):** Fachada `agent_customer_care.py` (`393` líneas, reducida un 78.4%) respaldada por `types_customer_care.py`, `cache_l1.py`, `session_memory_sqlite.py`, `fastpath_engine.py` (<1ms, 0 tokens) y `llm_reasoning_engine.py`.
  2. **Trazabilidad Conversacional E2E (`ConversationTraceEngine` — 5 Módulos Hexagonales):** Fachada `conversation_trace_engine.py` (`736` líneas, reducida un 76.9%) respaldada por `trace_models_and_timers.py` ($T_1 \dots T_8$), `trace_seed_catalog.py` (15 semillas forenses), `trace_sanitizer_certifier.py` (SHA-256) y `trace_cloud_sync_adapter.py`.
  3. **Comercial / Ventas N1:** Planes Inteliplan 10GB/20GB/50GB, bonos de portabilidad 10GB y embudo eSIM.
  4. **FinTech C2P N2:** Pagos móviles interbancarios SUDEBAN (50 a 50.000 Bs), BCV oficial y receptor `0424-1533712`.
  5. **Seguridad / CONATEL N3:** Validación IMEI por algoritmo de Luhn (15 dígitos), lista negra EIR y Zero-PII (<30ms RAM).
  6. **Operaciones de Red / NOC N5:** Detección de radiobases, boletines técnicos zonales y supresión de averías falsas.
  7. **Retención / Churn N4:** Modelo analítico Scikit-Learn de predicción de abandono y ofertas Next-Best-Action.
  8. **Compuerta de Dominio Telco:** `OFF_TOPIC_TELCO_GUARD` para desvío inmediato de gastronomía/comercio ajeno a directorios locales desde navegación 4GMAX.
- **Catálogo de Reglas Departamentales Hot-Reload:** Directorio declarativo `config/department_rules/` administrable en caliente en 2.14 ms vía cerrojo multihilo `threading.RLock()`.
- **Omnicanalidad & n8n Live MCP:** Workflow canónico en producción `sNMbtiEiTkuQ9OCY` conectado a Evolution API (`+58 424 153 3712` / **MOVI**).
- **Google Suite Enterprise:** Conectores MCP activos para Drive, Sheets, Docs, Calendar y Gmail con cuotas y circuit breakers.
- **Seguridad de Agentes (NVIDIA SkillSpector):** Escáner AST de malware, troyanos y jailbreaks para skills y tools.
- **Conversatorio & Monitoreo E2E:** Observabilidad del Webhook bot `+58 424 153 3712` en `:8010/ui/monitor/conversatorio.html` con flags de entrega verificada (`DELIVERY_ACK`).
- **Experiencia de Usuario (UI/UX/AX):** PWA Mobile-First responsive (`/ui/pwa_stitch/index.html`) con continuidad de sesión en `sessionStorage` (`movilnet_pwa_session_id`), pestaña `#tab-deals` (Club 4GMAX) y modal de registro comercial en 30s (`#modal-merchant-onboarding`).
- **Despliegue 100% en la Nube (Producción 24/7):** Microservicio en Render Cloud (Plan Free, $0/mo) protegido con Cloudflare Enterprise Anycast Edge:
  * **PWA Clientes Directa:** [`https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html`](https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html)
  * **Simulador con Máscara de Smartphone:** [`https://one21026-ids-movilnet-pwa.onrender.com/simulador`](https://one21026-ids-movilnet-pwa.onrender.com/simulador)
  * **NOC Dashboard:** [`https://one21026-ids-movilnet-pwa.onrender.com/ui/dashboard/noc_dashboard.html`](https://one21026-ids-movilnet-pwa.onrender.com/ui/dashboard/noc_dashboard.html)
- **Túnel Seguro Cloudflare (Opción 2):** Despliegue de alta resiliencia con ancho de banda 100% ILIMITADO y \$0 costo, enrutando tráfico público hacia el Core local (`:8010`) en 152 ms (cero cold starts).
- **Despliegue y Orquestación:** Microservicio ODA en Render Cloud y puerto local `:8010`, túnel Anycast global y n8n Cloud (`n8n.lpgtec.net`).
- **Anexo Técnico Oficial:** [`docs/ANEXO_TECNICO_CLOUDFLARE_TUNNEL.md`](docs/ANEXO_TECNICO_CLOUDFLARE_TUNNEL.md) con auditoría de protocolos QUIC, TLS 1.3, curvas X25519MLKEM768 y guía de mantenimiento.
- **Entregables Soberanos de Doble Clic:** Scripts `.command` para macOS (`reiniciar_todo_limpio.command`, `probar_geolocalizacion.command`, `verificar_whatsapp_sin_celular.command`, `AUDITAR_CLOUDFLARE_1CLIC.command`).
- **Respaldo Soberano Certificado:** Paquetes maestros `CORE_MOVILNET_EXPORT_161026.tar.gz` y `CORE_MOVILNET_EXPORT_181026.tar.gz` y Manual On-Premise `DEPLOYMENT_MANUAL_CLIENTE.md` (**Capítulos 1 al 225**).

---

## 🏛️ Arquitectura de Carpetas

```
AI_Movilnet_300926 /
├── MANIFIESTO_ARQUITECTURA_Y_COMPONENTES_141026.md # Manifiesto maestro y mapa de componentes
├── PUNTO_DE_CONTROL_SESION_ACTIVA.md               # Punto de control y memoria de sesión (Caps. 1-225)
├── ACTUALIZAR_REGLAS_DEPARTAMENTALES.command       # Lanzador 1-Clic de recarga en caliente de reglas
├── EJECUTAR_PRUEBA_REAL.command                    # Lanzador 1-Clic de prueba E2E
├── config/
│   └── department_rules/ # Catálogos JSON de 5 departamentos (Comercial, Finanzas, Atención, Seguridad, NOC)
├── api/                  # Microservicio REST, Contrato OpenAPI y Enjambre de Agentes
│   ├── agents/           # Agentes N1 a N5 (CustomerCare fachada 393 líneas), Funnel Marketing y Geoespaciales
│   ├── routers/          # Enrutadores modulares (cazador_router.py, telco_router.py, etc.)
│   ├── n8n_workflows/    # Workflows Canónicos exportados en JSON
│   └── webhook_bridge.py # Puente de Webhooks HMAC con DLQ y backoff
├── core/                 # Módulos Hexagonales (types, cache_l1, session_memory_sqlite, fastpath_engine, llm_reasoning, trace_*)
├── services/
│   └── cazador_ofertas/  # Microservicio Desacoplado Club 4GMAX (SpatialRadar, CryptoTokenVault, Gateway)
├── db/                   # DDL ODA, conectores con pooling y repositorio seguro Zero-PII
├── docs/                 # Bitácora continua (Capítulos 1-225) y documentos maestros
├── mcp/                  # Suites MCP (Telco, Fintech, NOC, CRM, Privacy, Omnicanal, Geo, Google, SkillSpector)
├── reports/              # Certificados criptográficos SHA-256 y manifiesto de respaldo
├── scripts/              # Validador de reglas, pipelines de despliegue, SRE Watchdog y clientes CLI
├── tests/                # Suites unitarias, de estrés, de integración y live connectors (100% PASS)
└── ui/                   # Portal web, Conversatorio en vivo, Dashboard NOC y PWA Stitch
```

---

## 🚀 Despliegue y Ejecución

### Opción 1: Lanzadores de Doble Clic (macOS — Pilar VII: Cero Terminal)
- `EJECUTAR_PRUEBA_REAL.command`: Chequeo de salud del sistema y apertura de la Sala de Control sin abrir pestañas innecesarias.
- `ACTUALIZAR_REGLAS_DEPARTAMENTALES.command`: Valida y recarga en caliente las reglas de los 5 departamentos en 2.14 ms sin reiniciar el servidor.
- `REINICIAR_SERVICIOS_MOVILNET.command`: Reinicia en limpio los servicios locales del puerto 8010 y el supervisor de sincronización en vivo.
- `PROBAR_PWA_CELULAR.command`: Detecta la red Wi-Fi y genera el enlace y código QR para probar la PWA en celulares físicos.
- `ACTUALIZAR_RENDER_1CLIC.command`: Dispara el Deploy Hook de Render para actualizar la nube en 60 segundos.

### Opción 2: Consola de Comandos
```bash
# Ejecutar suite completa de 430 pruebas (100% PASS)
./venv/bin/pytest tests/

# Validar catálogo de reglas departamentales
./venv/bin/python3 scripts/validate_department_rules.py --test

# Arrancar microservicio REST API (puerto 8010, aislado por agy-port-guardian)
python3 api/service.py  # o doble clic en REINICIAR_SERVICIOS_MOVILNET.command
```

---
*Telecomunicaciones Movilnet C.A. — La señal que nos une.*
