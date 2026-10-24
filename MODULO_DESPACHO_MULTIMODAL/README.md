# 📱 Módulo Autónomo de Despacho Multimodal en WhatsApp
**Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5**  
**Gobernanza:** Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal  
**Estado:** 🟡 **EN DESARROLLO (staging :8025)** — arquitectura y pruebas unitarias/integración OK; ver tabla "Estado real de los motores" más abajo. No integrado con producción.  

---

## 🎯 ¿Qué es este Módulo?

El **Módulo de Despacho Multimodal** es un componente de software desacoplado y portable que permite a los asistentes conversacionales de Movilnet procesar y despachar activos multimedia en WhatsApp, Telegram y portales web:

1. **Notas de Voz (Audio PTT):** Transcripción automática de voz a texto (<1.8s) y respuestas en audio sintetizado OGG/Opus.
2. **Fotografías y Capturas (Vouchers C2P):** Extracción OCR de referencias bancarias, montos y conciliación automática.
3. **Documentos (PDF):** Generación y despacho de comprobantes oficiales con código QR y archivo documental.
4. **Bóveda Privada por Abonado ($1 \leftrightarrow N$):** Almacenamiento seguro particionado (`/vaults/usr_{hash}/`), con cuota de 50 MB por usuario y purga Zero-PII tras 30 días.

---

## 🏛️ Principio de Autonomía y Cero Impacto en Producción

* **Desarrollo en Paralelo (Hermetic Parallel Staging):** Mientras el flujo central `sNMbtiEiTkuQ9OCY` en producción está en evaluación por directores y QA, este módulo opera en su propio espacio y en el **puerto `:8025`**, sin alterar ningún archivo de producción.
* **Portabilidad a Otros Proyectos:** Diseñado bajo **Arquitectura Hexagonal**. Puede ser copiado íntegramente a cualquier otro backend (Python, Node.js, Go) o ejecutado como microservicio independiente.

---

## 📂 Estructura del Repositorio

```text
MODULO_DESPACHO_MULTIMODAL/
├── README.md                                          <- Esta guía
├── INICIAR_MODULO_MULTIMODAL.command                  <- Lanzador 1-clic del servidor (:8025)
├── PROBAR_MODULO_MULTIMODAL.command                   <- Lanzador 1-clic de pruebas (100% PASS)
├── requirements.txt                                   <- Cero dependencias obligatorias
├── .env.example                                       <- Configuración declarativa
├── docs/
│   ├── HISTORIAL_CHATS_181026_ORIGEN_Y_CONCEPCION.md  <- Memoria de todos los chats de hoy 181026
│   ├── MODELO_CONCEPTUAL_Y_ARQUITECTURA.md            <- Topología, diagramas Mermaid y FSM
│   ├── DICCIONARIO_BASE_DATOS_Y_CAMPOS.md             <- Tablas, campos, DDL y prueba de $1 <-> N
│   ├── ESPECIFICACION_AGENTES_MCP_Y_ORQUESTADOR.md    <- Agentes, herramientas MCP y Swarm
│   └── GUIA_PORTABILIDAD_MULTIPROYECTO.md             <- Instrucciones de exportación a otros stacks
├── domain/                                            <- Capa de Dominio Puro
│   ├── enums.py                                       <- Tipos y enumeraciones
│   ├── models.py                                      <- Modelos de datos tipados
│   └── invariants.py                                  <- Guardas, cuotas y sufijo PWA
├── application/                                       <- Casos de Uso
│   ├── vault_service.py                               <- Gestor de Bóvedas Privadas ($1 <-> N)
│   ├── media_processor.py                             <- Pipeline unificado de procesamiento
│   ├── transcription_engine.py                        <- Motores STT y OCR
│   ├── multimodal_orchestrator.py                     <- Orquestador Swarm de extremo a extremo
│   └── rich_response_builder.py                       <- Generador de PDFs y audios salientes
├── infrastructure/                                    <- Adaptadores e Infraestructura
│   ├── database.py                                    <- Conexión SQLite WAL y DDL
│   ├── repository.py                                  <- Consultas tipadas O(1) con blind index
│   ├── storage_engine.py                              <- Filesystem seguro con guardas Path Traversal
│   └── whatsapp_client.py                             <- Cliente HTTP de mensajería
├── mcp/                                               <- Servidor Model Context Protocol
│   └── mcp_multimodal_tools.py                        <- 5 herramientas MCP JSON-RPC 2.0
├── agents/                                            <- Enjambre de Agentes
│   ├── multimodal_agent.py                            <- Fachada orquestadora
│   ├── audio_stt_subagent.py                          <- Especialista en voz
│   ├── vision_ocr_subagent.py                         <- Especialista en visión/OCR
│   └── document_subagent.py                           <- Especialista en PDFs
├── service/                                           <- Microservicio REST
│   └── server.py                                      <- Servidor HTTP en puerto :8025
├── scripts/                                           <- Scripts CLI Autónomos (Pilar II)
│   ├── init_multimodal_db.py                          <- Inicializador de base de datos (--test)
│   ├── cleanup_expired_vaults.py                      <- Demonio de purga Zero-PII (--test)
│   └── benchmark_multimodal.py                        <- Benchmark de latencia (<5ms)
├── tests/                                             <- Suite de Pruebas Automatizadas
│   ├── test_vault_invariants.py                       <- Pruebas de reglas de negocio
│   ├── test_media_pipeline.py                         <- Pruebas de almacenamiento y cuotas
│   ├── test_mcp_tools.py                              <- Pruebas de herramientas MCP
│   └── test_autonomous_service.py                     <- Pruebas de endpoints REST
└── vaults/                                            <- Almacenamiento seguro por usuario
```

