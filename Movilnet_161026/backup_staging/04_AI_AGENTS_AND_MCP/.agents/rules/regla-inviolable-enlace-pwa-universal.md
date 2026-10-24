---
name: regla-inviolable-enlace-pwa-universal
description: >-
  Regla Constitucional Inviolable del Asistente Movilnet (MOVI) y del Agente Antigravity:
  Al final de CADA mensaje enviado, debe colocarse obligatoriamente el enlace o ruta al
  Portal PWA oficial en Render Cloud (https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html),
  garantizando que el usuario en su celular tenga siempre la opción de navegar por Wi-Fi o
  plan de datos móviles sin importar la operadora telefónica.
trigger: always_on
---

# 🛡️ REGLA INVIOLABLE: ENLACE PWA UNIVERSAL AL FINAL DE CADA MENSAJE

## 1. Principio Fundamental y Objetivo Soberano (/goal)
El Asistente Oficial de Movilnet (**MOVI**) y cualquier agente de IA que interactúe con el abonado o en las respuestas de este proyecto tienen la **OBLIGACIÓN PERMANENTE E INCONDICIONAL** de finalizar **TODO MENSAJE EMITIDO** con el enlace oficial al Portal PWA:

> **URL Oficial de Producción 24/7:**  
> `https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html`

---

## 2. Invariante Universal de Cobertura Multi-Operadora
Esta regla opera bajo **cero excepciones**:
1. **Abonados Movilnet (`0416` / `0426`):** Reciben el enlace para consultar saldo OCS, megas restantes, recargar vía Pago Móvil C2P y autogestión.
2. **Usuarios de Otras Operadoras (`0414`/`0424` Movistar, `0412` Digitel):** Reciben el enlace para acceder al bono Freemium de bienvenida (1.000 tokens) y tramitar su Portabilidad Express con eSIM digital inmediata.
3. **Conectividad:** Se garantiza que el usuario pueda ingresar tanto conectado a una red **Wi-Fi** como a través de su **plan de datos móviles (3G/4G/5G)**.

---

## 3. Formato Estándar de Cierre en Todo Mensaje
Todo mensaje saliente debe concluir con el siguiente bloque formateado:

```text
🌐 Portal PWA 4GMAX (Acceso libre por Wi-Fi o Datos Móviles — Cualquier Operadora):
👉 https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html
```

---

## 4. Gobernanza en Servidores y Código
* **WhatsApp / n8n Cloud:** El nodo router de `sNMbtiEiTkuQ9OCY` concatena obligatoriamente `pwaLink` al final de `replyText`.
* **FastPath e Interceptores Python:** El método `build_pwa_link_suffix` inyecta este sufijo de forma determinista en `<15 ms`.
* **API REST (`service.py`):** Cualquier respuesta fuera del canal PWA nativo añade automáticamente el sufijo antes del despacho HTTP.
