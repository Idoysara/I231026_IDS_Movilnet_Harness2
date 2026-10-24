---
name: agy-telemetry-dual-sync-guardian
description: Guardián de Resiliencia de Red, Contexto SSL y Fusión Dual Simétrica de Telemetría (Local ↔ Cloud ↔ Frontend). Previene excepciones silenciosas de SSL/timeout en Python, condicionales asimétricos rotos en JavaScript y fugas de números legacy prohibidos.
---

# 🛡️ agy-telemetry-dual-sync-guardian

## Propósito
Este skill protege de forma autónoma y permanente la infraestructura de telemetría y sincronización conversacional del Asistente Virtual Movilnet Core. Intercepta, audita y previene los dos patrones de fallo identificados en el análisis forense RCA:
1. **Fallo de Contexto SSL y Timeouts Restrictivos en Python:** Llamadas de red con `urllib.request.urlopen` sin contexto SSL tolerante o con timeouts inferiores a 5s, así como bloques `except Exception: return 0` que ocultan la causa raíz.
2. **Condicionales Asimétricos y Fallbacks Rotos en Frontend:** Guardas JavaScript como `if (!responseOk && !isLocal)` que impiden a `localhost` consultar o fusionar los eventos en vivo de la nube.
3. **Fugas de Números Prohibidos:** Intentos de interacción del número legacy `0416-6251587`.

---

## Modos de Operación

### 1. Auditoría Estática de Resiliencia (AST + Regex)
Ejecutar el script verificador incluido para auditar todos los adaptadores de red y vistas del proyecto:
```bash
python3 backup_staging/01_SOURCE_CODE/scripts/audit_telemetry_resilience.py --audit
```
* Examina el árbol sintáctico (AST) de todos los archivos Python en `core/` y `api/`.
* Comprueba que toda llamada a `urlopen` pase un objeto `ssl` válido y `timeout >= 5.0`.
* Inspecciona los archivos HTML/JS en `ui/` asegurando que no existan guardas que excluyan a `localhost` de la sincronización cloud.

### 2. Auto-Verificación y Certificación (100% Pass)
```bash
python3 backup_staging/01_SOURCE_CODE/scripts/audit_telemetry_resilience.py --test
```
* Ejecuta aserciones formales sobre:
  1. `TraceCloudSyncAdapter.sync_with_cloud_render()` con contexto SSL y timeout de 10s.
  2. Adopción transparente de telemetría online de Render Cloud.
  3. Fusión bidireccional en `conversatorio.html`.
  4. Descarte perimetral inmediato del número `0416-6251587` en `WebhookNoiseFilter`.

---

## Reglas de Implementación Obligatorias

### Regla 1: Protocolo de Red Python Resiliente
Toda llamada de red hacia Render Cloud, n8n Cloud o APIs externas debe respetar este molde:
```python
import ssl
import urllib.request
import json

ctx = ssl._create_unverified_context()
req = urllib.request.Request(
    target_url,
    headers={"Accept": "application/json", "User-Agent": "MovilnetCore-Adapter/1.0"}
)
with urllib.request.urlopen(req, timeout=10.0, context=ctx) as resp:
    data = json.loads(resp.read().decode("utf-8"))
```

### Regla 2: Fusión Dual Simétrica en Frontend
Todo panel o conversatorio debe consultar en paralelo la fuente local y la nube:
```javascript
// 1. Consulta Local
const localRes = await fetch('/api/v1/monitor/conversations?t=' + ts);
// 2. Consulta Cloud (Siempre, sin excluir localhost)
const cloudRes = await fetch('https://one21026-ids-movilnet-pwa.onrender.com/api/v1/monitor/conversations?t=' + ts);
// 3. Fusión determinista por ID único de mensaje
localData.grouped_threads = mergeThreadsWithSeeds(localThreads, cloudThreads);
```
