---
name: protocolo-decagonal-garantia-calidad
description: >-
  Protocolo Maestro Decagonal de Garantía de Calidad y Cero Errores en Chat.
  Gobierna las 10 etapas de ingeniería (Analítica, Propuestas, Diseño, Consultas,
  Desarrollo, Pruebas, Verificación, Ajustes, Comprobación, Auditoría y Certificación)
  e intercepta constructivamente cualquier error o asunción en el diálogo.
trigger: always_on
---

# 🛡️ Protocolo Maestro Decagonal: Garantía de Verdad y Cero Errores (10 Fases)

Este protocolo es de cumplimiento obligatorio e incondicional para todo agente de Antigravity en este proyecto. Rige cada interacción, diagnóstico, propuesta, línea de código y reporte en el chat.

---

## 🚨 Principio Cero: Intercepción Constructiva de Errores en el Chat (Doble Chequeo Inflexible)
1. **Nunca asumir afirmaciones del chat como verdad física absoluta**:
   Si el usuario o un mensaje previo afirma una premisa (ejemplo: *"el puerto 8000 está libre"*, *"el número del cliente es X"*, *"la API está respondiendo en 2ms"*), el agente **no debe operar a ciegas sobre esa asunción**.
2. **Validación Previa con Telemetría Dura**:
   Antes de proceder, el agente ejecuta una comprobación contra la fuente real (`lsof`, consultas SQL, `grep`, endpoints REST).
3. **Manejo de Errores del Usuario (Intercepción con Evidencia)**:
   Si se detecta que la premisa del usuario contiene un error o discrepancia con el sistema:
   - **No complacer pasivamente ("sycophancy")**: Prohibido decir *"De acuerdo"* y aplicar un cambio que romperá el entorno.
   - **Presentar la evidencia con respeto y claridad**: Señalar la discrepancia técnica concreta, mostrar la evidencia observada (ej: *"Al verificar con `lsof -i :8000`, detecté que el puerto está ocupado por Docker `dss_gps_backend`..."*) y ofrecer la solución segura ya homologada.

---

## 🏛️ La Matriz de las 10 Fases de Ingeniería

### 1. Analítica (Comprensión y Diagnóstico de Contexto)
* **Regla:** Cero especulación. Diagnosticar inspeccionando archivos reales, bases de datos y procesos activos.
* **Guardarraíl:** Comprobar existencia física de archivos y esquemas antes de diagnosticarlos.

### 2. Propuestas (Recomendaciones y Estrategias)
* **Regla:** Toda propuesta técnica debe fundamentarse en trade-offs reales (latencia, tokens, impacto en arquitectura).
* **Guardarraíl:** Citar mediciones registradas con SHA-256 (`reports/fastpath_latency_report.json`) en lugar de estimaciones inventadas.

### 3. Diseño (Arquitectura y Modelado)
* **Regla:** Seguir Arquitectura Limpia (Hexagonal), contratos OpenAPI TM Forum ODA y principio Zero-PII.
* **Guardarraíl:** Prohibido guardar datos personales o secretos en texto plano; usar blind index HMAC-SHA256.

### 4. Consultas (Recopilación de Evidencia y Datos)
* **Regla:** Jerarquía de evidencia matemática:
  1º Base de Datos relacional / API REST autenticada.
  2º JSON exportado de producción (`pinData`).
  3º Captura de pantalla nítida en alta resolución.
  Prohibido usar OCR sobre tipografía diminuta (<14px) o borrosa.

### 5. Desarrollo (Programación y Construcción)
* **Regla:** Modularidad y scripts independientes. Todo nuevo script debe residir en `scripts/` o `api/` con tipado estricto (`typing`, `dataclasses`, `Pydantic`) y bloque `if __name__ == "__main__":` con CLI (`--test`, `--demo`). Prohibido espagueti monolítico.

### 6. Pruebas (Testing Automatizado Integral)
* **Regla del 100% Pass (0 fallos):** Ninguna tarea se da por concluida si `pytest tests/` no aprueba el 100% de las pruebas sin errores.

### 7. Verificación (Análisis Estático y Tipado)
* **Regla:** Todo código debe compilar limpiamente bajo análisis sintáctico AST (`ast.parse()`). Cero errores sintácticos o excepciones no controladas.

### 8. Ajustes (Refactorización y Corrección de Errores)
* **Regla:** Ediciones quirúrgicas mediante diffs exactos. Prohibido reemplazar archivos completos cuando solo se requiere un ajuste de líneas. Tras cada ajuste, re-ejecutar pruebas inmediatamente.

### 9. Comprobación (Ejecución E2E y Aislamiento de Entorno)
* **Regla:** Verificar aislamiento estricto de puertos (`agy-port-guardian`). Movilnet Core opera exclusivamente en el puerto dedicado `8010` para garantizar coexistencia con otros contenedores.

### 10. Auditoría y Certificación (Sellado Criptográfico Final)
* **Regla:** Toda entrega se audita con `scripts/audit_docs_evidence.py --audit` y `scripts/quality_gatekeeper_10phases.py --audit`. Los artefactos finales deben sellarse con hashes SHA-256 e incluir manuales de usuario de doble clic (Pilar VII: Cero Terminal).
