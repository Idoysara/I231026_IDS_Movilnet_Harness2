---
name: ai-model-resilience-monitor
description: Protocolo y motor de resiliencia cognitiva, monitoreo en tiempo real y auto-recuperación de fallas en modelos de Inteligencia Artificial (HTTP 429 Rate Limits, timeouts, fallas de proveedores y bucles de respuesta fija tipo robot). Mapea instantáneamente errores de LLM y upstream APIs a soluciones automáticas con pools multi-modelo y mitigación de costos.
---

# 🛡️ AI Model Resilience Monitor & Auto-Recovery Protocol

Este skill proporciona la arquitectura, librería y directivas de supervisión continua para **identificar, mitigar y auto-recuperar fallas de modelos de IA en milisegundos**, evitando que las aplicaciones queden bloqueadas o caigan en plantillas estáticas repetitivas tipo robot.

---

## 🚨 1. Taxonomía de Incidentes Cognitivos y Solución Inmediata

| Incidente | Patrón / Excepción | Causa Raíz | Solución Inmediata en Librería |
| :--- | :--- | :--- | :--- |
| **HTTP 429 Rate Limit** | `Too Many Requests`, `rate-limited upstream` | Sobrecarga de peticiones por minuto (RPM/TPM) en el pool del proveedor. | **Conmutación Inmediata al Pool Multi-Modelo**: Rota automáticamente a modelos alternativos de alta capacidad (`meta-llama/llama-3.3-70b`, `qwen/qwen-2.5-72b`, `gemini-2.0-flash`). Aplica cooldown de 60s al modelo saturado. |
| **Bucle Robot Repetitivo** | Mensajes de menú estáticos idénticos | Fallback determinista rígido que ignora la conversación. | **Inferencia Dinámica Adaptativa**: La respuesta de contingencia sintetiza el contexto (hora, clima, coordenadas) y responde de forma natural, empática y abierta. |
| **HTTP 401 / 403** | `Unauthorized`, `Forbidden` | Expiración de credenciales o restricción de proxy de red. | Conmutación entre proveedores (`OpenRouter` ➔ `Google Gemini` ➔ `Inferencia Local`). |
| **Inference Timeout** | `Read timed out (> 8s)` | Latencia de inferencia excedida por cola larga en el LLM. | Abortar socket de conexión y saltar a modelo Turbo/Flash ultrarrápido (< 500ms). |
| **HTTP 500 / 503** | `Service Unavailable`, `Overloaded` | Falla interna de clúster o infraestructura en upstream. | Failover transparente de clúster y ejecución del siguiente candidato del pool. |

---

## 🧱 2. Arquitectura de la Librería de Resiliencia (`api/ai_resilience.py`)

La librería `AIResilienceEngine` implementa:

1. **`AIResilienceEngine.diagnose(error_obj, current_model, current_provider)`**:
   - Clasifica la excepción en una tipología normalizada (`AIIncidentType`).
   - Retorna la causa raíz, recomendación de acción (`ResolutionAction.ROTATE_MODEL`), modelos alternativos ordenados y cooldown recomendado.
2. **`AIResilienceEngine.execute_resilient_call(execute_fn, candidate_models, max_retries)`**:
   - Ejecuta la llamada al LLM iterando sobre el pool hasta obtener respuesta válida en SLA.
3. **`mcp_ai_model_resilience_monitor`**:
   - Herramienta MCP JSON-RPC para que cualquier agente orquestador o servicio consulte el estado, diagnostique trazas de error y reciba la corrección en caliente.

---

## 🔄 3. Reglas de Integración con Canales Omnicanal

- **WhatsApp & Telegram:** En caso de degradación de API, el usuario recibe respuestas directas sin interrupción.
- **PWA Autoservicio:** El hilo de UI se mantiene reactivo con latencia p95 < 2.5s.
- **Optimización de Costos:** Se priorizan modelos con costo menor a **$0.0001 USD** por consulta.