---

## 🚀 Inicio Rápido (Zero Terminal)

### 1. Ejecutar las Pruebas y Certificar:
Haz doble clic en:
`PROBAR_MODULO_MULTIMODAL.command`
O ejecuta en consola:
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
**Resultado (18/10/2026):** `48 tests OK, 1 omitido` (la omitida es la prueba con Tesseract, no instalado en este equipo).

### 🔎 Estado real de los motores (leer antes de integrar)

| Componente | Estado | Detalle |
|---|---|---|
| **OCR de comprobantes** | ✅ **Real** | `Apple Vision` (nativo macOS, sin instalar nada) o `Tesseract` si existe. Falla cerrado: sin motor o sin referencia/monto → `is_valid_voucher=False`, jamás datos inventados. Probado con imagen real. |
| **Parser de comprobantes** | ✅ Real | `application/voucher_parser.py`. Tabla de bancos a validar con Movilnet/Finanzas. |
| STT (voz → texto) | 🔴 **Simulado** | Devuelve una frase fija. Pendiente (ver `docs/BITACORA_TECNICA.md` H-02). |
| Cliente WhatsApp (envío) | 🔴 **Simulado** | No hace HTTP real; devuelve IDs inventados. Pendiente (H-01). |
| Conciliación de saldo | ⚪ No existe | El módulo ya NO afirma "saldo actualizado"; solo "en verificación". |

> Toda falla, error o cambio queda registrado en [`docs/BITACORA_TECNICA.md`](docs/BITACORA_TECNICA.md).

### 2. Iniciar el Servidor Autónomo (:8025):
Haz doble clic en:
`INICIAR_MODULO_MULTIMODAL.command`
O ejecuta en consola:
```bash
python3 service/server.py --port 8025
```
El servidor quedará disponible en `http://127.0.0.1:8025`.

---

## 🌐 Enlace PWA Universal
Todo despacho saliente generado por este módulo concluye obligatoriamente con el sufijo oficial:
```text
🌐 Portal PWA 4GMAX (Acceso libre por Wi-Fi o Datos Móviles — Cualquier Operadora):
👉 https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html
```
