#!/usr/bin/env python3
"""
scripts/update_n8n_workflow_geo.py — Actualización del Workflow n8n para Geolocalización de Oficinas Movilnet
============================================================================================================
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)
Modificaciones aplicadas:
1. 'Edit Fields': soporte para msg.locationMessage y msg.liveLocationMessage (messageType: 'ubicacion').
2. 'Switch': regla para messageType 'ubicacion' enrutada a 'Captura Texto'.
3. 'Router - Consultas determinísticas': regla para capturar intenciones de oficinas o ubicaciones GPS.
4. 'Movilnet Core & Marketing Router': resolución determinista de oficina más cercana con Haversine,
   distancia, estimados a pie/vehículo, Google Maps y diferenciación 0416/0426 vs No-Usuarios.
"""

from __future__ import annotations

import json
from pathlib import Path

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / "api" / "n8n_workflows" / "viki_lpgtec_v2_ids_instant_dispatch.json"


def update_n8n_workflow(file_path: Path = WORKFLOW_PATH) -> bool:
    with open(file_path, "r", encoding="utf-8") as f:
        wf = json.load(f)

    # -------------------------------------------------------------------------
    # 1. Modificar nodo 'Edit Fields'
    # -------------------------------------------------------------------------
    ef = next((n for n in wf["nodes"] if n["name"] == "Edit Fields"), None)
    if not ef:
        raise ValueError("Nodo 'Edit Fields' no encontrado en el workflow.")

    assignments = ef["parameters"]["assignments"]["assignments"]

    for a in assignments:
        if a["name"] == "body.data.messageType":
            a["value"] = (
                "={{\n"
                "  (() => {\n"
                "    const whData = Array.isArray($('Webhook').item.json.body?.data) ? $('Webhook').item.json.body.data[0] : $('Webhook').item.json.body?.data;\n"
                "    const msg = whData?.message || {};\n"
                "    if (msg.locationMessage || msg.liveLocationMessage) return 'ubicacion';\n"
                "    if (msg.documentMessage) return 'pdf';\n"
                "    if (msg.imageMessage) return 'imagen';\n"
                "    if (msg.audioMessage) return 'audio';\n"
                "    if (msg.videoMessage) return 'video';\n"
                "    if (msg.conversation || msg.extendedTextMessage) return 'texto';\n"
                "    return 'texto';\n"
                "  })()\n"
                "}}"
            )
        elif a["name"] == "body.data.message.extended":
            a["value"] = (
                "={{\n"
                "  (() => {\n"
                "    const whData = Array.isArray($('Webhook').item.json.body?.data) ? $('Webhook').item.json.body.data[0] : $('Webhook').item.json.body?.data;\n"
                "    const msg = whData?.message || {};\n"
                "    const loc = msg.locationMessage || msg.liveLocationMessage;\n"
                "    if (loc) {\n"
                "      const lat = loc.degreesLatitude ?? loc.latitude;\n"
                "      const lon = loc.degreesLongitude ?? loc.longitude;\n"
                "      const name = loc.name || loc.address || '';\n"
                "      return `[UBICACION_GPS: lat=${lat}, lon=${lon}${name ? ', ref=' + name : ''}]`;\n"
                "    }\n"
                "    return msg.extendedTextMessage?.text || msg.conversation || msg.imageMessage?.caption || msg.videoMessage?.caption || '';\n"
                "  })()\n"
                "}}"
            )

    # Agregar body.data.location
    if not any(a["name"] == "body.data.location" for a in assignments):
        assignments.append({
            "id": "geo-location-extract-001",
            "name": "body.data.location",
            "type": "object",
            "value": (
                "={{\n"
                "  (() => {\n"
                "    const whData = Array.isArray($('Webhook').item.json.body?.data) ? $('Webhook').item.json.body.data[0] : $('Webhook').item.json.body?.data;\n"
                "    const msg = whData?.message || {};\n"
                "    const loc = msg.locationMessage || msg.liveLocationMessage;\n"
                "    if (loc) {\n"
                "      return {\n"
                "        latitude: loc.degreesLatitude ?? loc.latitude,\n"
                "        longitude: loc.degreesLongitude ?? loc.longitude,\n"
                "        name: loc.name || loc.address || ''\n"
                "      };\n"
                "    }\n"
                "    return null;\n"
                "  })()\n"
                "}}"
            )
        })

    # -------------------------------------------------------------------------
    # 2. Modificar nodo 'Switch' para incluir la regla 'ubicacion'
    # -------------------------------------------------------------------------
    switch_node = next((n for n in wf["nodes"] if n["name"] == "Switch"), None)
    if switch_node:
        switch_rules = switch_node["parameters"]["rules"]["values"]
        if not any(r.get("outputKey") == "ubicacion" for r in switch_rules):
            switch_rules.append({
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2
                    },
                    "conditions": [
                        {
                            "id": "switch-rule-geo-ubicacion-001",
                            "leftValue": "={{ $json.body.data.messageType.toString() }}",
                            "rightValue": "ubicacion",
                            "operator": {
                                "type": "string",
                                "operation": "contains"
                            }
                        }
                    ],
                    "combinator": "and"
                },
                "renameOutput": True,
                "outputKey": "ubicacion"
            })

    # Conectar la salida de 'ubicacion' en Switch hacia 'Captura Texto'
    # La salida 0 es texto, 1 imagen, 2 audio, 3 video, 4 pdf, 5 ubicacion
    conns = wf.setdefault("connections", {})
    switch_conns = conns.setdefault("Switch", {}).setdefault("main", [])
    # Asegurar que switch_conns tenga al menos 6 salidas
    while len(switch_conns) < 6:
        switch_conns.append([])
    # Conectar salida 5 (ubicacion) a 'Captura Texto'
    if not any(target.get("node") == "Captura Texto" for target in switch_conns[5]):
        switch_conns[5].append({"node": "Captura Texto", "type": "main", "index": 0})

    # -------------------------------------------------------------------------
    # 3. Modificar nodo 'Router - Consultas determinísticas'
    # -------------------------------------------------------------------------
    router_det = next((n for n in wf["nodes"] if n["name"] == "Router - Consultas determinísticas"), None)
    if router_det:
        rules = router_det["parameters"]["rules"]["values"]
        telco_rule = next((r for r in rules if r.get("outputKey") == "telco_movilnet_fastpath"), None)
        if telco_rule:
            cond = telco_rule["conditions"]["conditions"][0]
            cond["leftValue"] = (
                "={{\n"
                "  (() => {\n"
                "    const raw = $json.Content || '';\n"
                "    const t = raw.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').trim();\n\n"
                "    // 1. Detección de mensajes de ubicación GPS sintéticos\n"
                "    const isLocationMsg = /\\[UBICACION_GPS:/.test(raw) || /\\[UBICACION_GPS:/.test(t);\n\n"
                "    // 2. Intenciones Telco deterministas explícitas (incluyendo oficinas y agencias)\n"
                "    const isTelcoSpecific = isLocationMsg || /\\b(saldo|megas?|datos|cupo|balance|debo|cuanto debo|corte|contrato|informa contrato|mi contrato|plan|planes|titular|recarga|recargar|recargo|como pago|pago movil|pago movil c2p|como recargar|como recargo|donde recargo|c2p|robo|hurto|extravio|bloqueo|bloquear|imei|suspender|portabilidad|portar|cambiar|migrar|adquirir|pasarme|oficina|oficinas|agencia|agencias|sucursal|sucursales|sede|sedes|donde queda|donde estan|ubicados|atencion presencial|direccion movilnet)\\b/.test(t);\n\n"
                "    // 3. Detección de saludos y aperturas de reencuentro\n"
                "    const hasGreeting = /\\b(hola|buen(as?|os?)|buen dia|que tal|como estas?|saludos?|buenas noches|buenos dias|buenas tardes|alo|epa|epale|hi|hello|nuevamente soy yo|soy yo de nuevo|de nuevo yo|aqui de nuevo|aqui estoy|otra vez yo|volvi|buenas de nuevo)\\b/.test(t);\n\n"
                "    if (!isTelcoSpecific && !hasGreeting) return false;\n\n"
                "    // Si es saludo puro vs consulta compuesta\n"
                "    if (hasGreeting && !isTelcoSpecific) {\n"
                "      const residual = t\n"
                "        .replace(/\\b(hola|buenos dias|buenas tardes|buenas noches|buen dia|que tal|como estas?|saludos?|alo|epa|epale|hi|hello|buenas?|buenos?|amig[oa]s?|equipo|gente|asistente|bot|movilnet|senor|senora|sr|sra|estimad[oa]s?|gracias|muchas gracias|bendiciones|por favor|porfa|ok|vale|listo|aqui|alli|nuevamente|soy|yo|de nuevo|otra vez|volvi|estoy)\\b/g, '')\n"
                "        .replace(/[^a-z0-9\\s]/g, ' ')\n"
                "        .trim();\n\n"
                "      const words = residual.split(/\\s+/).filter(w => w.length > 0);\n"
                "      const hasQuestion = /[\\?\\¿]/.test(raw) || /\\b(que|cual|cuales|como|donde|cuando|cuanto|cuanta|porque|quien|recomiendas?|quiero|busco|necesito|laptop|computadora|farmacia|restaurante|tienda|comprar)\\b/.test(t);\n\n"
                "      if (words.length > 0 || hasQuestion) {\n"
                "        return false;\n"
                "      }\n"
                "    }\n\n"
                "    return true;\n"
                "  })()\n"
                "}}"
            )

    # -------------------------------------------------------------------------
    # 4. Modificar nodo 'Movilnet Core & Marketing Router'
    # -------------------------------------------------------------------------
    router_code = next((n for n in wf["nodes"] if n["name"] == "Movilnet Core & Marketing Router"), None)
    if router_code:
        current_js = router_code["parameters"]["jsCode"]
        # Inyectar el caso CASO_GEO antes del CASO A: SALDO
        geo_block = """  // CASO GEO: LOCALIZADOR DE OFICINAS Y AGENCIAS MOVILNET (GPS o Consulta Textual)
  if (/\\[UBICACION_GPS:/.test(rawMsg) || /oficina|oficinas|agencia|agencias|sucursal|sucursales|sede|sedes|donde queda|donde estan|ubicados|atencion presencial|direccion movilnet/.test(cleanMsg)) {
    const gpsMatch = rawMsg.match(/\\[UBICACION_GPS:\\s*lat=([0-9.-]+),\\s*lon=([0-9.-]+)/);
    let userLat = gpsMatch ? parseFloat(gpsMatch[1]) : null;
    let userLon = gpsMatch ? parseFloat(gpsMatch[2]) : null;

    if (!userLat && ef.data && ef.data.location) {
      userLat = ef.data.location.latitude;
      userLon = ef.data.location.longitude;
    }

    pipelineRoute = isCompetitor ? 'FUNNEL_MARKETING_NO_USUARIOS_MOVILNET' : 'FAST_PATH_TELCO_ODA';

    if (userLat !== null && userLon !== null) {
      if (userLat < 0.6 || userLat > 12.5 || userLon < -73.5 || userLon > -59.8) {
        replyText = `📍 *Localizador de Agencias Movilnet 4GMAX:*\\n\\n` +
                    `Detectamos que las coordenadas compartidas se encuentran fuera de Venezuela. ` +
                    `Nuestra red de atención presencial opera exclusivamente dentro del territorio nacional.\\n\\n` +
                    `Si te encuentras en Venezuela, comparte nuevamente tu ubicación actual por WhatsApp o escribe el nombre de tu ciudad.`;
      } else {
        const offices = [
          { name: "Oficina Comercial Movilnet Centro Plaza", lat: 10.4960, lon: -66.8525, addr: "Av. Francisco de Miranda, CC Centro Plaza, Nivel 3, Los Palos Grandes, Chacao, Caracas", hours: "Lunes a Sábado 09:00 - 17:00" },
          { name: "Oficina Comercial Movilnet Torre El Rosal (Sede Principal)", lat: 10.4890, lon: -66.8670, addr: "Av. Venezuela, Torre Movilnet, Urb. El Rosal, Chacao, Caracas", hours: "Lunes a Viernes 08:00 - 16:30" },
          { name: "Oficina Comercial Movilnet Sambil Chacao", lat: 10.4905, lon: -66.8580, addr: "CC Sambil Chacao, Nivel Autopista, Chacao, Caracas", hours: "Lunes a Domingo 10:00 - 19:00" },
          { name: "Oficina Comercial Movilnet Sambil La Candelaria", lat: 10.5050, lon: -66.9040, addr: "CC Sambil La Candelaria, Nivel Andrés Bello, Caracas", hours: "Lunes a Sábado 10:00 - 18:30" },
          { name: "Oficina Comercial Movilnet El Recreo", lat: 10.4920, lon: -66.8770, addr: "CC El Recreo, Nivel C2, Sabana Grande, Caracas", hours: "Lunes a Sábado 10:00 - 18:00" },
          { name: "Oficina Comercial Movilnet Metrópolis Valencia", lat: 10.1980, lon: -67.9540, addr: "CC Metrópolis Valencia, Nivel Sol, San Diego / Valencia, Carabobo", hours: "Lunes a Sábado 10:00 - 18:30" },
          { name: "Oficina Comercial Movilnet Sambil Valencia", lat: 10.2330, lon: -67.9890, addr: "CC Sambil Valencia, Naguanagua, Carabobo", hours: "Lunes a Sábado 10:00 - 19:00" },
          { name: "Oficina Comercial Movilnet Maracaibo 5 de Julio", lat: 10.6680, lon: -71.6180, addr: "Calle 77 (5 de Julio) con Av. 15 Delicias, Maracaibo, Zulia", hours: "Lunes a Viernes 08:30 - 16:30" },
          { name: "Oficina Comercial Movilnet Lago Mall Maracaibo", lat: 10.6800, lon: -71.6020, addr: "CC Lago Mall, Av. 2 El Milagro, Maracaibo, Zulia", hours: "Lunes a Sábado 10:00 - 18:00" },
          { name: "Oficina Comercial Movilnet Las Trinitarias Barquisimeto", lat: 10.0760, lon: -69.2880, addr: "CC Las Trinitarias, Barquisimeto, Lara", hours: "Lunes a Sábado 09:30 - 18:00" },
          { name: "Oficina Comercial Movilnet Plaza Mayor Puerto La Cruz", lat: 10.1950, lon: -64.6750, addr: "CC Plaza Mayor, Lechería / Puerto La Cruz, Anzoátegui", hours: "Lunes a Sábado 09:00 - 17:30" },
          { name: "Oficina Comercial Movilnet Las Américas Maracay", lat: 10.2520, lon: -67.5920, addr: "CC Las Américas, Maracay, Aragua", hours: "Lunes a Sábado 10:00 - 18:00" },
          { name: "Oficina Comercial Movilnet Sambil San Cristóbal", lat: 7.7850, lon: -72.2150, addr: "CC Sambil San Cristóbal, Táchira", hours: "Lunes a Sábado 10:00 - 18:00" }
        ];

        function calcDistKm(lat1, lon1, lat2, lon2) {
          const R = 6371.0;
          const dLat = (lat2 - lat1) * Math.PI / 180.0;
          const dLon = (lon2 - lon1) * Math.PI / 180.0;
          const a = Math.sin(dLat/2)*Math.sin(dLat/2) + Math.cos(lat1*Math.PI/180.0)*Math.cos(lat2*Math.PI/180.0)*Math.sin(dLon/2)*Math.sin(dLon/2);
          return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        }

        let nearest = offices[0];
        let minDist = calcDistKm(userLat, userLon, offices[0].lat, offices[0].lon);
        for (let i = 1; i < offices.length; i++) {
          const d = calcDistKm(userLat, userLon, offices[i].lat, offices[i].lon);
          if (d < minDist) {
            minDist = d;
            nearest = offices[i];
          }
        }

        const distFmt = minDist < 1 ? `${Math.round(minDist * 1000)} metros` : `${minDist.toFixed(1)} km`;
        const walkMin = Math.max(1, Math.round((minDist * 1000) / 80));
        const driveMin = Math.max(1, Math.round((minDist * 1000) / 500));
        const gmaps = `https://www.google.com/maps/dir/?api=1&destination=${nearest.lat},${nearest.lon}`;

        if (isCompetitor) {
          replyText = `📍 *Agencia Movilnet más cercana a tu ubicación (${distFmt}):*\\n` +
                      `*(Atención a clientes ${competitorLabel} - Portabilidad 4GMAX)*\\n\\n` +
                      `🏢 *${nearest.name}*\\n` +
                      `📫 *Dirección:* ${nearest.addr}\\n` +
                      `⏰ *Horario:* ${nearest.hours}\\n` +
                      `🚶‍♂️ *A pie:* ~${walkMin} min | 🚗 *En vehículo:* ~${driveMin} min\\n\\n` +
                      `🎁 *Trámites disponibles:* Portabilidad presencial a Movilnet 4GMAX, entrega de chip SIM físico gratuito y bono de 10 GB de bienvenida.\\n\\n` +
                      `🗺️ *Ruta en Google Maps:*\\n${gmaps}`;
        } else {
          replyText = `📍 *Agencia Movilnet más cercana a tu ubicación (${distFmt}):*\\n\\n` +
                      `🏢 *${nearest.name}*\\n` +
                      `📫 *Dirección:* ${nearest.addr}\\n` +
                      `⏰ *Horario:* ${nearest.hours}\\n` +
                      `🚶‍♂️ *A pie:* ~${walkMin} min | 🚗 *En vehículo:* ~${driveMin} min\\n\\n` +
                      `📋 *Trámites disponibles:* Reposición de SIM 4GMAX, migración de planes, soporte técnico, actualización de contrato y recargas C2P.\\n\\n` +
                      `🗺️ *Ruta en Google Maps:*\\n${gmaps}`;
        }
      }
    } else {
      const textLow = cleanMsg.toLowerCase();
      let matchedOffices = [];
      if (/valencia|carabobo|naguanagua|san diego/.test(textLow)) {
        matchedOffices = [
          { name: "Oficina Comercial Movilnet Metrópolis Valencia", addr: "CC Metrópolis, Nivel Sol, San Diego / Valencia", hours: "Lunes a Sábado 10:00 - 18:30", lat: 10.1980, lon: -67.9540 },
          { name: "Oficina Comercial Movilnet Sambil Valencia", addr: "CC Sambil Valencia, Naguanagua", hours: "Lunes a Sábado 10:00 - 19:00", lat: 10.2330, lon: -67.9890 }
        ];
      } else if (/maracaibo|zulia/.test(textLow)) {
        matchedOffices = [
          { name: "Oficina Comercial Movilnet Maracaibo 5 de Julio", addr: "Calle 77 (5 de Julio) con Av. 15 Delicias, Maracaibo", hours: "Lunes a Viernes 08:30 - 16:30", lat: 10.6680, lon: -71.6180 },
          { name: "Oficina Comercial Movilnet Lago Mall Maracaibo", addr: "CC Lago Mall, Nivel Avenida, Maracaibo", hours: "Lunes a Sábado 10:00 - 18:00", lat: 10.6800, lon: -71.6020 }
        ];
      } else if (/barquisimeto|lara/.test(textLow)) {
        matchedOffices = [
          { name: "Oficina Comercial Movilnet Las Trinitarias Barquisimeto", addr: "CC Las Trinitarias, Barquisimeto", hours: "Lunes a Sábado 09:30 - 18:00", lat: 10.0760, lon: -69.2880 }
        ];
      } else if (/puerto la cruz|lecheria|barcelona|anzoategui/.test(textLow)) {
        matchedOffices = [
          { name: "Oficina Comercial Movilnet Plaza Mayor Puerto La Cruz", addr: "CC Plaza Mayor, Nivel PB, Lechería / Puerto La Cruz", hours: "Lunes a Sábado 09:00 - 17:30", lat: 10.1950, lon: -64.6750 }
        ];
      } else if (/maracay|aragua/.test(textLow)) {
        matchedOffices = [
          { name: "Oficina Comercial Movilnet Las Américas Maracay", addr: "CC Las Américas, Nivel 1, Maracay", hours: "Lunes a Sábado 10:00 - 18:00", lat: 10.2520, lon: -67.5920 }
        ];
      } else if (/san cristobal|tachira/.test(textLow)) {
        matchedOffices = [
          { name: "Oficina Comercial Movilnet Sambil San Cristóbal", addr: "CC Sambil San Cristóbal, Nivel Río", hours: "Lunes a Sábado 10:00 - 18:00", lat: 7.7850, lon: -72.2150 }
        ];
      } else if (/caracas|chacao|candelaria|recreo|rosal|miranda|distrito capital/.test(textLow)) {
        matchedOffices = [
          { name: "Oficina Comercial Movilnet Centro Plaza", addr: "CC Centro Plaza, Nivel 3, Los Palos Grandes, Chacao", hours: "Lunes a Sábado 09:00 - 17:00", lat: 10.4960, lon: -66.8525 },
          { name: "Oficina Comercial Movilnet Torre El Rosal (Sede Principal)", addr: "Av. Venezuela, Torre Movilnet, El Rosal, Chacao", hours: "Lunes a Viernes 08:00 - 16:30", lat: 10.4890, lon: -66.8670 },
          { name: "Oficina Comercial Movilnet Sambil Chacao", addr: "CC Sambil Chacao, Nivel Autopista, Chacao", hours: "Lunes a Domingo 10:00 - 19:00", lat: 10.4905, lon: -66.8580 },
          { name: "Oficina Comercial Movilnet Sambil La Candelaria", addr: "CC Sambil La Candelaria, Nivel Andrés Bello", hours: "Lunes a Sábado 10:00 - 18:30", lat: 10.5050, lon: -66.9040 },
          { name: "Oficina Comercial Movilnet El Recreo", addr: "CC El Recreo, Nivel C2, Sabana Grande", hours: "Lunes a Sábado 10:00 - 18:00", lat: 10.4920, lon: -66.8770 }
        ];
      }

      if (matchedOffices.length > 0) {
        replyText = `📍 *Oficinas Comerciales Movilnet encontradas en tu zona:*\\n\\n`;
        for (let i = 0; i < matchedOffices.length; i++) {
          const o = matchedOffices[i];
          const gmaps = `https://www.google.com/maps/dir/?api=1&destination=${o.lat},${o.lon}`;
          replyText += `${i + 1}. 🏢 *${o.name}*\\n` +
                       `   📫 ${o.addr}\\n` +
                       `   ⏰ ${o.hours}\\n` +
                       `   🗺️ Ruta: ${gmaps}\\n\\n`;
        }
        if (isCompetitor) {
          replyText += `🎁 ¡Visítanos y activa tu Portabilidad a Movilnet 4GMAX con 10GB de bono de bienvenida gratis!`;
        } else {
          replyText += `✨ Recuerda llevar tu Cédula laminada para reposición de chip o gestiones de contrato.`;
        }
      } else {
        replyText = `📍 *Localizador de Oficinas Comerciales y Agencias Movilnet 4GMAX*\\n\\n` +
                    `Para indicarte con precisión la agencia más cercana a ti y su ruta en Google Maps, indícanos:\\n\\n` +
                    `1. 📍 *Comparte tu ubicación actual por WhatsApp:* Presiona el botón de adjuntar (📎 o +) y selecciona *'Ubicación'* -> *'Enviar mi ubicación actual'*.\\n` +
                    `2. ✍️ *O dinos en qué ciudad o zona estás:* Ejemplos: *'Oficinas en Caracas'*, *'Agencias en Valencia'*, *'Maracaibo'*, *'Barquisimeto'*, *'Puerto La Cruz'*.\\n\\n` +
                    `Te responderemos al instante con la dirección exacta, horarios y cómo llegar. 📶`;
    }
"""
        if "// CASO GEO: LOCALIZADOR DE OFICINAS" not in current_js:
            updated_js = current_js.replace(
                "  // CASO A: CONSULTA DE SALDO, DEUDA, BALANCE O CORTE\n  if (/saldo",
                geo_block + "\n  // CASO A: CONSULTA DE SALDO, DEUDA, BALANCE O CORTE\n  } else if (/saldo"
            )
            router_code["parameters"]["jsCode"] = updated_js

    # Guardar workflow actualizado
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)

    print(f"✅ [N8N_WORKFLOW]: Workflow actualizado exitosamente con soporte Geoespacial en {file_path}")
    return True


if __name__ == "__main__":
    update_n8n_workflow()
