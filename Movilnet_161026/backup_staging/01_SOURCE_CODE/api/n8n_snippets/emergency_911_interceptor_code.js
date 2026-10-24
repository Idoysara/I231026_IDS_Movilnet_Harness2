// =========================================================================
// n8n Code Node: Emergency_911_PreFirewall_Interceptor
// Propósito: Interceptar emergencias de máxima prioridad antes de compuertas
// Proyecto: Movilnet Core 4GMAX — Asistente MOVI (Carrier-Grade)
// =========================================================================

const item = $input.first().json;
const body = item.body || item;
const data = body.data || {};
const messageObj = data.message || {};
const key = data.key || {};
const remoteJid = key.remoteJid || body.remoteJid || "";

// 1. Descarte estricto de seguridad para números no autorizados / decommissioned
if (remoteJid.includes("4166251587")) {
  return [];
}

// 2. Extraer contenido de texto y ubicación
const conversation = (
  messageObj.conversation ||
  messageObj.extendedTextMessage?.text ||
  data.messageText ||
  body.message ||
  ""
).trim();

const messageType = data.messageType || "";

// Detección de mensajes de ubicación nativa (Evolution API / WhatsApp Baileys / Meta Cloud)
const locMessage = messageObj.locationMessage || messageObj.liveLocationMessage || body.locationMessage || {};
const latitude = locMessage.degreesLatitude || locMessage.latitude || null;
const longitude = locMessage.degreesLongitude || locMessage.longitude || null;
const hasLocation = Boolean(latitude !== null && longitude !== null) || messageType.toLowerCase().includes("location");

// 3. Patrón léxico de alta prioridad (Accidentes, Robos, Salud, 911, Policía)
const emergencyRegex = /\b(911|171|emergencia|emergencias|auxilio|socorro|policia|policía|ambulancia|ambulancias|bomberos|bombero|me estan robando|me están robando|robando|robo|secuestro|secuestraron|me secuestran|accidente|accidentes|choque grave|herido|heridos|fuego|incendio)\b/i;
const isEmergencyText = emergencyRegex.test(conversation);

// 4. Memoria estática de n8n para sesiones de auxilio en progreso
const staticData = $getWorkflowStaticData('global');
staticData.emergencySessions = staticData.emergencySessions || {};
const lastSessionTime = staticData.emergencySessions[remoteJid];
const hasActiveSession = Boolean(lastSessionTime && (Date.now() - lastSessionTime) < 1800000); // 30 min TTL

const isEmergency = isEmergencyText || (hasLocation && hasActiveSession);

if (isEmergency) {
  // Renovar sesión activa
  staticData.emergencySessions[remoteJid] = Date.now();

  const mapsUrl = (latitude && longitude) ? `https://www.google.com/maps?q=${latitude},${longitude}` : null;

  return [{
    json: {
      ...item,
      IS_EMERGENCY_ACTIVE: true,
      EMERGENCY_DATA: {
        remoteJid,
        rawText: conversation,
        hasLocation,
        latitude,
        longitude,
        mapsUrl,
        timestamp: new Date().toISOString()
      },
      override_pipeline: "EMERGENCY_DISPATCH_911",
      target_subagent: "Emergency_911_Dispatcher"
    }
  }];
}

// Tráfico no crítico: continúa por el firewall de operadoras estándar
return [{
  json: {
    ...item,
    IS_EMERGENCY_ACTIVE: false,
    override_pipeline: null
  }
}];
