# 🛡️ Regla de Proyecto: Webhook Canónico Exclusivo n8n (`messages_upsert4`)

Esta directiva es de cumplimiento obligatorio, incondicional e inviolable para todo agente, script, servicio backend, despliegue en Render y orquestador en este proyecto (`Movilnet_PWA`).

---

## 🏛️ 1. Mandato Único de Webhook

Queda terminantemente prohibido utilizar, invocar, configurar o aceptar cualquier URL de webhook de n8n distinta a:

```text
"webhookUrl": "https://n8n.lpgtec.net/webhook/messages_upsert4"
```

### Parámetros Canónicos Certificados:
* **Host Canónico:** `https://n8n.lpgtec.net`
* **Ruta de Producción:** `/webhook/messages_upsert4`
* **URL Completa Canónica:** `https://n8n.lpgtec.net/webhook/messages_upsert4`
* **Destino Interno Docker (Evolution API):** `http://n8n:5678/webhook/messages_upsert4`
* **Workflow n8n Asociado:** `sNMbtiEiTkuQ9OCY` (*Viki_LPGTEC_v2_ids_Movilnet_Google_Suite_Full*)

---

## 🚫 2. Endpoints Estrictamente Prohibidos

1. ❌ `https://n8n.lpgtec.net/webhook/messages_upsert` (Heredado / Viki Personal legacy `WdWU8G9EggQDMack` — Prohibido).
2. ❌ `https://n8n.lpgtec.net/webhook/viki-chat` (Inactivo / Web Chat `1xcXxHsgN20LTenq` — Prohibido).
3. ❌ Cualquier ruta alternativa no homologada en este repositorio.

Cualquier referencia heredada a `/webhook/messages_upsert` que ingrese por variables de entorno (`N8N_WEBHOOK_URL`) o llamadas API debe ser interceptada y auto-promocionada en el borde por `core/n8n_webhook_resolver.py` a `messages_upsert4`.

---

## 🔬 3. Manejo de Eventos Recibidos en `messages_upsert4`

La pasarela de mensajería (Evolution API / Baileys) emite múltiples tipos de eventos hacia este webhook canónico:

| Tipo de Evento (`event`) | Descripción | Acción Requerida en Movilnet Core |
| :--- | :--- | :--- |
| **`messages.upsert`** | Mensaje nuevo entrante de WhatsApp (texto, audio, imagen, pdf). | **PROCESAR:** Fast-Path SQLite / Árbol ODA / Gemini. |
| **`contacts.update`** | Sincronización de perfil o contacto (`@lid`, nombre `pushName`). | **DESCARTAR (<1ms):** `FilterVerdict.DROP_CONTACTS_UPDATE`. |
| **`presence.update`** | Estado en línea (`available`, `composing`). | **DESCARTAR (<1ms):** `FilterVerdict.DROP_PRESENCE_UPDATE`. |
| **`chats.update`** | Actualización de lista de chats en WhatsApp. | **DESCARTAR (<1ms):** `FilterVerdict.DROP_CHATS_UPDATE`. |
| **`send.message`** | Eco de mensaje saliente emitido por el propio bot. | **DESCARTAR (<1ms):** `FilterVerdict.DROP_FROM_ME_ECHO`. |

---

## 🛡️ 4. Guardarraíl de Código y Verificación

1. **`core/n8n_webhook_resolver.py`** es la única autoridad de resolución de URL de webhook.
2. Todas las suites de pruebas (`tests/test_n8n_webhook_resolver.py`, `tests/test_n8n_full_cycle.py`) deben certificar que el endpoint resuelto sea exactamente `https://n8n.lpgtec.net/webhook/messages_upsert4`.
3. Ningún commit o despliegue a Render puede ser aprobado si altera este webhook canónico.
