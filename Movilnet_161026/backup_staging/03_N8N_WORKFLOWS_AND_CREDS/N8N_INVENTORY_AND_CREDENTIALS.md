# 📦 Inventario y Especificaciones de Workflows n8n — CORE_MOVILNET

Este directorio contiene los flujos de trabajo (Workflows) exportados en formato JSON estándar, listos para importarse en cualquier instancia n8n (v1.x o superior) On-Premise o Cloud.

## 1. Catálogo de Workflows Exportados

| Archivo JSON | Descripción / Propósito | Integraciones / Nodos Clave |
| :--- | :--- | :--- |
| `viki_lpgtec_v2_ids_instant_dispatch.json` | Flujo Maestro de Despacho Inmediato Viki v2 | Webhooks, Router L5, Core API Ingest, AI Agents |
| `viki_lpgtec_v2_ids_aaa_certified.json` | Flujo Certificado AAA con validación de tokens | HMAC SHA-256 Auth, Postgres Storage, Circuit Breaker |
| `viki_lpgtec_v2_ids_with_google_suite.json` | Orquestación con Google Workspace | Gmail API, Google Calendar, Google Drive |
| `viki_lpgtec_v2_ids_with_movilnet.json` | Enlace de Telecomunicaciones y CRM | Movilnet Core PWA, PII Vault, Balances API |
| `viki_lpgtec_v2_ids_live.json` | Flujo productivo de contingencia | Webhooks de mensajería, Ingest fallback |
| `movilnet_whatsapp_ai_workflow.json` | Atención al abonado vía WhatsApp Business | Meta Cloud API, Gemini 2.5 Flash, FAQ Retriever |
| `movilnet_telegram_ai_workflow.json` | Bot corporativo de autogestión Telegram | Telegram Bot API, Router de consultas |
| `movilnet_c2p_payment_workflow.json` | Conciliación de Pagos Móviles C2P / Sudeban | Validación Bancaria, Actualización de Balances |
| `movilnet_retention_churn_workflow.json` | Análisis predictivo de Churn y Fidelización | Scoring de retención, Notificaciones promocionales |
| `movilnet_incident_eir_lock_workflow.json` | Bloqueo por IMEI/EIR en caso de robo o extravío | EIR Security API, Notificación a operadoras |

---

## 2. Credenciales Requeridas para Despliegue en Servidor del Cliente

Para levantar estos flujos en una nueva instancia de n8n, el equipo de sistemas debe aprovisionar las siguientes credenciales en el panel `Credentials` de n8n:

1. **Google OAuth2 API (Google Cloud Console):**
   - Scopes: `https://mail.google.com/`, `https://www.googleapis.com/auth/calendar`, `https://www.googleapis.com/auth/drive`
   - Client ID & Client Secret
2. **Meta Cloud API / WhatsApp Business Platform:**
   - Access Token de sistema
   - Phone Number ID
   - Verify Token de Webhooks
3. **Telegram Bot Token:**
   - Token emitido por `@BotFather`
4. **PostgreSQL Database Connection:**
   - Host: `ids_postgres_db` (o IP del servidor)
   - Port: `5432` / `5433`
   - User: `ids_user`
   - Database: `ids_ag_nblm_stich`
5. **Movilnet Core API Token:**
   - Header: `X-API-Key` o Bearer Token configurado en el archivo `.env` del Core.
