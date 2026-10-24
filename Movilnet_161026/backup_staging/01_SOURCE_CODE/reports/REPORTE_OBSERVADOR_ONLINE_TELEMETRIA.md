# 📡 Reporte de Telemetría E2E — Observador Continuo de Ecosistema
**ID de Auditoría:** `OBS-E2E-58BF3E7325CE` | **Sello SHA-256:** `SEAL-OBS-00AAA4EDD26A2E50333C7D78`
**Fecha / Hora (UTC):** `2026-10-22T11:46:54.730908+00:00` | **Línea Bot:** `+58 424 153 3712`
**Estado de Salud:** `DEGRADACION_PROVEEDOR_IA_EXTERNO` (Infraestructura 5/5 Online)

---

## 1. 🌐 Matriz de los 5 Eslabones (Celulares ↔ n8n ↔ Movilnet Core ↔ Celulares)

| # | Eslabón | Origen ➔ Destino | Latencia | Estado | Diagnóstico |
| :-: | :--- | :--- | :-: | :-: | :--- |
| **1** | **Ingesta Celulares ➔ Evolution API** | `Red Móvil GSM/LTE (Abonados Externos)` ➔ `Evolution API (+58 424 153 3712)` | `1.1ms` | 🟢 ACTIVO / RECIBIENDO | Webhook WhatsApp activo. Múltiples números (0414-2554590, 0414-2650088) recibidos. |
| **2** | **Orquestador n8n Cloud Webhook & Router** | `Evolution API (/webhook/messages_upsert)` ➔ `n8n Cloud Workflow sNMbtiEiTkuQ9OCY (74 Nodos)` | `2.4ms` | 🟢 ACTIVO (Flujo Producción) | Workflow sNMbtiEiTkuQ9OCY activo. Router de 10 salidas deterministas operativo. |
| **3** | **Túnel Seguro n8n ➔ Movilnet Core (MacBook)** | `n8n Cloud (Nodo Movilnet Core - Fast-Path ODA)` ➔ `MacBook Pro (100.87.72.93:8010 / Tailscale utun1)` | `88.44ms` | 🟢 ENLACE CONECTADO | Túnel Tailscale VPN asignado a IP 100.87.72.93. Endpoint /api/v1/n8n/webhook-ingest. |
| **4** | **Motor Core ODA & SQLite WAL Local** | `api/service.py (:8010)` ➔ `db/local_movilnet.db (11 Tablas ODA + HMAC-SHA256)` | `1.241ms` | 🟢 RESUELTO (<0.15ms • 0 Tokens) | Subagente N8nDispatcherAgent responde consultas telco deterministas en <0.15ms. |
| **5** | **Despacho WhatsApp Celulares de Salida** | `n8n Cloud (Nodo HTTP Request /sendText)` ➔ `Evolution API ➔ Pantalla WhatsApp del Abonado` | `280.0ms` | 🟢 ENTREGA CONFIRMADA (DELIVERY_ACK) | Paquetes HTTP entregados a terminales celulares con acuse de recibo de red. |

---

## 2. 📱 Historial Forense de Celulares Recibidos en Vivo (Webhook +58 424 153 3712)

| Ejecución | Celular Remitente | Nombre | Mensaje | Duración | Ruta Activada | Estado |
| :---: | :---: | :---: | :--- | :-: | :--- | :-: |
| `#9644` | `0414-2554590` | **Ids** | *"Pero cómo está el tiempo en caracas"* | `1.68s` | `RAMA_9_AI_GEMINI` | 🔴 ERROR |
| `#9643` | `0414-2554590` | **Ids** | *"Quiero ir al cine"* | `26.06s` | `RAMA_9_AI_GEMINI` | 🟢 SUCCESS |
| `#9642` | `0414-2554590` | **Ids** | *"Hola"* | `36.33s` | `RAMA_9_AI_GEMINI` | 🟢 SUCCESS |
| `#9641` | `N/A (Editor Manual)` | **Admin n8n** | *"Ejecución de prueba manual en lienzo n8n"* | `300.0s` | `PRUEBA_MANUAL_EDITOR` | 🔴 ERROR |
| `#9640` | `0414-2554590` | **Ids** | *"Hola"* | `52.36s` | `RAMA_9_AI_GEMINI` | 🔴 ERROR |
| `#9638` | `0414-2554590` | **Ids** | *"Necesito una merienda"* | `92.23s` | `RAMA_9_AI_GEMINI (Tool Recetas)` | 🔴 ERROR |
| `#9637` | `0414-2554590` | **Ids** | *"Que novedad tenemos"* | `7.66s` | `RAMA_9_AI_GEMINI (SerpAPI Google News)` | 🟢 SUCCESS |
| `#9636` | `0414-2554590` | **Ids** | *"Hokaaaaaaa"* | `1.81s` | `RAMA_9_AI_GEMINI` | 🟢 SUCCESS |
| `#9635` | `0414-2554590` | **Ids** | *"Podemos probar si estás funcionando"* | `2.85s` | `RAMA_9_AI_GEMINI` | 🟢 SUCCESS |
| `#9623` | `0414-2650088` | **Francisco Landaeta** | *"Calcular diferencial cambiario"* | `1.28s` | `RAMA_BCV_FINTECH` | 🟢 SUCCESS |

---

## 3. 🚨 Hallazgo Crítico del Observador: Incidente en Proveedor Externo de IA
* **Llegada del Mensaje:** Los mensajes `"Necesito una merienda"` (#9638) y `"Hola"` (#9640) entraron exitosamente al webhook.
* **Falla en n8n Cloud:** El nodo `Google Gemini Chat Model` arrojó `503 Service Unavailable`, bloqueando la respuesta.
* **Ventaja de Movilnet Core:** La **Rama 8 (Fast-Path Core :8010)** NO usa Gemini externo; resuelve en `<0.15ms` localmente desde SQLite WAL.

---
*Certificación generada automáticamente por `scripts/observer_online_telemetry.py` bajo Protocolo Decagonal.*