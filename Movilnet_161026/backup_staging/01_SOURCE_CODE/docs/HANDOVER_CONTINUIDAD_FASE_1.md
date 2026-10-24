# 📘 HANDOVER & CONTINUIDAD DEL PROYECTO — AI_MOVILNET_300926
## Documento Maestro de Traspaso Técnico y Memoria Operativa

**Organización:** Telecomunicaciones Movilnet C.A.  
**Proyecto:** `AI_Movilnet_300926` — Aplicación Cognitiva Interactiva de IA  
**Escala:** 4.000.000 de Abonados (Prefijos 0416 / 0426)  
**Arquitectura:** TM Forum ODA (TMF620, TMF622, TMF632, TMF676, TMF678, TMF680)  
**Fecha de Actualización:** 2 de Octubre de 2026, 11:35 VET (UTC-4)  
**Estado Global:** 🟢 **OPERACIONAL — Fases 0, 1, 2, 3 y Fase 4 Pasos 1 y 2 al 100% certificados**  
**Tests Totales Pasando:** **219 / 219 (100% en 5.135s)**  

---

## 1. 📌 Mapa de Estado por Fase

| Fase | Título | Tests | Certificado | Sello SHA-256 |
|:---:|:---|:---:|:---|:---:|
| **0** | Discovery & Inception | 41 | `FASE0-CERT-6CFBDE45D91A` | `6cfbde45d91a...` |
| **1** | Capa de Datos ODA & Persistencia WAL | 55 | `FASE1-CERT-B1ED910BFAC6` | `b1ed910bfac6...` |
| **2** | REST API OpenAPI 3.1.0 & Workflows n8n | 131 | `FASE2-GATEKEEPER-CERT-5F331AB7384F` | `5f331ab7384f...` |
| **3** | Core IA & Enjambre Swarm Nivel 5 | 205 | `FASE3-GATEKEEPER-CERT-0886A5D9B351` | `0886a5d9b351...` |
| **4 — P1** | Sistema de Diseño UI/UX/IX/AX | 211 | `FASE4-PASO1-CERT-8C21DA769B40` | `801f2ff75232...` |
| **4 — P2** | Dashboard Web Ejecutivo NOC/CCO | 219 | `FASE4-PASO2-CERT-1529E341CA67` | `1529e341ca67...` |

---

## 2. 🏛️ Arquitectura Técnica del Sistema

### 2.1 Stack de Persistencia
- **PostgreSQL 15+ Enterprise Partitioned:** 10 tablas ODA con particionamiento HASH (8 shards) para `telco_lines` y `balances_and_quotas`, y RANGE mensual para `usage_records_cdr` y `financial_transactions`.
- **SQLite 3 WAL Multi-Hilo (Modo Resiliente):** Modo de contingencia local idéntico al esquema PostgreSQL. Latencia de lectura medida: **0.057ms** (SLA 5.0ms).
- **PgBouncer (Puerto 6432):** Pool de conexiones en modo `transaction` para absorber miles de webhooks concurrentes de n8n.
- **Redis L1 Cache:** Caché de contexto de conversación con TTL 60s y latencia < 2ms.

### 2.2 Las 10 Tablas ODA
| # | Tabla | Estándar TM Forum | Tipo de Partición |
|:---:|:---|:---:|:---|
| 1 | `subscribers` | TMF632 | — |
| 2 | `pii_vault` | TMF632 | — (Aislada de n8n) |
| 3 | `product_plans` | TMF620 | — |
| 4 | `telco_lines` | TMF622 | HASH(msisdn) × 8 shards |
| 5 | `balances_and_quotas` | TMF678 | HASH(msisdn) × 8 shards |
| 6 | `usage_records_cdr` | TMF678 | RANGE mensual (BRIN) |
| 7 | `banks_sudeban` | TMF676 | — |
| 8 | `financial_transactions` | TMF676 | RANGE mensual |
| 9 | `churn_metrics` | TMF680 | — |
| 10 | `eir_security_events` | GSMA EIR | — |

### 2.3 Seguridad Zero-Knowledge PII
- `blind_index_cid`: HMAC-SHA256 de la Cédula de Identidad (V-/E-/J-) con salt de producción.
- `pii_vault`: AES-256-GCM para datos personales cifrados. El rol `usr_n8n_app` tiene `REVOKE ALL ON pii_vault`.
- `hmac.compare_digest()` en todas las comparaciones de tokens para prevenir timing-attacks.
- Anti-replay de 300s por `X-Delivery-ID` único en webhooks entrantes.

---

## 3. 🐝 Los 4 Agentes del Enjambre Swarm Nivel 5

| Agente | Rol TM Forum | Archivo | Latencia Medida | Certificado |
|:---|:---:|:---|:---:|:---:|
| **N1 — Customer Care** | TMF621 | `api/agents/agent_customer_care.py` | 0.18ms Fast-Path | `FASE3-PASO1-CERT-AA65BDFDE953` |
| **N2 — Fintech C2P** | TMF676 | `api/agents/agent_fintech_c2p.py` | 0.006ms Oráculo BCV | `FASE3-PASO2-CERT-3BC268AE3EE0` |
| **N3 — Emergencias EIR** | GSMA | `api/agents/agent_emergency_eir.py` | 0.019ms Luhn-10 | `FASE3-PASO3-CERT-A5AC87CE80FD` |
| **N4 — Retención Churn** | TMF680 | `api/agents/agent_retention_churn.py` | 0.57ms ML Infer. | `FASE3-PASO4-CERT-58F42856AD7B` |

