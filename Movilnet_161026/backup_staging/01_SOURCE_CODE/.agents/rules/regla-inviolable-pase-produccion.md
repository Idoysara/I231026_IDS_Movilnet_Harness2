# 🛑 Regla Inviolable de Blindaje: Prohibición Absoluta de Despliegue a Producción sin Instrucción Directa y Respaldo Previo

Esta directiva es de cumplimiento obligatorio, estricto e incondicional para todo agente de Antigravity en este proyecto. Rige cada commit, sincronización, push, comando y cambio de rama.

---

## 🔒 1. Principio Fundamental de Aislamiento de Entorno
1. **Entorno de Trabajo Activo:** Todo el desarrollo, refactorización, pruebas y actualizaciones cotidianas deben realizarse **exclusivamente en la rama `develop`** y en el entorno local (puerto dedicado `8010`).
2. **Ambiente de Producción Blindado:** La producción en Render Cloud (`https://movilnet-core.onrender.com`) está vinculada a la rama `main` en GitHub. Por diseño, mientras el agente opere en `develop`, la producción está físicamente desacoplada y protegida contra cualquier cambio accidental.
3. **Recordatorio Mandatario:** Siempre que el agente inicie una sesión o responda al usuario, debe tener presente y recordar explícitamente que estamos operando en el ambiente de desarrollo seguro (`develop`), sin tocar la producción.

---

## 🚫 2. Prohibición Absoluta de Pase a Producción Autónomo
* **Queda estrictamente prohibido:**
  - Ejecutar `git checkout main`, `git merge develop` o `git push origin main` de forma autónoma.
  - Ejecutar scripts de despliegue a producción (`ACTUALIZAR_RENDER_1CLIC.command`, `DESPLEGAR_A_LA_NUBE.command`, `SUBIR_A_GITHUB.command` sobre `main`) sin la instrucción humana directa.
  - Cualquier acción que altere la rama `main` sin cumplir con el protocolo de pase a producción.

---

## 📋 3. Protocolo Mandatario para Pase a Producción
Para que un pase a producción sea legalmente ejecutable, deben cumplirse **sin excepción** los siguientes cuatro requisitos secuenciales:

### Requisito 1: Instrucción Directa, Específica y Explícita del Usuario
El usuario debe ordenar de forma inequívoca el pase a producción (ejemplo: *"autorizo pasar a producción"*, *"ejecuta el pase a producción con respaldo previo"*). Ninguna inferencia o suposición permite asumir esta orden.

### Requisito 2: Creación Previa de Copia con Respaldo Completo Sellado
Antes de tocar `main`, el agente debe crear una copia íntegra y ordenada de todo el proyecto en la carpeta de respaldos correspondiente (ej: `Desktop/121026_CORE_MOVILNET/Movilnet_DDMMAA/...`), verificando:
- Inclusión de todos los componentes, base de datos SQLite y flujos n8n.
- Generación del manifiesto criptográfico SHA-256 maestro (`MANIFESTO_SHA256_RESPALDO_*.json`).
- Verificación de autonomía de ejecución de la copia.

### Requisito 3: Certificación 100% PASS de Calidad y Cero Alucinación
- `pytest tests/`: **100% de pruebas aprobadas (0 fallos)**.
- `scripts/audit_docs_evidence.py --audit`: **Hallazgos: 0**.
- `scripts/verify_zero_hallucination_compliance.py --audit`: **0 alucinaciones**.
- `scripts/quality_gatekeeper_10phases.py --audit`: **10/10 Fases Aprobadas**.

### Requisito 4: Despliegue Transparente y Registro en Bitácora
Una vez cumplidos los requisitos 1, 2 y 3:
1. Merge controlado a `main`: `git checkout main && git merge develop && git push origin main`.
2. Verificación de telemetría en Render Cloud (`/health`).
3. Retorno inmediato a la rama `develop`: `git checkout develop`.
4. Registro del pase a producción en `docs/BITACORA_MOVILNET.md` con su hash de commit y hash del respaldo.
