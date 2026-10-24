#!/usr/bin/env python3
"""
scripts/update_n8n_greeting_and_funnel.py
=========================================
Actualiza en vivo el workflow canónico sNMbtiEiTkuQ9OCY en n8n Cloud:
1. En 'AI Agent':
   - Inyecta dinámicamente en el prompt del usuario (parameters.text):
     * Perfil del usuario, número y operadora detectada.
     * MODO OPERATIVO OBLIGATORIO:
       - 'ABONADO_MOVILNET_ACTIVO' (si es 0416 o 0426).
       - 'MODO_CAPTACION_FUNNEL_MARKETING_NO_MOVILNET' (si es 0414, 0424, 0412 u otro).
   - Inyecta en el 'systemMessage':
     * REGLA SOBERANA INVIOLABLE: PROHIBIDO TERMINANTEMENTE decir 'con tu línea Movilnet'
       o asumir que tiene Movilnet a números no 0416/0426.
     * Obligación de operar en modo captación y portabilidad para prospectos.
     * Trato empático ante aperturas como 'Nuevamente soy yo', reconociendo su línea externa.
2. En 'Router - Consultas determinísticas':
   - Calibra la condición 'telco_movilnet_fastpath' para capturar saludos y reencuentros
     ('nuevamente soy yo', 'de nuevo yo', 'volvi', 'hola') sin carga sustantiva.
3. En 'Movilnet Core & Marketing Router':
   - Reconoce saludos y reencuentros, enrutando a la competencia (0414/0424/0412) directamente
     al MÓDULO NO_USUARIOS_MOVILNET (Portabilidad 4GMAX, eSIM gratis, Bono 10GB, sin saldo interno).
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.n8n_tools import _make_request

# ==============================================================================
# 1. PROMPT Y SYSTEM MESSAGE DEL AI AGENT
# ==============================================================================
AI_AGENT_TEXT_PROMPT = r'''={{
  (() => {
    const ef = $('Edit Fields').first().json.body || {};
    const wh = $('Webhook').first().json.body || {};
    const whData = Array.isArray(wh.data) ? wh.data[0] : (wh.data || {});
    const dataKey = (whData && whData.key) || (ef.data && ef.data.key) || {};

    let rawJid = dataKey.remoteJid || whData.remoteJid || wh.sender || (ef && ef.phone) || '';
    const altJid = dataKey.remoteJidAlt || '';
    if (rawJid.endsWith('@lid')) {
      if (altJid && !altJid.endsWith('@lid')) rawJid = altJid;
      else if (whData.participant && !whData.participant.endsWith('@lid')) rawJid = whData.participant;
    }

    let cleanDigits = rawJid.replace(/@.*$/, '').replace(/[^\d]/g, '');
    if (cleanDigits.startsWith('0058') && cleanDigits.length === 14) cleanDigits = cleanDigits.slice(2);
    let national = cleanDigits;
    if (cleanDigits.startsWith('58') && cleanDigits.length === 12) national = '0' + cleanDigits.slice(2);

    const prefix = national.slice(0, 4);
    const isMovilnet = (prefix === '0416' || prefix === '0426');
    const carrier = isMovilnet ? 'Movilnet 4GMAX' : ((prefix === '0414' || prefix === '0424') ? 'Movistar Venezuela' : (prefix === '0412' ? 'Digitel 4G' : 'Operadora Externa'));
    const modoOperativo = isMovilnet ? 'ABONADO_MOVILNET_ACTIVO' : 'MODO_CAPTACION_FUNNEL_MARKETING_NO_MOVILNET';
    const pushName = whData.pushName || (ef.data && ef.data.pushName) || 'Abonado';

    return `[PERFIL DEL USUARIO]\n` +
           `- Nombre: ${pushName}\n` +
           `- Teléfono: ${national} (${carrier})\n` +
           `- MODO OPERATIVO DEL SISTEMA: ${modoOperativo}\n` +
           `- Fecha Actual: ${$now}\n\n` +
           `[MENSAJE DEL USUARIO]\n` +
           `${$json.Content}`;
  })()
}}'''

AI_AGENT_SYSTEM_MESSAGE = """Eres MOVI, el Asistente Virtual Oficial y Asesor Cognitivo de Telecomunicaciones Movilnet 4GMAX por WhatsApp (+58 424 153 3712).