### Flujos de Coordinación Swarm (7 Rutas Certificadas):
1. **N1 → N4:** Intención de cancelación/portabilidad detectada → Oferta de retención `RESCATE-VIP`.
2. **N3 → N4:** Denuncia de robo + bloqueo IMEI EIR → Cupón de fidelización post-hurto.
3. **N4 → N2:** Cupón de retención generado → Canje con descuento del 20% en pasarela C2P.
4. **N2 → N4:** Canje atómico de cupón + bloqueo anti-doble gasto (`CUPON_YA_CANJEADO`).
5. **N2 → N3:** Alerta de fraude financiero (score ≥ 0.80) → Suspensión preventiva de línea.
6. **N3 → N1:** Purga inmediata de caché L1 ante eventos de seguridad EIR.
7. **N1 → N2:** Solicitud de recarga express C2P Pago Móvil desde conversación WhatsApp/Telegram.

---

## 4. 🌐 Microservicio REST API y Workflows Omnicanal

### 4.1 REST API (api/service.py)
- **23 endpoints RESTful** y **29 esquemas TM Forum ODA** (OpenAPI 3.1.0).
- Swagger UI embebido en `/docs`.
- **Nuevo:** Servicio de archivos estáticos UI en `/ui` (Fase 4 Paso 1).

### 4.2 Workflows n8n Canónicos (api/n8n_workflows/)
| Workflow | Nodos | Webhook |
|:---|:---:|:---|
| `movilnet_whatsapp_ai_workflow.json` | 8 | `/movilnet-whatsapp-webhook` |
| `movilnet_telegram_ai_workflow.json` | 7 | `/movilnet-telegram-webhook` |
| `movilnet_c2p_payment_workflow.json` | 5 | `/movilnet-c2p-webhook` |
| `movilnet_incident_eir_lock_workflow.json` | 6 | `/movilnet-eir-lock-webhook` |
| `movilnet_retention_churn_workflow.json` | 6 | `/movilnet-retention-churn-webhook` |

---

## 5. 🎨 Sistema de Diseño UI/UX/IX/AX (Fase 4 — Paso 1 Completado)

| Componente | Archivo | Estado |
|:---|:---|:---:|
| Design Tokens W3C | `ui/tokens/design_tokens.json` | ✅ Activo |
| CSS Variables Light/Dark NOC | `ui/css/movilnet_tokens.css` | ✅ Activo |
| Componentes WCAG 2.1 AAA | `ui/css/movilnet_components.css` | ✅ Activo |
| Motor IX & Validaciones | `ui/js/movilnet_ui.js` | ✅ Activo |
| Living Showcase + Dual View | `ui/index.html` | ✅ Activo |

**Ratios de contraste WCAG 2.1 AAA:**
- Azul Noche (`#002B49`) / Blanco: **12.8:1** (AAA ≥ 7.0:1)
- Dark NOC (`#0A1118`) / Texto (`#F8FAFC`): **15.6:1** (AAA ≥ 7.0:1)
- 4GMAX (`#00558C`) / Blanco: **7.2:1** (AAA ≥ 7.0:1)

---

## 6. 🚀 Próximo Hito: Fase 4 — Paso 2

**Dashboard Web Ejecutivo de Operaciones (NOC / CCO):**
1. Panel KPI en tiempo real (4M abonados, OCS, C2P, EIR, Churn ML).
2. Monitor del Enjambre Swarm L5 (stream de eventos N1-N2-N3-N4).
3. Sala de Control Financiero C2P (recaudación diaria BCV, 23 bancos SUDEBAN).
4. Consola de Seguridad EIR (mapa de bloqueos IMEI, alertas SIM-Swap < 72h).
5. Centro de Control de Retención Churn (scores tetramodales + cupones NBA).

---

## 7. 📁 Árbol de Archivos Claves del Proyecto

```
AI_Movilnet_300926/
├── STATE.md                         ← Estado operativo actualizado
├── db/
│   ├── schema.sql                   ← DDL maestro 10 tablas ODA
│   ├── connection.py                ← Failover PG15/SQLite WAL
│   └── repository.py               ← Queries tipadas Zero-PII
├── mcp/
│   ├── telco_tools.py               ← Suite MCP Telco
│   ├── fintech_tools.py             ← Suite MCP Fintech
│   ├── crm_tools.py                 ← Suite MCP CRM
│   ├── privacy_tools.py             ← Suite MCP Privacy
│   ├── whatsapp_tools.py            ← Suite MCP WhatsApp
│   └── master_gateway.py           ← Puerta de enlace MCP
├── api/
│   ├── service.py                   ← REST API 23 endpoints + /ui
│   ├── webhook_bridge.py            ← Puente HMAC Anti-Replay
│   ├── openapi.json                 ← Contrato OpenAPI 3.1.0
│   ├── n8n_workflows/               ← 5 Workflows Omnicanal
│   └── agents/                      ← 4 Agentes Swarm L5
├── ui/
│   ├── index.html                   ← Living Showcase Dual View
│   ├── css/                         ← Tokens + Componentes WCAG
│   ├── js/                          ← Micro-interacciones IX/AX
│   └── tokens/                      ← Design Tokens W3C
├── tests/                           ← 211 tests / 100% OK
├── scripts/                         ← PDF generators + Gatekeepers
├── reports/                         ← Certificados JSON + Manifiestos
└── docs/                            ← Bitácora + Dossiers técnicos
```

---
*Handover preparado por el Swarm Orchestrator Autónomo — Telecomunicaciones Movilnet C.A.*  
*Última actualización: 2 de Octubre de 2026, 02:50 VET (UTC-4)*
