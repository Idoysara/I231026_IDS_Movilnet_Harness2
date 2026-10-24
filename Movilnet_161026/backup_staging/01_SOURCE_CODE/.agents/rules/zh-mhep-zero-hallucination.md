---
name: zh-mhep-zero-hallucination
description: >-
  Regla de Evidencia Dura y Tolerancia Cero a la Alucinación (ZH-MHEP) del
  proyecto Movilnet. Toda cifra, número telefónico, nombre, hora o resultado
  debe provenir de una fuente verificable.
trigger: always_on
---

# ZH-MHEP — Evidencia Dura (resumen operativo, siempre activo)

Texto completo: `AI_Movilnet_300926-main/rules/zero_hallucination_hard_evidence_rule.md`

## Antes de afirmar o documentar
1. **Prohibido inferir** teléfonos, nombres, saldos, latencias, horas o resultados. Si no hay fuente, escribir "no medido" / "no registrado" o preguntar.
2. **Jerarquía de evidencia:** API REST / JSON exportado / SQLite > captura nítida > plantillas o memoria. Nunca usar OCR sobre texto pequeño o borroso.
3. **Métricas:** toda latencia o costo se obtiene ejecutando `scripts/measure_fastpath_latency.py --out reports/fastpath_latency_report.json` y se cita con su SHA-256. No se redondean ni se estiman "representativas".
4. **Alcance:** declarar qué se midió y qué no (por ejemplo, "en proceso, sin red").
5. **Datos sintéticos:** siempre etiquetados como tales.

## Al terminar cualquier tarea que toque docs o bitácora
Ejecutar, y no dar por cerrada la tarea si falla:
```
cd AI_Movilnet_300926-main
./venv/bin/python scripts/audit_docs_evidence.py --audit          # debe imprimir "Hallazgos: 0"
./venv/bin/python scripts/verify_zero_hallucination_compliance.py --audit
./venv/bin/pytest tests/                                          # 100% pass
```

## Incidentes de referencia
- INC-2026-10-05-01: OCR erróneo de un número (docs/REGISTRO_FORENSE_ALUCINACIONES.md).
- 2026-10-07: latencias y resultados no medidos en el Capítulo 114, y un número de abonado inexistente en la Fase 5; corregidos (Capítulo 115).
