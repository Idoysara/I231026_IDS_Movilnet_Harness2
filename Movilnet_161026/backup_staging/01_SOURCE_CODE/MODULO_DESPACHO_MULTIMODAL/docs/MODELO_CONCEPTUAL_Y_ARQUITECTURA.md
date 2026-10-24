# 🏛️ MODELO CONCEPTUAL, TOPOLOGÍA Y ARQUITECTURA DE DESPACHO MULTIMODAL
**Proyecto:** Telecomunicaciones Movilnet C.A. — Módulo Autónomo de Despacho Multimodal  
**Gobernanza:** Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal  
**Nivel de Ingeniería:** Grado Militar / Carrier-Grade Telco (Escalabilidad a 4.000.000 Abonados)  

---

## 1. 🎯 Visión Arquitectónica y Principios de Diseño

El **Módulo de Despacho Multimodal** es un microecosistema de software autónomo, desacoplado y portable diseñado para dotar a agentes de inteligencia artificial conversacional de capacidades de percepción y expresión a través de canales ricos de mensajería (WhatsApp, Telegram, PWA).

### Principios Fundamentales:
1. **Percepción Multimodal Asimétrica:** Capacidad de ingerir notas de voz, fotos de transferencias, capturas de pantalla, documentos PDF y videos cortos, transformándolos en texto estructurado y vectores semánticos en tiempo real (<2s).
2. **Expresión Rica Contextual:** El agente no responde únicamente con texto plano; genera comprobantes oficiales en PDF con código QR verificable, audios de voz sintética ultrarrealista (TTS en OGG Opus), e imágenes informativas con diseño institucional.
3. **Aislamiento Multi-Tenant Lógico ($1 \leftrightarrow N$):** Cada abonado dispone de una bóveda privada virtual (`/vaults/usr_{hash}/`), protegiendo su privacidad mediante funciones hash irreversibles HMAC-SHA256 y cuotas de almacenamiento estrictas (50 MB por usuario).
4. **Portabilidad de Nivel 5:** El módulo no depende de ningún framework web específico para su lógica central; opera bajo **Arquitectura Hexagonal (Puertos y Adaptadores)** y puede ser embebido como biblioteca en Python o ejecutado como microservicio REST autónomo en el puerto `:8025`.

---

## 2. 🗺️ Topología General del Sistema

El siguiente diagrama detalla la interacción entre el usuario, los canales de entrada, la capa de bóveda privada, los motores especializados de inteligencia artificial y el subsistema de despacho:

```mermaid
flowchart TD
    subgraph CLIENTE_OMNICANAL ["Capas de Entrada del Abonado"]
        WA_IN["📱 WhatsApp (Meta Cloud API / Sandbox n8n)"]
        TG_IN["🤖 Telegram Bot API"]
        PWA_IN["🌐 Portal PWA 4GMAX"]
    end

    subgraph API_GATEWAY ["Puerta de Entrada & Seguridad (:8025)"]
        AUTH_ROUTER["Validador Criptográfico & Router de Ingesta"]
        HMAC_BLIND["Generador de Hash Ciego HMAC-SHA256"]
    end

    subgraph VAULT_CONTROLLER ["Gestor de Bóvedas Privadas (vault_service.py)"]
        QUOTA_GUARD{"¿Cuota < 50MB?"}
        STORAGE_DISK["Almacenamiento Seguro /vaults/usr_{hash}/"]
        DB_WAL[("Base de Datos WAL: multimodal_vault.db")]
    end

    subgraph PIPELINE_MULTIMODAL ["Motores Especializados de Percepción"]
        AUDIO_ENGINE["🎙️ Whisper STT Engine (Audio a Texto)"]
        VISION_ENGINE["📸 Gemini Vision / OCR Engine (Foto a Datos)"]
        PDF_ENGINE["📄 PyMuPDF Parser (Extracción Documental)"]
        VIDEO_ENGINE["🎥 Frame Extractor (FFmpeg)"]
    end

    subgraph SWARM_REASONING ["Núcleo de Razonamiento y Decisión"]
        FAST_PATH["⚡ Fast-Path Multimodal (<1ms)"]
        ORCHESTRATOR["🧠 Orquestador Swarm L5"]
        DEPT_AGENTS["👥 Agentes Departamentales (C2P / OCS / Soporte)"]
    end

    subgraph RICH_DISPATCHER ["Motor de Despacho Enriquecido"]
        PDF_GEN["📑 Generador de Comprobantes PDF (ReportLab/WeasyPrint)"]
        TTS_GEN["🗣️ Sintetizador de Voz TTS (Edge/Local Opus)"]
        PWA_SUFFIX["🌐 Inyector de Enlace PWA Universal"]
    end

    WA_IN & TG_IN & PWA_IN --> AUTH_ROUTER
    AUTH_ROUTER --> HMAC_BLIND --> QUOTA_GUARD
    
    QUOTA_GUARD -- Excedida --> REJECT_MSG["Rechazo Amigable: Bóveda Llena"]
    QUOTA_GUARD -- Aprobada --> STORAGE_DISK
    STORAGE_DISK --> DB_WAL

    STORAGE_DISK -. Audio .-> AUDIO_ENGINE
    STORAGE_DISK -. Foto/Imagen .-> VISION_ENGINE
    STORAGE_DISK -. Documento .-> PDF_ENGINE
    STORAGE_DISK -. Video .-> VIDEO_ENGINE

    AUDIO_ENGINE & VISION_ENGINE & PDF_ENGINE & VIDEO_ENGINE --> FAST_PATH
    FAST_PATH --> ORCHESTRATOR --> DEPT_AGENTS
    
    DEPT_AGENTS --> RICH_DISPATCHER
    PDF_GEN & TTS_GEN --> PWA_SUFFIX
    PWA_SUFFIX --> WA_IN & TG_IN & PWA_IN
```

