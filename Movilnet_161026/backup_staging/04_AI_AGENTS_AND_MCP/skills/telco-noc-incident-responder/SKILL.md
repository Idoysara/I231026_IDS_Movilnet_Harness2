---
name: telco-noc-incident-responder
version: 1.0.0
description: Protocolo de respuesta inteligente del NOC para mitigación de averías masivas, avisos proactivos georreferenciados y diagnóstico de radiobases en Movilnet 4GMAX.
category: telco-noc
scope: project
risk: none
license: Apache-2.0
tags: [noc, movilnet, 4gmax, incident-response, radiobase, proactive-bulletins, zero-hallucination]
---

# 📡 Skill: Telco NOC Incident Responder (Operaciones de Red Movilnet)

## 1. Propósito
Habilita al Asistente Inteligente **MOVI** (`+58 424 153 3712`) para interceptar consultas sobre problemas de cobertura, caídas de señal y lentitud de datos, cruzándolas en $<5\text{ ms}$ contra el catálogo de boletines proactivos del NOC (`operaciones_noc.json`).

---

## 2. Protocolo de Triage y Mitigación Proactiva
1. **Extracción Geográfica:** Detectar estado o municipio en el mensaje (ej: Maracaibo, Valencia, Caracas).
2. **Inspección de Boletín Activo:** Consultar `DepartmentRuleEngine` a través de `mcp_noc_get_regional_status`.
3. **Supresión Proactiva de Tickets Falsos:** Si la zona se encuentra en ventana de mantenimiento o modernización 4GMAX:
   - Se emite inmediatamente el mensaje oficial de la cuadrilla con tiempo estimado de normalización (ETA).
   - Se evita la saturación de los canales de atención y la apertura redundante de averías individuales.
4. **Diagnóstico Técnico Individual:** Si la zona reporta estado óptimo (`OPERATIONAL_OPTIMAL`), se verifica la configuración APN (`int.movilnet.com.ve`) o se genera un ticket formal (`#NOC-XXXXXXXX`).
