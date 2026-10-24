# 🛡️ Regla de Proyecto: Guardarraíl Anti-Propaganda y Descarte de Auto-Respondedores Comerciales

Esta directiva es de cumplimiento obligatorio, incondicional e inviolable en todo el ecosistema de Movilnet Core, PWA, orquestación n8n Cloud y pasarelas de mensajería (Evolution API / Baileys).

---

## 🏛️ 1. Principio Fundamental: Protección de Recursos de IA en la Frontera (Edge Shielding)

Los modelos de Inteligencia Artificial (Google Gemini Flash / LangChain) y los motores de ejecución de n8n Cloud operan bajo cuotas de peticiones y límites de concurrencia.
Queda **terminantemente prohibido** despachar hacia los flujos de n8n Cloud o invocar modelos LLM con:
1. **Auto-respuestas comerciales de WhatsApp Business:** Mensajes automáticos de bienvenida, ausencia o confirmación emitidos por empresas o cuentas comerciales (ej: *"Gracias por comunicarte con [Comercio]..."*, *"En breve atenderemos su solicitud"*).
2. **Difusiones masivas o convocatorias no solicitadas (Spam/Propaganda):** Invitaciones a meetups, eventos externos, registros en Luma, hackathons, talleres gratuitos o publicidad no relacionada con telecomunicaciones de Movilnet.
3. **Avisos automáticos de cifrado y seguridad:** Mensajes de WhatsApp como *"Los mensajes y llamadas están cifrados de extremo a extremo"*.

---

## 🚫 2. Taxonomía de Mensajes Sujetos a Descarte Inmediato

Cualquier mensaje que contenga los siguientes patrones léxicos debe ser clasificado y frenado en la frontera (<1ms):

| Categoría | Patrones Léxicos Típicos | Acción Requerida | Veredicto del Filtro |
| :--- | :--- | :--- | :--- |
| **Auto-Respondedor Comercial WhatsApp Business** | `gracias por comunicarte con`, `gracias por escribirnos`, `en breve atenderemos su solicitud`, `un asesor te atenderá`, `bienvenido a nuestro canal`, `horario de atención`, `mensaje automático`, `auto-respuesta` | **Descarte Inmediato (0ms)**<br>Cero despacho a n8n<br>0 tokens LLM | `FilterVerdict.DROP_COMMERCIAL_AUTOREPLY` |
| **Spam / Difusión / Propaganda Externa** | `meetup`, `conferencia`, `entrada libre`, `te invitamos a`, `luma.com`, `registro en luma`, `patrocinado por`, `comunidad tech`, `hackathon`, `after office` | **Descarte Inmediato (0ms)**<br>Cero despacho a n8n<br>0 tokens LLM | `FilterVerdict.DROP_SPAM_INVITATION` |
| **Avisos Técnicos de WhatsApp** | `mensajes y llamadas están cifrados`, `código de seguridad cambió`, `end-to-end encrypted`, `esperando el mensaje` | **Descarte Inmediato (0ms)** | `FilterVerdict.DROP_SYSTEM_SECURITY_NOTICE` |
| **Ecos del Propio Bot** | `fromMe == true`, `send.message` emitido por el daemon Baileys | **Descarte Inmediato (0ms)** | `FilterVerdict.DROP_FROM_ME_ECHO` |

---

## ⚙️ 3. Puntos de Control y Bloqueo Mandatorios

1. **Control Perimetral en `core/webhook_noise_filter.py`:**  
   Todo payload recibido por webhooks entrantes de WhatsApp debe evaluarse contra `COMMERCIAL_AUTOREPLY_REGEX` y `SPAM_INVITATION_REGEX`. Si el veredicto es de descarte, `should_process` retorna `False`.
2. **Control Pre-Despacho en `api/service.py`:**  
   Antes de que cualquier hilo en background intente enviar un paquete a n8n Cloud (`_dispatch_to_n8n`), debe pasar por el guardarraíl. Si el mensaje es propaganda o auto-respuesta comercial, **el hilo aborta el envío**.
3. **Aislamiento de Workflow en n8n Cloud:**  
   El único webhook permitido en producción es `/webhook/messages_upsert4` (`sNMbtiEiTkuQ9OCY`). El flujo obsoleto `WdWU8G9EggQDMack` queda formalmente retirado de la ingesta para impedir bucles con auto-respondedores externos.

---

## 🧪 4. Métrica de Cumplimiento

* **Latencia de descarte:** $\le 1.0 \text{ ms}$ (en memoria volátil, regex precompilado).
* **Consumo de tokens:** Exactamente **0 tokens** de Gemini / LLM.
* **Tasa de error 503 por propaganda:** **0%**.
