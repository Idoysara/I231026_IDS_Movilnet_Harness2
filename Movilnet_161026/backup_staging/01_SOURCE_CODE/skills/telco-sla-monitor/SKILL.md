---
name: telco-sla-monitor
version: 1.0.0
description: Centinela de observabilidad y monitoreo de Acuerdos de Nivel de Servicio (SLA) para respuestas telco en tiempo real.
category: observability-sre
scope: global
risk: none
license: MIT
tags: [sla, monitoring, prometheus, latency, telco-sre, fast-path, circuit-breaker]
---

# 📊 Skill: Telco SLA Monitor & Latency Guardian

## 1. Propósito
Monitorear activamente las métricas de rendimiento y tiempos de respuesta de cada petición entrante, alertando si el 70% Fast-Path excede los 25ms o si la inferencia de IA excede los 2 segundos.

---

## 2. Umbrales de SLA Establecidos para Movilnet IA

| Ruta de Ejecución | Latencia Esperada | Umbral de Alerta (Warning) | Acción de Mitigación |
|:---|:---|:---|:---|
| **Fast-Path (Redis Cache)** | **< 25 ms** | > 100 ms | Purgar memoria y reindexar claves Redis |
| **Consulta SQL (PostgreSQL)** | **< 15 ms** | > 200 ms | Optimizar índices particionados `0416`/`0426` |
| **Inferencia LLM (Model Gateway)** | **< 1.8 s** | > 4.0 s | Conmutar al modelo de fallback de menor latencia (Groq / Gemini Flash) |
| **Switch Bancario (Pago Móvil C2P)**| **< 3.5 s** | > 8.0 s | Reintento automático con backoff exponencial |