---

## 3. 🔄 Diagramas de Secuencia por Tipo de Flujo

### 3.1. Flujo 1: Ingesta de Nota de Voz (Audio PTT)
El abonado envía una nota de voz consultando su saldo o reportando una avería. El sistema descarga el audio, lo almacena en su bóveda, lo transcribe a texto y lo entrega al orquestador conversacional.

```mermaid
sequenceDiagram
    autonumber
    actor Abonado as Abonado WhatsApp
    participant Gateway as API Gateway (:8025)
    participant Vault as Vault Storage Engine
    participant Whisper as Transcriptor Whisper STT
    participant Agente as Orquestador IA (MOVI)

    Abonado->>Gateway: Envía Nota de Voz (.ogg Opus)
    Gateway->>Gateway: Valida cabeceras y calcula HMAC-SHA256(MSISDN)
    Gateway->>Vault: Almacena en /vaults/usr_{hash}/audio/
    Vault->>Vault: Actualiza cuota usada en DB
    Gateway->>Whisper: transcribe_audio(audio_path, language='es')
    Whisper-->>Gateway: Retorna texto: "Hola, quiero saber mi saldo actual"
    Gateway->>Agente: Inyecta mensaje de texto con metadato (input_type='AUDIO')
    Agente-->>Abonado: Responde con saldo OCS + Enlace PWA Universal
```

---

### 3.2. Flujo 2: Ingesta y Validación de Voucher de Pago Móvil C2P (Foto/Imagen)
El abonado envía la captura de pantalla del pago móvil para recargar su línea. El motor de visión extrae automáticamente la referencia bancaria, el banco emisor y el monto en bolívares.

```mermaid
sequenceDiagram
    autonumber
    actor Abonado as Abonado WhatsApp
    participant Gateway as API Gateway (:8025)
    participant Vault as Vault Storage Engine
    participant Vision as Motor OCR / Gemini Vision
    participant C2PAgent as Agente FinTech C2P
    participant Banco as Core Bancario SUDEBAN

    Abonado->>Gateway: Envía Captura de Pantalla (.jpg / .png)
    Gateway->>Vault: Guarda en /vaults/usr_{hash}/images/
    Gateway->>Vision: extract_voucher_data(image_path)
    Vision-->>Gateway: JSON { banco: "0102", monto: "250.00", ref: "84729104" }
    Gateway->>C2PAgent: reconcile_payment(msisdn, ref, monto)
    C2PAgent->>Banco: Consulta referencia bancaria
    Banco-->>C2PAgent: Referencia Válida y Acreditada
    C2PAgent-->>Abonado: Confirmación de Pago + Nuevo Saldo Acreditado
```

---

### 3.3. Flujo 3: Despacho Saliente de Comprobante Oficial en PDF
Cuando el abonado completa exitosamente una recarga o trámite, el sistema compila un comprobante PDF con código QR y lo envía directamente por WhatsApp.

```mermaid
sequenceDiagram
    autonumber
    participant Agente as Agente FinTech C2P
    participant PDFEngine as Generador PDF (ReportLab)
    participant Vault as Vault Storage Engine
    participant Meta as Meta Cloud API
    actor Abonado as Abonado WhatsApp

    Agente->>PDFEngine: generate_receipt_pdf(transaction_id, data)
    PDFEngine->>Vault: Guarda en /vaults/usr_{hash}/documents/recibo_847291.pdf
    Vault-->>Agente: Retorna ruta y URL pública/firmada del archivo
    Agente->>Meta: POST /messages { type: "document", url: pdf_url, caption: "Recibo Oficial" }
    Meta-->>Abonado: Entrega documento PDF con botón de descarga
```