MISIÓN:
Atender a los usuarios con calidez venezolana, empatía, profesionalismo y precisión. Comprendes el lenguaje coloquial venezolano, modismos y expresiones naturales sin depender de palabras clave exactas.

🚨 REGLA SOBERANA INVIOLABLE: SEGMENTACIÓN ESTRICTA POR NÚMERO (0416/0426 vs NO-MOVILNET):

A. SI EL MODO OPERATIVO ES 'ABONADO_MOVILNET_ACTIVO' (Líneas 0416 y 0426 ÚNICAMENTE):
   - El usuario ya es cliente de Movilnet. Atiéndelo cordialmente sobre su línea actual, saldo, megas, recargas C2P y planes Movilnet 4GMAX.

B. SI EL MODO OPERATIVO ES 'MODO_CAPTACION_FUNNEL_MARKETING_NO_MOVILNET' (Cualquier número DIFERENTE de 0416 y 0426: 0414, 0424, 0412, etc.):
   - ⚠️ EL USUARIO NO ES CLIENTE DE MOVILNET. Su línea pertenece a la competencia (Movistar Venezuela, Digitel, etc.).
   - 🚫 QUEDA TERMINANTEMENTE PROHIBIDO:
     * Decirle 'con tu línea Movilnet', 'tu plan Movilnet' o 'en qué te ayudo con tu línea Movilnet'.
     * Asumir que tiene plan, saldo o contrato activo en Movilnet.
     * Ofrecerle consultar el saldo de su propio número telefónico externo.
   - 🎯 ESTÁS OBLIGADO A OPERAR 100% EN MODO CAPTACIÓN Y FUNNEL MARKETING:
     1. Saludos, aperturas o reencuentros (ej: 'Nuevamente soy yo', 'Hola', 'Volví', 'Epa'):
        Salúdalo con entusiasmo y calidez venezolana, reconociendo con respeto su operadora:
        Ejemplo: "¡Qué gusto saludarte de nuevo! Veo que nos contactas desde tu línea Movistar Venezuela. ¿Cómo te podemos asesorar hoy para traerte tu número a Movilnet 4GMAX con tu eSIM gratis y bono de 10GB de bienvenida, o en qué consulta general te colaboro?"
     2. Consultas de saldo o consumo:
        Aclara amablemente que al ser de Movistar/Digitel no tenemos acceso a su saldo externo, pero invítalo a unirse a Movilnet para ahorrar hasta 60% en renta con eSIM gratis + 10GB de bono, o si desea consultar el saldo de una línea 0416/0426 que indique dicho número.
     3. Consultas abiertas o de asesoría (laptops, farmacias, restaurantes, etc.):
        Responde su consulta con amabilidad, precisión y brevedad (siguiendo la regla de datos faltantes), e incluye al final una invitación cordial a unirse a Movilnet 4GMAX para tener la mejor conectividad móvil.

ÁRBOL DE DECISIÓN COGNITIVO Y HERRAMIENTAS:
1. PORTABILIDAD Y CAMBIO DE COMPAÑÍA:
   - Invoca SIEMPRE la herramienta 'Portabilidad'.
   - Presenta con entusiasmo los beneficios exclusivos (100% gratis conservando su número, eSIM digital activada en minutos, bono de 10GB de bienvenida y WhatsApp libre).
   - Invita amablemente al usuario a indicar su Cédula de Identidad para iniciar la portabilidad express.

2. CONSULTA DE SALDO, MEGAS Y CORTE:
   - Solo para líneas 0416/0426. Para números externos, aplicar regla B.2 arriba.
   - Invoca la herramienta 'ConsultarSaldo' y responde amablemente con sus balances detallados.

3. CATÁLOGO DE PLANES Y TARIFAS:
   - Invoca la herramienta 'CatalogoPlanes' y detalla los planes de forma estructurada y atractiva (Inteliplan 10GB, Plan Conecta 5GB, Mega Plus 25GB).

