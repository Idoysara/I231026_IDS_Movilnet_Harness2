# 📄 Especificación Técnica: Sandbox n8n Hermano `[DEV_STAGE]`

**Flujo:** `[DEV_STAGE] Movilnet_Despacho_Multimodal_Sandbox`  
**Endpoint Webhook:** `/webhook-stage/multimodal_media_v1`  
**Destino de Backend:** `http://127.0.0.1:8025/api/v1/multimodal/process`  
**Fecha de Emisión:** 18 de Octubre de 2026  
**Gobernanza:** Universal Best Practices Engineering Rule (Pilares I, II, IV, VI y VII)

---

## 1. Principio Fundamental e Invariante de Blindaje de Producción

> [!IMPORTANT]
> **REGLA DE AISLAMIENTO INVIOLABLE:**
> El workflow productivo actual del Asistente Movilnet:
> - **ID n8n:** `sNMbtiEiTkuQ9OCY` (`Viki_LPGTEC_v2_ids_Movilnet_Google_Suite_Full`)
> - **Webhook Productivo:** `https://n8n.lpgtec.net/webhook-test/messages_upsert4`
> - **Servidor Core Producción:** Puerto `:8010`
> - **Base de Datos Producción:** `local_movilnet.db`
> 
> **PERMANECE EN ESTADO `LOCKED_FREEZE`**. Queda terminantemente prohibido modificar, editar, pausar, reconectar o desplegar código sobre dicho workflow mientras QA y directores evalúan la versión productiva.

---

## 2. Topología de Red y Comparativa de Entornos

```mermaid
graph TD
    subgraph PRODUCCION_INTOCABLE ["🔒 ENTORNO PRODUCCIÓN INTOCABLE (QA & Directores)"]
        PROD_WHATSAPP["📱 WhatsApp Meta Cloud (Prod)"] --> N8N_PROD["n8n: sNMbtiEiTkuQ9OCY\nPath: /webhook-test/messages_upsert4"]
        N8N_PROD --> CORE_8010["Servidor Core :8010\n(Render Cloud 24/7)"]
        CORE_8010 --> DB_PROD[("local_movilnet.db\n13 Tablas ODA")]
    end

    subgraph STAGING_HERMETICO ["🚀 SANDBOX HERMANO STAGING (Despacho Multimodal)"]
        DEV_TESTER["🧪 Tester QA / Script / Gateway Sandbox"] --> N8N_STAGE["n8n Hermano DEV_STAGE\nPath: /webhook-stage/multimodal_media_v1"]
        N8N_STAGE --> CORE_8025["Servidor Multimodal :8025\n(MODULO_DESPACHO_MULTIMODAL)"]
        CORE_8025 --> DB_STAGE[("multimodal_vault.db\nBóvedas Cifradas SQLite WAL")]
        CORE_8025 --> CLIENT_WA["WhatsApp Resiliente\n(Circuit Breaker + Backoff)"]
    end

    PRODUCCION_INTOCABLE ~~~|AISLAMIENTO HERMÉTICO TOTAL (SIN PUERTOS NI DB COMPARTIDOS)| STAGING_HERMETICO
```

---

## 3. Contrato de Entrada del Webhook Sandbox (`/webhook-stage/multimodal_media_v1`)

El webhook acepta dos modalidades de ingesta sin requerir cambios en el payload del cliente:

### Modalidad A: JSON con Base64 (API Gateway o Webhook n8n)
```json
{
  "phone_number": "+584166251587",
  "filename": "comprobante_banco_venezuela.jpg",
  "file_base64": "<DATOS_EN_BASE64_DEL_ARCHIVO_BINARIO>"
}
```

### Modalidad B: Multipart Form-Data (Carga Directa de Archivo)
- `phone_number`: Texto con el MSISDN (ej. `+584166251587`).
- `data`: Archivo binario adjunto (imagen JPG/PNG, audio OGG/MP3/M4A, video MP4, documento PDF).

---

## 4. Contrato de Despacho hacia el Backend Multimodal (`:8025/api/v1/multimodal/process`)

El nodo de n8n reenvía la petición normalizada al microservicio en `:8025`:

### Petición HTTP POST:
- **URL:** `http://127.0.0.1:8025/api/v1/multimodal/process`
- **Headers:** `Content-Type: application/json`
- **Timeout:** 30000 ms

### Respuesta Estructurada Exitosa (`HTTP 200 OK`):
```json
{
  "status": "PROCESSED",
  "phone_number": "+584166251587",
  "input_asset_id": "asset_4a6f8b12-9c3d-4e5f-a1b2-c3d4e5f6a7b8",
  "media_type": "IMAGE",
  "transcription": "Comprobante C2P Banco de Venezuela Ref 84729104 Bs 250.00",
  "output_asset_id": "asset_7d8e9f01-2a3b-4c5d-6e7f-8a9b0c1d2e3f",
  "reply_text": "📸 Recibimos tu comprobante y leímos estos datos:\nDetalle: Comprobante C2P Banco de Venezuela Ref 84729104 Bs 250.00\nQueda en verificación; te confirmaremos cuando sea conciliado.\n\n👉 https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html",
  "latency_ms": 142.5,
  "dispatch": {
    "success": true,
    "message_id": "wamid_mock_1_1792339187",
    "mode": "MOCK_DISPATCH",
    "delivered_to": "+584166251587"
  }
}
```

---

## 5. Instrucciones de Despliegue en la Instancia n8n

1. Acceder a la consola web de n8n (`https://n8n.lpgtec.net` o instancia local).
2. En el menú superior izquierdo, hacer clic en **Workflows** -> **Import from File**.
3. Seleccionar el archivo:
   `config/n8n_workflows/DEV_STAGE_Movilnet_Despacho_Multimodal_Sandbox.json`
4. Verificar que el Webhook quede asignado al path `multimodal_media_v1` en modo Test o Production Stage.
5. Activar el toggle de **Active** para el flujo.
6. Guardar los cambios.

---

## 6. Verificación de Aislamiento con CLI Autónomo

Para validar que el flujo de staging responde con total autonomía sin tocar producción:
```bash
python3 scripts/simulate_n8n_stage_webhook.py --test
```
O enviar un comprobante de prueba hacia el servidor de staging:
```bash
python3 scripts/simulate_n8n_stage_webhook.py --voucher
```