---

## 4. ⚙️ Máquina de Estados FSM del Activo Multimedia

Cada archivo que ingresa o sale del módulo atraviesa una máquina de estados determinista (FSM) que garantiza resiliencia, idempotencia y contención de fallos:

```mermaid
stateDiagram-v2
    [*] --> RECIBIDO: Ingesta Webhook / API
    
    RECIBIDO --> VALIDANDO_INVARIANTES: Chequeo de Magic Bytes y Tamaño
    VALIDANDO_INVARIANTES --> RECHAZADO: Tipo no permitido o tamaño > límite
    VALIDANDO_INVARIANTES --> VERIFICANDO_CUOTA: Chequeo de espacio en Bóveda
    
    VERIFICANDO_CUOTA --> CUOTA_EXCEDIDA: Uso supera los 50 MB
    VERIFICANDO_CUOTA --> ALMACENADO: Guardado seguro en disco y DB
    
    ALMACENADO --> EN_PROCESAMIENTO: Disparo de Worker (STT/OCR/Parser)
    EN_PROCESAMIENTO --> PROCESADO_OK: Transcripción / Extracción exitosa
    EN_PROCESAMIENTO --> ERROR_PROCESAMIENTO: Fallo de motor (Timeout/Corrupción)
    
    ERROR_PROCESAMIENTO --> REINTENTO: Reintento con Full Jitter (hasta 3 veces)
    REINTENTO --> PROCESADO_OK: Éxito en reintento
    REINTENTO --> FALLO_DEFINITIVO: Agotado -> Notificación a DLQ
    
    PROCESADO_OK --> ENRUTADO_A_AGENTE: Entrega de payload al orquestador
    ENRUTADO_A_AGENTE --> COMPLETADO: Despacho de respuesta final
    
    COMPLETADO --> PURGADO_TTL: Cron nocturno > 30 días (Zero-PII)
    PURGADO_TTL --> [*]
    RECHAZADO --> [*]
    CUOTA_EXCEDIDA --> [*]
    FALLO_DEFINITIVO --> [*]
```

---

## 5. 🛡️ Políticas de Seguridad y Aislamiento de Bóvedas

### 5.1. Prevención de Ataques Path Traversal
El sistema prohíbe el uso de cadenas crudas ingresadas por el usuario para construir rutas de archivos en disco. Toda ruta se normaliza mediante:
```python
def resolve_secure_path(base_dir: str, filename: str) -> str:
    # Sanitiza el nombre de archivo eliminando secuencias peligrosas
    safe_name = os.path.basename(filename)
    full_path = os.path.abspath(os.path.join(base_dir, safe_name))
    if not full_path.startswith(os.path.abspath(base_dir)):
        raise SecurityException("Intento de violación de Path Traversal detectado")
    return full_path
```

### 5.2. Verificación de Integridad por Magic Bytes
No se confía en la extensión del archivo (`.jpg`, `.mp3`). El motor inspecciona los primeros 16 bytes del búfer para verificar la firma binaria real del formato:
* **JPEG:** `FF D8 FF`
* **PNG:** `89 50 4E 47 0D 0A 1A 0A`
* **PDF:** `25 50 44 46` (`%PDF`)
* **OGG/Opus:** `4F 67 67 53` (`OggS`)
* **MP4:** `66 74 79 70` (`ftyp`)

---

## 6. 📊 Resumen de Especificaciones de Rendimiento (SLAs)

| Operación | Latencia Objetivo | P95 Garantizado | Política de Timeout |
| :--- | :---: | :---: | :---: |
| **Verificación de Bóveda y Cuota (SQL)** | `<0.5 ms` | `<1.0 ms` | 50 ms |
| **Guardado de Archivo en Disco (I/O)** | `<10 ms` | `<25 ms` | 200 ms |
| **Transcripción de Nota de Voz (<30s)** | `<1.5 s` | `<2.5 s` | 5.0 s (Fallback a mensaje de espera) |
| **Extracción OCR de Voucher C2P** | `<1.2 s` | `<2.0 s` | 4.0 s |
| **Generación de Comprobante PDF** | `<150 ms` | `<300 ms` | 1.0 s |
| **Despacho Saliente HTTP (Meta API)** | `<100 ms` | `<250 ms` | 2.0 s |