4. RECARGA DE SALDO Y PAGO MÓVIL C2P:
   - Invoca la herramienta 'PagoC2P' y proporciona los datos oficiales del Banco de Venezuela para Pago Móvil C2P.

5. ROBO, EXTRAVÍO Y BLOQUEO DE IMEI:
   - Invoca la herramienta 'BloqueoIMEI' y solicita con empatía los requisitos de seguridad (Cédula y últimos 4 dígitos del IMEI).

6. TASAS DE CAMBIO (BCV / EUROS):
   - Usa 'BCV oficial' o 'BCV Euros' para tasas oficiales.
   - Tasa paralela: solo si el usuario proporciona la clave autorizada 2306.

7. REGLA INVIOLABLE DE CERO ADIVINACIÓN Y DATOS FALTANTES:
   - NUNCA adivines ni alucines información que el usuario no haya suministrado.
   - Si el usuario pide sugerencias de productos o recomendaciones de lugares (restaurantes, farmacias, automercados, clínicas, etc.) y NO indica en qué ciudad o zona se encuentra, QUEDA ESTRICTAMENTE PROHIBIDO asumir que está en Caracas o en cualquier otra ciudad.
   - En su lugar, solicita amablemente, de forma muy breve y cordial su ubicación o datos faltantes: "¿En qué ciudad o zona te encuentras para recomendarte las mejores opciones cercanas?".
   - Una vez que responda, usa las herramientas y la información verificada para responder de forma concisa, respetuosa y amigable, ahorrando tokens al máximo (2 a 4 oraciones)."""


# ==============================================================================
# 2. EXPRESIÓN DE ENRUTAMIENTO DETERMINISTA EN ROUTER
# ==============================================================================
ROUTER_TELCO_CONDITION_JS = r'''={{
  (() => {
    const raw = $json.Content || '';
    const t = raw.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();

    // 1. Intenciones Telco deterministas explícitas
    const isTelcoSpecific = /\b(saldo|megas?|datos|cupo|balance|debo|cuanto debo|corte|contrato|informa contrato|mi contrato|plan|planes|titular|recarga|recargar|recargo|como pago|pago movil|pago movil c2p|como recargar|como recargo|donde recargo|c2p|robo|hurto|extravio|bloqueo|bloquear|imei|suspender|portabilidad|portar|cambiar|migrar|adquirir|pasarme)\b/.test(t);

    // 2. Detección de saludos y aperturas de reencuentro
    const hasGreeting = /\b(hola|buen(as?|os?)|buen dia|que tal|como estas?|saludos?|buenas noches|buenos dias|buenas tardes|alo|epa|epale|hi|hello|nuevamente soy yo|soy yo de nuevo|de nuevo yo|aqui de nuevo|aqui estoy|otra vez yo|volvi|buenas de nuevo)\b/.test(t);

    // Si no tiene nada de lo anterior, no es fastpath determinista
    if (!isTelcoSpecific && !hasGreeting) return false;

    // 3. Si tiene saludo o reencuentro pero NO es una intención telco explícita:
    // Analizar si es Saludo Puro o Consulta Compuesta (ej: "Hola, quiero comprar una laptop...")
    if (hasGreeting && !isTelcoSpecific) {
      // Limpiar saludos, cortesías y reencuentros para evaluar si queda contenido sustantivo
      const residual = t
        .replace(/\b(hola|buenos dias|buenas tardes|buenas noches|buen dia|que tal|como estas?|saludos?|alo|epa|epale|hi|hello|buenas?|buenos?|amig[oa]s?|equipo|gente|asistente|bot|movilnet|senor|senora|sr|sra|estimad[oa]s?|gracias|muchas gracias|bendiciones|por favor|porfa|ok|vale|listo|aqui|alli|nuevamente|soy|yo|de nuevo|otra vez|volvi|estoy)\b/g, '')
        .replace(/[^a-z0-9\s]/g, ' ')
        .trim();

      const words = residual.split(/\s+/).filter(w => w.length > 0);
      const hasQuestion = /[\?¿]/.test(raw) || /\b(que|cual|cuales|como|donde|cuando|cuanto|cuanta|porque|quien|recomiendas?|quiero|busco|necesito|laptop|computadora|farmacia|restaurante|tienda|comprar)\b/.test(t);

      // Si tiene palabras residuales o indicadores de pregunta -> ES CONSULTA COMPUESTA
      // -> NO debe ser interceptado por FastPath -> Retorna false para viajar a AI Agent!
      if (words.length > 0 || hasQuestion) {
        return false;
      }
    }

    return true;
  })()
}}'''


# ==============================================================================
# 3. CÓDIGO JS REFINADO PARA 'Movilnet Core & Marketing Router'
# ==============================================================================
ROUTER_CORE_MARKETING_JS = r'''for (const item of items) {
  // 1. Extraer datos del remitente y mensaje con soporte universal (Object o Array) y resolución LID
  const ef = $('Edit Fields').first().json.body || {};
  const wh = $('Webhook').first().json.body || {};
  const whData = Array.isArray(wh.data) ? wh.data[0] : (wh.data || {});
  const dataKey = (whData && whData.key) || (ef.data && ef.data.key) || {};

  let rawJid = dataKey.remoteJid || whData.remoteJid || wh.sender || (ef && ef.phone) || '';
  const altJid = dataKey.remoteJidAlt || '';
  if (rawJid.endsWith('@lid')) {
    if (altJid && !altJid.endsWith('@lid')) {
      rawJid = altJid;
    } else if (whData.participant && !whData.participant.endsWith('@lid')) {
      rawJid = whData.participant;
    }
  }

  const pushName = whData.pushName || (ef.data && ef.data.pushName) || 'Abonado';
  const rawMsg = item.json.Content || '';
  const cleanMsg = rawMsg.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
  const normalizedMsg = cleanMsg.replace(/(.)\1+/g, '$1');

  // 2. Normalizar número a formato legible nacional e internacional
  let cleanDigits = rawJid.replace(/@.*$/, '').replace(/[^\d]/g, '');
  if (cleanDigits.startsWith('0058') && cleanDigits.length === 14) {
    cleanDigits = cleanDigits.slice(2);
  }
  let nationalNumber = cleanDigits;
  if (cleanDigits.startsWith('58') && cleanDigits.length === 12) {
    nationalNumber = '0' + cleanDigits.slice(2);
  }

  let phoneFormatted = cleanDigits;
  if (cleanDigits.startsWith('58') && cleanDigits.length === 12) {
    phoneFormatted = '+58 ' + cleanDigits.slice(2, 5) + ' ' + cleanDigits.slice(5);
  } else if (cleanDigits.length === 11 && cleanDigits.startsWith('0')) {
    phoneFormatted = '+58 ' + cleanDigits.slice(1, 4) + ' ' + cleanDigits.slice(4);
  }

  const prefix = nationalNumber.slice(0, 4);
  const isMovilnet = (prefix === '0416' || prefix === '0426');
  const isCompetitor = !isMovilnet;
  const competitorLabel = (prefix === '0414' || prefix === '0424') ? 'Movistar Venezuela' : (prefix === '0412' ? 'Digitel 4G' : 'Operadora Externa');

  // 3. Saludo dinámico según horario de Venezuela (UTC-4)
  const nowUtc = new Date();
  const vetHour = (nowUtc.getUTCHours() - 4 + 24) % 24;
  let saludoDia = '¡Buenas noches';
  if (vetHour >= 5 && vetHour < 12) saludoDia = '¡Buenos días';
  else if (vetHour >= 12 && vetHour < 19) saludoDia = '¡Buenas tardes';

  // Enlace PWA oficial
  const pwaCarrierSlug = isCompetitor ? ((prefix === '0414' || prefix === '0424') ? 'movistar' : 'digitel') : 'movilnet';
  const pwaLink = `\n\n🌐 *Portal PWA 4GMAX (Datos Móviles 3G/4G/5G):* https://mixture-merchandise-jumping-expenditures.trycloudflare.com/ui/pwa_stitch/index.html?carrier=${pwaCarrierSlug}&phone=${cleanDigits}&token=${cleanDigits.slice(-8)}4gmax`;

  // 4. Lógica de Enrutamiento y Generación de Respuesta
  let replyText = '';
  let pipelineRoute = 'FAST_PATH_TELCO_ODA';

  // EVALUAR SI ES SALUDO O REENCUENTRO PURO:
  const residualGreeting = cleanMsg
    .replace(/\b(hola|buenos dias|buenas tardes|buenas noches|buen dia|que tal|como estas?|saludos?|alo|epa|epale|hi|hello|buenas?|buenos?|amig[oa]s?|equipo|gente|asistente|bot|movilnet|senor|senora|sr|sra|estimad[oa]s?|gracias|muchas gracias|bendiciones|por favor|porfa|ok|vale|listo|nuevamente|soy|yo|de nuevo|otra vez|volvi|estoy|aqui)\b/g, '')
    .replace(/[^a-z0-9\s]/g, ' ')
    .trim();
  const isPureGreeting = (residualGreeting.split(/\s+/).filter(w => w.length > 0).length === 0) && !/[\?¿]/.test(rawMsg);

  // CASO A: CONSULTA DE SALDO, DEUDA, BALANCE O CORTE
  if (/saldo|cuanto debo|debo|balance|cuenta|corte/.test(cleanMsg) || /saldo|cuanto debo|debo|balance|cuenta|corte/.test(normalizedMsg)) {
    if (isCompetitor) {
      pipelineRoute = 'FUNNEL_MARKETING_NO_USUARIOS_MOVILNET';
      replyText = `👋 ${saludoDia}, ${pushName}! Te damos la más cordial bienvenida a *Movilnet 4GMAX*.\n\n` +
                  `Identificamos que nos contactas desde tu línea ${competitorLabel} (\`${phoneFormatted}\`). ` +
                  `Por normativas de telecomunicaciones y resguardo de privacidad de CONATEL, las plataformas de facturación ` +
                  `y saldo de ${competitorLabel} son independientes, por lo que como canal oficial de Movilnet no podemos consultar saldos externos.\n\n` +
                  `🚀 *¡Pero puedes unirte a Movilnet conservando tu mismo número!*\n` +
                  `• ✨ *eSIM Digital Inmediata:* Activación rápida mediante código QR.\n` +
                  `• 🎁 *Bono de Bienvenida:* 10 GB de navegación gratis de obsequio.\n` +
                  `• 💵 *Ahorro Garantizado:* Hasta 60% menos en renta mensual.\n\n` +
                  `Si deseas consultar el saldo de una línea Movilnet (0416/0426), escribe el número a consultar.`;
    } else {
      pipelineRoute = 'FAST_PATH_TELCO_ODA';
      replyText = `Estimado abonado Movilnet (${phoneFormatted}):\n\n` +
                  `💰 Tu consulta de saldo se procesa directamente vía OCS en tiempo real.\n` +
                  `Para recargar tu saldo vía Pago Móvil C2P, escribe 'Recarga'.`;
    }

  // CASO B: MEGAS Y DATOS
  } else if (/mega|datos|cupo|navegacion|gigas?/.test(cleanMsg) || /mega|datos|cupo|navegacion|gigas?/.test(normalizedMsg)) {
    if (isCompetitor) {
      pipelineRoute = 'FUNNEL_MARKETING_NO_USUARIOS_MOVILNET';
      replyText = `${saludoDia}, ${pushName}! Te comunicas desde una línea *${competitorLabel}* (${phoneFormatted}).\n\n` +
                  `📶 En *Movilnet 4GMAX* puedes disfrutar de *Inteliplan 10 GB* por solo Bs. 295/mes + *10 GB de Bono de Bienvenida GRATIS* y WhatsApp libre al portar tu número.\n\n` +
                  `Escribe *Portabilidad* para solicitar tu eSIM digital gratuita.`;
    } else {
      pipelineRoute = 'FAST_PATH_TELCO_ODA';
      replyText = `Estimado abonado Movilnet (${phoneFormatted}):\n\n` +
                  `📶 Navegación 4GMAX: 10.0 GB disponibles de tu cuota de 10 GB.\n` +
                  `🚀 Estado de Red: Cobertura 4GMAX LTE Activa.\n` +
                  `✨ WhatsApp libre incluido en tu ciclo actual.`;
    }

  // CASO C: RECARGAS Y PAGOS C2P
  } else if (/recarga|pagar|pago movil|c2p/.test(cleanMsg) || /recarga|pagar|pago movil|c2p/.test(normalizedMsg)) {
    replyText = `Recarga Digital Movilnet (${phoneFormatted}):\n\n` +
                `Puedes recargar cualquier línea Movilnet (0416/0426) mediante Pago Móvil C2P SUDEBAN instantáneo desde cualquier banco nacional:\n` +
                `• Banco Receptor: Banco de Venezuela (0102)\n` +
                `• RIF: G-20000012-3\n` +
                `• Teléfono: 0424-1533712\n\n` +
                `Indica el monto a recargar (Monto mínimo: Bs. 150,00).`;

  // CASO D: PLANES Y TARIFAS
  } else if (/plan|planes|inteliplan|conecta|tarifa/.test(cleanMsg) || /plan|planes|inteliplan|conecta|tarifa/.test(normalizedMsg)) {
    replyText = `Catálogo de Planes Oficiales Movilnet 4GMAX:\n\n` +
                `1. Inteliplan 10GB: 10 GB de datos + 1.000 Minutos + 1.000 SMS (Bs. 295/mes).\n` +
                `2. Plan Conecta 5GB: 5 GB de datos + 500 Minutos + 500 SMS (Bs. 180/mes).\n` +
                `3. Plan Mega Plus 25GB: 25 GB de datos + Minutos libres (Bs. 590/mes).\n\n` +
                `Para activar o cambiar tu plan, responde con el nombre del plan deseado.`;

  // CASO E: PORTABILIDAD EXPRESS
  } else if (/portabilidad|cambiar|migrar|esim|quiero movilnet|adquirir|pasarme/.test(cleanMsg) || /portabilidad|cambiar|migrar|esim|quiero movilnet|adquirir|pasarme/.test(normalizedMsg)) {
    pipelineRoute = 'FUNNEL_MARKETING_NO_USUARIOS_MOVILNET';
    replyText = `🎯 ¡Excelente decisión, ${pushName}!\n\n` +
                `Cambiarte a Movilnet 4GMAX es 100% GRATIS conservando tu mismo número (${phoneFormatted}).\n\n` +
                `🎁 Beneficios exclusivos de bienvenida:\n` +
                `• Tu eSIM digital gratis activada en minutos\n` +
                `• Bono de 10 GB de navegación gratis\n` +
                `• WhatsApp libre en toda Venezuela\n\n` +
                `Para iniciar tu activación express, responde con tu número de Cédula de Identidad.`;

  // CASO F: SEGURIDAD, ROBO O BLOQUEO DE IMEI
  } else if (/robo|hurto|bloqueo|extravio|imei|suspender/.test(cleanMsg) || /robo|hurto|bloqueo|extravio|imei|suspender/.test(normalizedMsg)) {
    replyText = `🚨 Centro de Seguridad y Bloqueo EIR Movilnet:\n\n` +
                `Para suspender temporalmente tu línea Movilnet por robo o extravío, confirma tu número de Cédula de Identidad y los últimos 4 dígitos del IMEI.`;

  // CASO G: CONTRATO / TITULAR
  } else if (/contrato|titular|informa contrato/.test(cleanMsg) || /contrato|titular|informa contrato/.test(normalizedMsg)) {
    if (isCompetitor) {
      pipelineRoute = 'FUNNEL_MARKETING_NO_USUARIOS_MOVILNET';
      replyText = `Estimado(a) ${pushName}, el número ${phoneFormatted} pertenece a *${competitorLabel}* y aún no registra un contrato activo en Movilnet 4GMAX (0416/0426).\n\n` +
                  `✨ Solicita hoy tu *Portabilidad Express* con eSIM Digital GRATIS y recibe *10 GB de bono de bienvenida*.`;
    } else {
      pipelineRoute = 'FAST_PATH_TELCO_ODA';
      replyText = `Estimado(a) ${pushName}, tu contrato para la línea Movilnet ${phoneFormatted} está ACTIVO en el plan Inteliplan 10GB 4GMAX.\n\n` +
                  `🔒 Estado EIR: Habilitado y Seguro`;
    }

  // CASO H: SALUDOS PUROS Y REENCUENTROS (DISTINGUIR ABONADO 0416/0426 vs NO USUARIO)
  } else if (isPureGreeting) {
    if (isCompetitor) {
      // MÓDULO OBLIGATORIO: NO_USUARIOS_MOVILNET (Funnel Marketing Portabilidad 4GMAX)
      pipelineRoute = 'FUNNEL_MARKETING_NO_USUARIOS_MOVILNET';
      replyText = `👋 ${saludoDia}, ${pushName}! Te damos la bienvenida al canal oficial de *Movilnet 4GMAX*.\n\n` +
                  `Detectamos que te comunicas desde una línea *${competitorLabel}* (${phoneFormatted}).\n\n` +
                  `🚀 *Módulo de Nuevos Usuarios & Portabilidad 4GMAX:*\n` +
                  `• 🔄 *Cámbiate GRATIS a Movilnet:* Conserva tu mismo número con eSIM digital inmediata.\n` +
                  `• 🎁 *Bono de Bienvenida:* 10 GB de navegación gratis durante tu primer mes.\n` +
                  `• 💰 *Ahorro Comprobado:* Hasta 60% menos en tu renta mensual.\n\n` +
                  `¿Qué deseas realizar hoy?\n` +
                  `• Escribe *'Portabilidad'* para tramitar tu eSIM gratis con 10GB de bono.\n` +
                  `• Escribe *'Planes'* para conocer tarifas y comparar tu ahorro.\n` +
                  `• Escribe *'Recarga'* si deseas recargar la línea de un tercero Movilnet con Pago Móvil C2P.\n` +
                  `• O hazme cualquier pregunta sobre servicios, tecnología o dudas generales.`;
    } else {
      // MÓDULO EXCLUSIVO: ABONADOS ÚNICOS MOVILNET (0416 / 0426)
      pipelineRoute = 'FAST_PATH_TELCO_ODA';
      replyText = `👋 ${saludoDia}, ${pushName}! Bienvenido al canal de autoservicio *Movilnet 4GMAX* (${phoneFormatted}).\n\n` +
                  `📋 *Menú de Autogestión Oficial Movilnet:*\n` +
                  `• Escribe *'Saldo'* para consultar tu balance disponible y megas.\n` +
                  `• Escribe *'Planes'* para conocer nuestras tarifas activas.\n` +
                  `• Escribe *'Recarga'* para recargar mediante Pago Móvil C2P.\n` +
                  `• Escribe *'Contrato'* para consultar tu información de contrato.\n` +
                  `• O pregúntame cualquier consulta sobre tu servicio.`;
    }

  // CASO I: FALLBACK GENERAL
  } else {
    if (isCompetitor) {
      pipelineRoute = 'FUNNEL_MARKETING_NO_USUARIOS_MOVILNET';
      replyText = `Estimado usuario (${phoneFormatted}):\n\n` +
                  `Bienvenido al Centro de Atención Digital Movilnet 4GMAX.\n` +
                  `Detectamos que nos contactas desde tu línea ${competitorLabel}.\n` +
                  `• Escribe 'Portabilidad' para cambiarte gratis a Movilnet con eSIM y 10GB de bono.\n` +
                  `• Escribe 'Planes' para conocer tarifas disponibles.\n` +
                  `• Escribe 'Recarga' para recargar a un tercero con Pago Móvil C2P.`;
    } else {
      pipelineRoute = 'FAST_PATH_TELCO_ODA';
      replyText = `Estimado abonado Movilnet (${phoneFormatted}):\n\n` +
                  `Bienvenido al Centro de Autogestión Movilnet 4GMAX.\n` +
                  `• Escribe 'Saldo' para consultar balance disponible.\n` +
                  `• Escribe 'Planes' para conocer tarifas.\n` +
                  `• Escribe 'Recarga' para recargar con Pago Móvil C2P.\n` +
                  `• Escribe 'Portabilidad' para solicitar nueva eSIM.`;
    }
  }

  // 5. Salida para convergencia y entrega en WhatsApp
  replyText = replyText + pwaLink;
  item.json.verdict = "ALLOW_VALID_USER_MESSAGE";
  item.json.output = replyText;
  item.json.final_text = replyText;
  item.json.pipeline_route = pipelineRoute;
  item.json.carrier_phone = cleanDigits;
}

return items;'''


def apply_update():
    print("📡 Obteniendo workflow sNMbtiEiTkuQ9OCY desde n8n Cloud...")
    res = _make_request("workflows/sNMbtiEiTkuQ9OCY")
    if not res.get("success"):
        print(f"❌ Error al obtener workflow: {res}")
        return False

    wf = res["data"]
    nodes = wf.get("nodes", [])

    updated_ai_agent = False
    updated_router_cond = False
    updated_marketing_router = False

    for n in nodes:
        node_name = n.get("name")
        if node_name == "AI Agent":
            params = n.setdefault("parameters", {})
            params["promptType"] = "define"
            params["text"] = AI_AGENT_TEXT_PROMPT
            opts = params.setdefault("options", {})
            opts["systemMessage"] = AI_AGENT_SYSTEM_MESSAGE
            updated_ai_agent = True
            print("  ✅ Nodo 'AI Agent' actualizado con inyección dinámica de MODO OPERATIVO y REGLA SOBERANA NO-MOVILNET.")

        elif node_name == "Router - Consultas determinísticas":
            params = n.setdefault("parameters", {})
            rules = params.get("rules", {}).get("values", [])
            for r in rules:
                if r.get("outputKey") == "telco_movilnet_fastpath":
                    conds = r.get("conditions", {}).get("conditions", [])
                    for c in conds:
                        c["leftValue"] = ROUTER_TELCO_CONDITION_JS
                        updated_router_cond = True
                        print("  ✅ Condición 'telco_movilnet_fastpath' actualizada con soporte de reencuentros.")

        elif node_name == "Movilnet Core & Marketing Router":
            n.setdefault("parameters", {})["jsCode"] = ROUTER_CORE_MARKETING_JS
            updated_marketing_router = True
            print("  ✅ Nodo 'Movilnet Core & Marketing Router' actualizado con módulo estricto NO_USUARIOS_MOVILNET.")

    if not (updated_ai_agent and updated_router_cond and updated_marketing_router):
        print(f"⚠️ Advertencia: ai_agent={updated_ai_agent}, router_cond={updated_router_cond}, marketing={updated_marketing_router}")

    # Guardar copia local del workflow
    local_out = PROJECT_ROOT / "api" / "n8n_workflows" / "viki_lpgtec_v2_ids_instant_dispatch.json"
    clean_settings = {
        "executionOrder": wf.get("settings", {}).get("executionOrder", "v1"),
        "timezone": wf.get("settings", {}).get("timezone", "America/Caracas"),
        "callerPolicy": wf.get("settings", {}).get("callerPolicy", "workflowsFromSameOwner")
    }

    payload = {
        "name": wf.get("name"),
        "nodes": nodes,
        "connections": wf.get("connections", {}),
        "settings": clean_settings
    }

    print("🚀 Desplegando workflow actualizado hacia n8n Cloud...")
    put_res = _make_request("workflows/sNMbtiEiTkuQ9OCY", method="PUT", data=payload)
    if put_res.get("success"):
        print("🎉 ¡Workflow sNMbtiEiTkuQ9OCY actualizado exitosamente en n8n Cloud!")
        with open(local_out, "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=2, ensure_ascii=False)
        print(f"💾 Copia local sincronizada en {local_out}")
        return True
    else:
        print(f"❌ Error al desplegar en n8n Cloud: {put_res}")
        return False


if __name__ == "__main__":
    success = apply_update()
    sys.exit(0 if success else 1)
