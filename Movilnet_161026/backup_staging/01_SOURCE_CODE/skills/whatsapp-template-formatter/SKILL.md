---
name: whatsapp-template-formatter
version: 1.0.0
description: Formateador inteligente de respuestas para WhatsApp Meta Cloud API con soporte de mensajes interactivos, botones rápidos y listas.
category: messaging
scope: global
risk: none
license: MIT
tags: [whatsapp, meta-cloud-api, templates, interactive-messages, n8n-whatsapp]
---

# 📱 Skill: WhatsApp Template Formatter & Interactive UX

## 1. Propósito
Garantizar que todas las respuestas generadas por los modelos de IA se adapten estrictamente a los límites y capacidades interactivas de la **Meta WhatsApp Cloud API**.

---

## 2. Restricciones y Reglas de Formateo

* **Límite de Longitud:** Respuestas de texto no deben superar los **4.096 caracteres** (recomendado máximo 300 palabras para legibilidad móvil).
* **Botones Rápidos (Quick Reply Buttons):** Máximo **3 botones por mensaje** con títulos de hasta **20 caracteres** (ej: `[ Consultar Saldo ]`, `[ Recargar C2P ]`, `[ Ver Planes ]`).
* **Listas Desplegables (Interactive Lists):** Hasta **10 opciones** organizadas por secciones con títulos de hasta 24 caracteres.
* **Formateo Tipográfico:** Uso correcto de `*negritas*`, `_cursivas_` y `~tachados~`.
