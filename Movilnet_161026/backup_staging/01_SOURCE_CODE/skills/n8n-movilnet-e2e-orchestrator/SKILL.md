---
name: n8n-movilnet-e2e-orchestrator
description: Orquestador integral y certificador del ciclo completo de datos Movilnet (Abonado) ↔ Input (n8n) ↔ Nodos (n8n) ↔ Output (n8n) ↔ Movilnet. Gobierna el enrutamiento de intenciones Telco, la inyección del nodo Fast-Path ODA en el canvas de n8n, el despacho estructurado hacia Evolution API y la confirmación de entrega en tiempo real.
---

# 🔁 n8n Movilnet E2E Closed-Loop Orchestrator

## 1. Misión
Gobernar, auditar y certificar que cada mensaje enviado por un abonado en WhatsApp complete el ciclo cerrado de 5 tramos sin pérdidas, sin alucinación y con latencia total inferior a 1200ms:

```
[1. ABONADO] ➔ [2. INPUT N8N] ➔ [3. NODOS N8N] ➔ [4. MOVILNET CORE] ➔ [5. OUTPUT N8N] ➔ [1. ABONADO]
```

---

## 2. Los 5 Tramo-Invariantes del Ciclo

### Tramo 1: Abonado ➔ Ingress n8n
* Evento: `messages.upsert` emitido por Evolution API al webhook `/webhook/messages_upsert`.
* Validación: Filtrar mensajes donde `fromMe == true` para prevenir bucles de auto-respuesta.

### Tramo 2: Ingress n8n ➔ Normalización
* Nodo `Edit Fields`: Extraer `server_url`, `instance`, `apikey`, `remoteJid` y `message_id`.
* Nodo `Switch`: Enrutamiento multimodal (Texto, Audio, Imagen, Video, PDF).
* Nodo `Chat`: Unificación en el campo `{ "Content": "..." }`.

### Tramo 3: Nodos n8n ➔ Movilnet Core (Fast-Path ODA)
* El nodo inyectado `Movilnet Core - Fast-Path ODA` dispara un POST a:
  `/api/v1/n8n/webhook-ingest`
* Si la intención es Telco (`CONTRACT_INFO`, `BALANCE_CHECK`, `RECHARGE_C2P`, `EMERGENCY_EIR`), Movilnet Core resuelve en $<15\text{ ms}$ a $\$0.00$ tokens consultando SQLite WAL / PostgreSQL ODA.

### Tramo 4: Movilnet Core ➔ Output n8n
* Movilnet Core genera el objeto estructurado `n8n_egress_payload`:
  ```json
  {
    "instanceId": "Viki LPGTEC",
    "number": "584142650088@s.whatsapp.net",
    "options": { "delay": 1500 },
    "text": "Estimado(a) Francisco Landaeta..."
  }
  ```
* Se conecta a `Merge - Respuestas 5` ➔ Nodo `Code` (limpieza de Markdown).

### Tramo 5: Output n8n ➔ Abonado (WhatsApp)
* Nodo `HTTP Request`: Dispara POST a `/message/sendText/{instance}` en Evolution API.
* El cliente recibe el mensaje institucional directamente en su aplicación de WhatsApp.

---

## 3. Comandos de Verificación del Ciclo
```bash
# 1. Probar el endpoint integrado en Movilnet Core
venv/bin/pytest tests/test_n8n_full_cycle.py -v

# 2. Inyectar o regenerar el canvas de n8n con el nodo Movilnet
venv/bin/python3 scripts/inject_movilnet_node_into_n8n.py --test

# 3. Validar el subagente despachador
venv/bin/python3 api/agents/agent_n8n_dispatcher.py --test
```
