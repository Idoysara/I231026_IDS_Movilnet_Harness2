---
name: c2p-fraud-detector
version: 1.0.0
description: Motor de análisis heurístico y prevención de fraude para transacciones de Pago Móvil C2P (Comercio a Persona) bajo normativa SUDEBAN.
category: fintech-security
scope: global
risk: none
license: Apache-2.0
tags: [fintech, c2p, pago-movil, fraud-detection, sudeban, bdv, otp-validation]
---

# 💳 Skill: C2P Fraud Detector & Heuristic Security (SUDEBAN)

## 1. Propósito
Proteger a los abonados y a la operadora contra transacciones fraudulentas de débito en cuenta (Pago Móvil C2P) mediante reglas de validación en tiempo real antes de invocar la pasarela bancaria.

---

## 2. Reglas de Validación Antifraude

1. **Límite de Intentos OTP:** Máximo **3 intentos fallidos de clave dinámica (token OTP)** en una ventana de 15 minutos. Al 3er fallo, se bloquea la operación por 1 hora.
2. **Coincidencia de Titularidad:** La cédula del pagador debe coincidir con el titular del contrato o estar explícitamente autorizada en la sesión conversacional.
3. **Control de Velocidad (Velocity Check):** Rechazar recargas idénticas en intervalos menores a 60 segundos (prevención de doble cobro accidental por latencia).
4. **Montos Máximos:** Validación contra los límites diarios oficiales en Bolívares (VES) dictados por la Superintendencia de las Instituciones del Sector Bancario (**SUDEBAN**).
