---
name: telco-network-diagnostic
version: 1.0.0
description: Protocolo de diagnóstico de radiobases, calidad de señal 4GMAX, detección de congestión en celdas y reporte de fallas OSS para abonados de telecomunicaciones.
category: telco-oss
scope: global
risk: none
license: Apache-2.0
tags: [telco, oss, 4gmax, movilnet, signal-diagnostic, radiobase, conatel, cellsite]
---

# 📡 Skill: Telco Network Diagnostic & Radiobase Health (OSS)

## 1. Propósito
Habilita a los agentes y subagentes de **Antigravity** para realizar diagnósticos automatizados sobre el estado de la red móvil (cobertura 4GMAX, radiobases activas, nivel de señal RSRP/RSRQ y cortes zonales de energía eléctrica).

---

## 2. Parámetros Clave de Diagnóstico Móvil

| Métrica | Rango Óptimo | Rango Crítico | Acción Automatizada |
|:---|:---|:---|:---|
| **RSRP (Potencia Señal)** | > -85 dBm | < -115 dBm | Sugerir reinicio de datos o cambio a 3G/GSM |
| **RSRQ (Calidad de Señal)**| > -10 dB | < -19 dB | Reportar interferencia zonal a Ingeniería OSS |
| **Estado Celda (CellSite)**| Activa / 100% | Degradada / Outage | Informar al abonado sobre labores técnicas en curso |

---

## 3. Protocolo de Atención al Abonado
1. **Identificación de Coordenadas o Zona:** Extraer parroquia/municipio del mensaje del usuario (ej: *"No tengo señal en La Candelaria"*).
2. **Consulta a Servidor MCP OSS:** Invocar herramienta de verificación de radiobases activas.
3. **Respuesta Empática y Humana:** Si hay una falla masiva o corte eléctrico, informar el tiempo estimado de restablecimiento (ETA) sin tecnicismos innecesarios.
