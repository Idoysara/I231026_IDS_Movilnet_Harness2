# 🔄 Flujo N8N: Deflector Omnicanal Cazador de Ofertas Movilnet
**Ruta del Archivo Importable:** [`cazador_ofertas_n8n_workflow.json`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/n8n/cazador_ofertas_n8n_workflow.json)  
**Canales Soportados:** WhatsApp (Meta Cloud / Whapify), Telegram Bot API y PWA Mobile-First  
**Backend Vinculado:** Core API REST FastAPI `:8030` (`POST /api/deflector/n8n`)

---

## 🗺️ 1. Diagrama de la Topología de Nodos en N8N

```mermaid
flowchart TD
    subgraph Triggers ["1. Triggers de Entrada"]
        W1["🟢 Webhook WhatsApp<br/>(Meta Cloud / Whapify)"]
        W2["🔵 Webhook Telegram<br/>(Telegram Bot API)"]
        W3["🟣 Webhook PWA Event<br/>(App Móvil :8030)"]
    end

    subgraph Normalization ["2. Normalización & Seguridad"]
        N1["⚙️ Normalizador Omnicanal<br/>(JavaScript Code Node)"]
        F1{"❓ ¿Es Abonado Movilnet?<br/>(0416 / 0426)"}
        REJ["🛑 Rechazo Operadora Ajena<br/>(HTTP 403 Exclusividad)"]
    end

    subgraph CoreEngine ["3. Invocación al Motor Core"]
        API["📡 HTTP Request -> Cazador API<br/>POST :8030/api/deflector/n8n<br/>(Radar Haversine + Cero Alucinación)"]
        ENR["✨ Enriquecedor de Respuesta<br/>(Magic Link HMAC + Zero-Rating)"]
    end

    subgraph Dispatchers ["4. Despachadores de Salida"]
        SW{"🔀 Switch Canal"}
        OUT_WA["📲 Respuesta WhatsApp Webhook<br/>(Texto + Magic Link)"]
        OUT_TG["✈️ Respuesta Telegram Webhook<br/>(Inline WebApp Button)"]
        OUT_PWA["📱 Respuesta PWA Directa<br/>(JSON con Anillos & Ofertas)"]
    end

    W1 --> N1
    W2 --> N1
    W3 --> N1

    N1 --> F1
    F1 -->|No Movilnet (0412/0414)| REJ
    F1 -->|Movilnet Válido| API

    API --> ENR
    ENR --> SW
    SW -->|Canal WhatsApp| OUT_WA
    SW -->|Canal Telegram| OUT_TG
    SW -->|Canal PWA| OUT_PWA
```

---

## 🧩 2. Inventario Detallado de los 11 Nodos

1. **`Webhook WhatsApp`:** Expone el endpoint `/webhook/cazador-whatsapp`. Recibe eventos entrantes de Meta WhatsApp Business Cloud API o Evolution API/Whapify.
2. **`Webhook Telegram`:** Expone el endpoint `/webhook/cazador-telegram`. Configurado como Webhook para bots de Telegram (`setWebhook`).
3. **`Webhook PWA Event`:** Expone el endpoint `/webhook/cazador-pwa`. Permite a la PWA o a servicios frontend despachar consultas directas.
4. **`Normalizador Omnicanal (Code Node)`:** Código JavaScript de alta eficiencia que extrae de forma polimórfica el número del usuario, el texto o las coordenadas GPS (`lat`, `lon`), normalizando el formato venezolano a `0416...` o `0426...`.
5. **`¿Es Abonado Movilnet? (IF Node)`:** Candado de negocio que verifica si el prefijo pertenece a Movilnet.
6. **`Rechazo Operadora Ajena (Respond to Webhook)`:** Responde de forma cortesa con código HTTP 403 explicando que el programa de ahorro y Zero-Rating es exclusivo para Movilnet.
7. **`Invocar Cazador Core API (:8030) (HTTP Request)`:** Envía la petición a `http://localhost:8030/api/deflector/n8n`. El servidor ejecuta el Radar Haversine (<0.2ms), aplica el Grounding Cero Alucinación y genera el Magic Link con firma criptográfica HMAC-SHA256.
8. **`Enriquecedor de Respuesta (Code Node)`:** Adapta el payload según las capacidades de cada canal (por ejemplo, genera el botón interactivo `web_app` para Telegram).
9. **`Switch Canal Saliente (Switch Node)`:** Enruta el flujo según el canal de origen (`whatsapp`, `telegram`, `pwa`).
10. **`Respuesta WhatsApp Webhook`:** Retorna el mensaje formateado con vista previa del enlace.
11. **`Respuesta Telegram Webhook`:** Retorna el texto con teclado inline interactivo (`InlineKeyboardMarkup` con botón WebApp).
12. **`Respuesta PWA Directa`:** Retorna el JSON completo para el cliente web.

---

## 🚀 3. Instrucciones de Importación en N8N (Cero Terminal)

1. Abrir la interfaz web de **n8n** en su navegador (ej: `http://localhost:5678`).
2. En el menú superior derecho del lienzo de trabajo, hacer clic en los tres puntos (`⋮`) o presionar `Cmd + O` / `Ctrl + O`.
3. Seleccionar **"Import from File"** (Importar desde archivo).
4. Seleccionar el archivo [`cazador_ofertas_n8n_workflow.json`](file:///Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/n8n/cazador_ofertas_n8n_workflow.json).
5. Hacer clic en **"Save"** (Guardar) y activar el switch **"Active"** en la esquina superior derecha.

---

## 🧪 4. Pruebas Rápidas con `curl`

### Prueba 1: Simulación de WhatsApp con número Movilnet
```bash
curl -X POST http://localhost:5678/webhook/cazador-whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "584161234567",
            "type": "text",
            "text": { "body": "Quiero hamburguesa" }
          }]
        }
      }]
    }]
  }'
```

### Prueba 2: Simulación de Telegram con ubicación GPS (Chacao, Caracas)
```bash
curl -X POST http://localhost:5678/webhook/cazador-telegram \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "chat": { "id": 123456789 },
      "from": { "phone_number": "04269876543" },
      "location": { "latitude": 10.4925, "longitude": -66.8550 }
    }
  }'
```

### Prueba 3: Rechazo de Operadora Ajena (ej: Digitel 0412)
```bash
curl -X POST http://localhost:5678/webhook/cazador-whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "584125550000",
            "type": "text",
            "text": { "body": "ofertas" }
          }]
        }
      }]
    }]
  }'
```
Retornará:
```json
{
  "status": "rejected",
  "error": "NON_MOVILNET_SUBSCRIBER",
  "message": "👋 ¡Hola! El Cazador de Ofertas y el beneficio de navegación Zero-Rating (sin consumo de datos) es exclusivo para líneas Movilnet (0416 y 0426)."
}
```
