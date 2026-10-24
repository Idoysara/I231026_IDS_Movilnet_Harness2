---
name: sim-swap-guard
version: 1.0.0
description: Protocolo de prevención de suplantación de identidad mediante SIM Swap (cambio de chip) conforme al estándar internacional GSMA Open Gateway.
category: telco-security
scope: global
risk: none
license: Apache-2.0
tags: [gsma, sim-swap, identity-verification, conatel, anti-phishing, usim-security]
---

# 🔒 Skill: SIM Swap Guard & GSMA Open Gateway Security

## 1. Propósito
Detectar si la tarjeta USIM asociada a una línea `0416`/`0426` fue reemplazada recientemente (últimas 24-48 horas) antes de autorizar transacciones financieras críticas o cambios de clave.

---

## 2. Protocolo de Verificación GSMA SIM Swap

1. **Consulta de Marca Temporal IMSI:** El sistema verifica la fecha y hora del último aprovisionamiento de la tarjeta USIM en el HLR/HSS de Movilnet.
2. **Ventana de Cuarentena (48 Horas):** Si la línea sufrió reposición de chip en las últimas 48 horas:
   - Se bloquean las transacciones bancarias salientes por Pago Móvil C2P.
   - Se exige doble factor de autenticación presencial o biometría KYC antes de resetear credenciales.
3. **Notificación Out-of-Band:** Envío de alerta preventiva por SMS y correo alternativo al titular legítimo.
