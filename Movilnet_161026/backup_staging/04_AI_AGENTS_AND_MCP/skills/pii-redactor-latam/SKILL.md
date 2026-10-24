---
name: pii-redactor-latam
version: 1.0.0
description: Filtro de seguridad perimetral para anonimización, enmascaramiento y redaction de PII para Venezuela y LATAM (Cédula, RIF, USIM).
category: security-privacy
scope: global
risk: none
license: Apache-2.0
tags: [pii, redaction, masking, privacy, conatel, gdpr, cedula-venezuela, zero-trust]
---

# 🛡️ Skill: PII Redactor LATAM & Data Privacy (CONATEL)

## 1. Propósito
Aislar y enmascarar información personalmente identificable (PII) antes de ser enviada a cualquier modelo de lenguaje o servicio externo, garantizando el cumplimiento de la Ley de Telecomunicaciones y regulaciones de CONATEL.

---

## 2. Patrones de Expresiones Regulares para Venezuela

| Dato Sensible | Patrón Regex | Formato Enmascarado |
|:---|:---|:---|
| **Cédula de Identidad** | `r'(?i)\b([VEJPG])-?(\d{1,2})\.?(\d{3})\.?(\d{3})\b'` | `V-***.***.123` |
| **Teléfono Móvil** | `r'\b(0416|0426|0414|0424|0412)[0-9]{7}\b'` | `0416-***-4567` |
| **Serial USIM 4GMAX** | `r'\b8958\d{15,16}\b'` | `8958************` |
| **Token Bancario OTP** | `r'\b\d{6,8}\b'` | `[REDACTED_OTP]` (Cero persistencia en logs) |

---

## 3. Política de Logs y Auditoría
Los tokens OTP dinámicos y contraseñas jamás deben escribirse en archivos de logs de texto claro ni transmitirse en URLs GET.
