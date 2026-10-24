---
name: bcv-exchange-sync
version: 1.0.0
description: Motor de sincronización, auditoría y conversión de tasas cambiarias oficiales del Banco Central de Venezuela (BCV) para facturación y tarifas bimonetarias (VES/USD).
category: fintech-billing
scope: global
risk: none
license: MIT
tags: [bcv, exchange-rate, ves-usd, sudeban, billing, tariffs, currency-conversion]
---

# 💱 Skill: BCV Official Exchange Sync & Dual Currency Billing

## 1. Propósito
Garantizar la actualización diaria automática de las tasas de cambio oficiales del **Banco Central de Venezuela (BCV)** para el cálculo de facturas, recargas de saldo y planes bimonetarios en estricto cumplimiento legal.

---

## 2. Reglas de Negocio Cambiario

* **Horario de Sincronización Oficial:** Loop diario ejecutado a las **17:30 (5:30 PM)** tras la publicación del cierre de mesas cambiarias del BCV, con vigencia para el día hábil siguiente.
* **Caché en Redis con TTL Seguro:** La tasa oficial se almacena en `redis:bcv_rate_usd_ves` con TTL de 24 horas y persistencia de respaldo en PostgreSQL.
* **Cero Recargos no Oficiales:** Se prohíbe el uso de marcadores paralelos; todas las conversiones de recargas C2P se calculan al céntimo exacto sobre la tasa oficial.
