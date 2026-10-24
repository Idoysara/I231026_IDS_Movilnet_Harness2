---
name: n8n-movilnet-bidirectional-bridge
description: Orquestador y certificador de la pasarela de comunicación bidireccional entre Evolution API, los Webhooks de n8n y el Núcleo Cognitivo de Telecomunicaciones Movilnet (Fast-Path ODA + Swarm L5). Garantiza integridad criptográfica HMAC-SHA256, deduplicación idempotente, latencia sub-segundo (<1200ms) y cero pérdida de eventos en el ciclo Input <--> Antigravity <--> n8n <--> Output.
---

# 🌉 n8n Movilnet Bidirectional Bridge Guardian

## 1. Misión Crítica
Este Skill gobierna, verifica y certifica la comunicación bidireccional integral del ecosistema omnicanal de Movilnet:

```
[ INPUT: WhatsApp / Evolution API ]
               ▲
               │  (Webhook POST /messages_upsert)
               ▼
[ N8N INGRESS: Workflow Viki_LPGTEC_v2_ids ]
               ▲
               │  (HTTP HMAC Handshake: X-Movilnet-Signature)
               ▼
[ ANTIGRAVITY: Movilnet Cognitive Core (Fast-Path ODA + DB SQLite/Postgres) ]
               ▲
               │  (Payload JSON Estructurado + Reply Text)
               ▼
[ N8N EGRESS: Dispatcher Node ]
               ▲
               │  (POST /message/sendText/{instance})
               ▼
[ OUTPUT: WhatsApp del Abonado ]
```

---

## 2. Invariantes Mandatorios de Certificación

### Invariante 1: Integridad Criptográfica y Anti-Replay (RFC 2104)
* Toda comunicación entre n8n y Antigravity Movilnet debe transportar las siguientes cabeceras HTTP:
  - `X-Movilnet-Signature`: Firma `HMAC-SHA256(secret, timestamp + "." + body)`.
  - `X-Movilnet-Timestamp`: Marca de tiempo Unix en segundos.
  - `X-Movilnet-Delivery-ID`: UUIDv4 único de entrega.
* **Ventana de Tolerancia:** Máximo 300 segundos. Mensajes con timestamp fuera de ventana son rechazados con `HTTP 401 Unauthorized` por ataque de repetición (*replay attack*).

### Invariante 2: Idempotencia y Deduplicación
* WhatsApp y Evolution API reintentan envíos si la red oscila.
* El puente debe registrar cada `message_id` en una memoria volátil LRU / Redis / SQLite con TTL de 24 horas. Si el ID ya fue procesado, se retorna la respuesta en caché sin re-ejecutar transacciones financieras ni debitar saldos.

### Invariante 3: Enrutamiento Dual (Fast-Path vs. Agente Cognitivo)
* **Fast-Path Determinista ($0.00 Tokens, <15 ms):**
  - Consultas de contrato ODA (`CONTRACT_INFO`).
  - Consulta de saldo y megas (`BALANCE_CHECK`).
  - Solicitud de Pago Móvil C2P (`RECHARGE_C2P`).
  - Bloqueo de línea e IMEI por hurto (`EMERGENCY_EIR`).
* **Slow-Path Cognitivo (Google Gemini 2.5 Flash, <1200 ms):**
  - Consultas libres, soporte conversacional, asesoría de planes complejos y ventas contextuales (Funnel NBA).

### Invariante 4: Formato de Salida Omnicanal Sanitizado
* El texto despachado hacia el nodo `HTTP Request` de n8n no debe contener Markdown incompatible con WhatsApp (como encabezados `#`, tablas complejas o etiquetas HTML crudas).
* Debe mantener las directrices del canal: negritas simples (`*texto*`), emojis institucionales y saltos de línea legibles.

---

## 3. Protocolo de Pruebas Automatizadas (100% Pass)
Cada cambio en el puente debe validarse ejecutando:
```bash
venv/bin/pytest tests/test_n8n_movilnet_bridge.py -v
```
Requisitos para certificación:
- 0 fallos.
- Cobertura completa de firma HMAC válida, firma inválida rechazada, replay attack rechazado y deduplicación por `message_id`.
