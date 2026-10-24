---
name: telco-churn-predictor
version: 1.0.0
description: Modelo analítico y heurístico para predicción temprana de deserción de abonados (Churn Rate), detección de insatisfacción y ofertas proactivas de retención.
category: telco-analytics
scope: global
risk: none
license: Apache-2.0
tags: [telco, churn-prediction, retention, nps, loyalty, movilnet, customer-experience]
---

# 📉 Skill: Telco Churn Predictor & Retention Engine

## 1. Propósito
Monitorear patrones de comportamiento del abonado en tiempo real (mora en recargas, degradación de datos consumidos, reclamos reiterados) para predecir riesgo de abandono y activar promociones de retención personalizadas.

---

## 2. Indicadores de Riesgo de Deserción (Señales de Alerta)

| Indicador | Patrón Crítico | Nivel de Riesgo | Acción Proactiva de Movilnet IA |
|:---|:---|:---:|:---|
| **Frecuencia de Recargas** | Pasó de recargar cada 15 días a >45 días sin saldo | 🔴 Alto | Ofrecer bono de megas extra en la próxima recarga C2P |
| **Reclamos de Cobertura** | >2 reportes de señal en menos de 7 días | 🔴 Alto | Priorizar atención técnica e indemnizar con bolsa de datos |
| **Consumo de Datos** | Caída >60% en megas consumidos mes a mes | 🟡 Medio | Sugerir cambio a un plan más económico (ej: Inteliplan 2.1GB) |
| **Preguntas sobre SIM Swap**| Pregunta cómo migrar su línea o liberar equipo | 🔴 Crítico | Derivar a un operador sénior con oferta de fidelización |
