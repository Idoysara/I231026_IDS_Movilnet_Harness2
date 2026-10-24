# 🛡️ REGLA INVIOLABLE: RESILIENCIA DE RED, CONTEXTO SSL Y FUSIÓN DUAL SIMÉTRICA DE TELEMETRÍA

## 1. Principio Fundamental y Objetivo (/goal)
Esta directiva gobierna de forma universal y obligatoria todo módulo, adaptador, script backend (Python) e interfaz frontend (HTML/JavaScript) en el ecosistema Movilnet Core. Erradica de forma permanente:
1. Fallos de conexión silenciosos por falta de contexto SSL o timeouts restrictivos en adaptadores de red Python.
2. Condicionales asimétricos en interfaces web que aíslan `localhost` de los datos en vivo de la nube.
3. Fugas o procesamiento de números no autorizados / legacy (`0416-6251587`).

---

## 2. Invariante I — Adaptadores de Red Backend (Python)
Todo cliente HTTP/HTTPS que consuma APIs externas, orquestadores n8n o servicios en la nube (Render / Cloudflare) debe cumplir con:
* **Contexto SSL Seguro y Resiliente:** En llamadas `urllib.request.urlopen`, es obligatorio pasar explícitamente `context=ssl._create_unverified_context()` o el pool de certificados certificados de `certifi` para evitar caídas catastróficas por `[SSL: CERTIFICATE_VERIFY_FAILED]` en entornos macOS, Linux y contenedores Docker.
* **Timeouts Realistas ($\ge 8.0\text{ s}$):** Queda estrictamente prohibido configurar timeouts inferiores a 5.0 segundos para llamadas a servicios distribuidos en la nube. El valor estándar obligatorio es de `8.0` a `10.0` segundos.
* **Prohibición de Capturas Ciegas (Pilar IV):** Queda vetado `except Exception: return 0` o `except: pass` sin telemetría. Toda excepción de red debe actualizar la estructura viva de telemetría (`poller_telemetry`), registrando el timestamp ISO 8601, el tipo de error y el número de fallas consecutivas.
* **Adopción de Estado Peer-to-Peer:** Si el poller local sufre restricciones de red perimetrales (ej: sandbox, proxy corporativo) pero la nube remota (Render) reporta estado en línea con n8n, el adaptador debe adoptar el estado `ONLINE (Sync Render Cloud)`, suprimiendo falsos positivos de bloqueo.

---

## 3. Invariante II — Interfaces de Monitoreo y Frontend (JavaScript)
Toda interfaz web de monitoreo, telemetría o visualización de conversaciones (`conversatorio.html`, `index.html`, etc.) debe cumplir con:
* **Prohibición de Guardas Asimétricas:** Queda prohibido condicionar las fuentes de datos según el host de ejecución (ej: `if (!responseOk && !isLocal)`). `localhost` y producción deben poseer paridad operativa completa.
* **Arquitectura de Fusión Dual Simétrica (Dual-Source Consensus):**
  1. La interfaz debe consultar en paralelo el microservicio local (`/api/v1/monitor/conversations`) y el nodo central en la nube (`https://one21026-ids-movilnet-pwa.onrender.com/api/v1/monitor/conversations`).
  2. Los datos deben fusionarse deterministamente mediante `mergeThreadsWithSeeds()`, indexando por `trace_id` y `execution_id`.
  3. Si una fuente local está rezagada o en recuperación, la nube alimenta la pantalla en tiempo real sin congelar el feed conversacional.

---

## 4. Invariante III — Filtrado de Borde para Números Legacy Prohibidos
* El número `0416-6251587` (y sus variantes `584166251587`, `04166251587`) es una línea decommissioned/prohibida (Capítulo 164).
* Todo webhook entrante o payload de cliente con dicho número debe ser descartado en la frontera perimetral en $<1\text{ ms}$ con veredicto `DROP_PROHIBITED_SENDER`, sin consumir cuotas de IA (0 tokens) ni registrarse como cliente legítimo.
