#!/usr/bin/env python3
"""
scripts/fix_n8n_characters_and_encoding.py
=========================================
Sanea los caracteres conflictivos en el flujo n8n en producción:
1. Corrige la URL del nodo 'HTTP Request' agregando encodeURIComponent() para
   evitar el error 'Bad request - please check your parameters' por espacios en blanco.
2. Sanea el texto de salida:
   - Convierte saltos literales escapados (\\n) a saltos de línea reales.
   - Reemplaza viñetas no nativas (•) por guiones estándar (- ) de WhatsApp.
   - Desactiva linkPreview tanto a nivel raíz como dentro de options para erradicar
     el cuadro negro con botón de reproducción (tarjeta falsa de previsualización).
3. Publica la actualización directamente a n8n API y verifica la respuesta.
"""

import json
import urllib.request
import urllib.error

N8N_URL = "https://n8n.lpgtec.net/api/v1/workflows/sNMbtiEiTkuQ9OCY"
N8N_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4YTIxZmVjNC1iMGI3LTQ4ODEtODdmNS1lZTU5YTQxMTYyMTUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZjhhMWE1NmQtY2JkYi00MjM1LThmNDctMGM1ZjM5NzQzOTAzIiwiaWF0IjoxNzkxMjQyMzMyLCJleHAiOjE3OTg5NDg4MDB9.q6HiXqDygN5FSHwQ36Phmief0XACLJcwuFObdj-3MnM"

def fetch_workflow():
    req = urllib.request.Request(
        N8N_URL,
        headers={
            "X-N8N-API-KEY": N8N_KEY,
            "User-Agent": "Mozilla/5.0"
        }
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def update_workflow(wf_payload):
    data_bytes = json.dumps(wf_payload).encode("utf-8")
    req = urllib.request.Request(
        N8N_URL,
        data=data_bytes,
        headers={
            "X-N8N-API-KEY": N8N_KEY,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        },
        method="PUT"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print("🚀 [1/3] Descargando workflow activo de n8n...")
    wf = fetch_workflow()

    http_req = next((n for n in wf["nodes"] if n["name"] == "HTTP Request"), None)
    if not http_req:
        print("❌ Nodo HTTP Request no encontrado.")
        return

    print("🔧 [2/3] Aplicando corrección quirúrgica a 'HTTP Request'...")
    # 1. URL con encodeURIComponent para evitar error 400 por espacios en la instancia
    http_req["parameters"]["url"] = (
        "={{ ($('Webhook').item.json.body.server_url || 'http://evolution:8080') }}/message/sendText/"
        "{{ encodeURIComponent($('Edit Fields').item.json.body.instance || $('Webhook').item.json.body.instance || 'Viki LPGTEC') }}"
    )

    # 2. Body con sanitización de caracteres (\n literales, viñetas •, y linkPreview forzado a false)
    http_req["parameters"]["body"] = (
        "={{\n"
        "  (() => {\n"
        "    // 1. Obtener payload entrante del Webhook\n"
        "    const wh = $('Webhook').item.json.body || {};\n"
        "    const whData = Array.isArray(wh.data) ? wh.data[0] : (wh.data || {});\n"
        "    const key = whData.key || {};\n\n"
        "    // 2. Extraer JID dinámico del usuario entrante\n"
        "    let jid = key.remoteJid || whData.remoteJid || wh.sender || ($('Edit Fields').item.json.body && $('Edit Fields').item.json.body.phone) || '';\n"
        "    const altJid = key.remoteJidAlt || '';\n\n"
        "    if (jid.endsWith('@lid')) {\n"
        "      if (altJid && !altJid.endsWith('@lid')) {\n"
        "        jid = altJid;\n"
        "      } else if (whData.participant && !whData.participant.endsWith('@lid')) {\n"
        "        jid = whData.participant;\n"
        "      }\n"
        "    }\n\n"
        "    // 3. Sanitizar a dígitos puros E.164\n"
        "    let cleanNum = jid.replace(/@.*/, '').replace(/\\D/g, '');\n\n"
        "    // 4. Normalizar formato nacional venezolano (04XX -> 584XX)\n"
        "    if (cleanNum.startsWith('04') && cleanNum.length === 11) {\n"
        "      cleanNum = '58' + cleanNum.slice(1);\n"
        "    }\n\n"
        "    // 5. GUARDARRAÍL: La única línea bot es +58 424 153 3712 (evitar bucle)\n"
        "    const OFFICIAL_BOT_NUMBERS = ['584241533712', '04241533712'];\n"
        "    if (!cleanNum || OFFICIAL_BOT_NUMBERS.includes(cleanNum) || cleanNum.length < 10) {\n"
        "      if ($json.carrier_phone && !OFFICIAL_BOT_NUMBERS.includes($json.carrier_phone.replace(/\\D/g, '')) && $json.carrier_phone.replace(/\\D/g, '').length >= 10) {\n"
        "        cleanNum = $json.carrier_phone.replace(/\\D/g, '');\n"
        "        if (cleanNum.startsWith('04') && cleanNum.length === 11) cleanNum = '58' + cleanNum.slice(1);\n"
        "      } else if (wh.data && wh.data.key && wh.data.key.remoteJid && !OFFICIAL_BOT_NUMBERS.includes(wh.data.key.remoteJid.replace(/\\D/g, ''))) {\n"
        "        cleanNum = wh.data.key.remoteJid.replace(/@.*/, '').replace(/\\D/g, '');\n"
        "        if (cleanNum.startsWith('04') && cleanNum.length === 11) cleanNum = '58' + cleanNum.slice(1);\n"
        "      }\n"
        "    }\n\n"
        "    // 6. Sanitizar texto: convertir \\n literales a saltos de línea reales y viñetas • a '- '\n"
        "    let sendText = ($json.final_text || $json.output || 'Estimado abonado, su consulta fue recibida.');\n"
        "    sendText = String(sendText).replace(/\\\\n/g, '\\n').replace(/•\\s*/g, '- ');\n\n"
        "    // 7. Retornar payload estricto para Evolution API con linkPreview: false\n"
        "    return JSON.stringify({\n"
        "      \"number\": cleanNum,\n"
        "      \"text\": sendText,\n"
        "      \"linkPreview\": false,\n"
        "      \"options\": {\n"
        "        \"delay\": ($json.human_delay_ms || 1200),\n"
        "        \"presence\": \"composing\",\n"
        "        \"linkPreview\": false\n"
        "      }\n"
        "    });\n"
        "  })()\n"
        "}}"
    )

    allowed_settings = [
        'executionOrder', 'timezone', 'saveExecutionProgress',
        'saveManualExecutions', 'saveDataErrorExecution',
        'saveDataSuccessExecution', 'executionTimeout', 'errorWorkflow'
    ]
    clean_settings = {k: v for k, v in wf.get("settings", {}).items() if k in allowed_settings}

    clean_payload = {
        "name": wf.get("name"),
        "nodes": wf.get("nodes"),
        "connections": wf.get("connections"),
        "settings": clean_settings
    }

    print("📤 [3/3] Desplegando workflow saneado a producción...")
    res = update_workflow(clean_payload)
    print(f"✅ Workflow actualizado exitosamente: {res.get('updatedAt')}")
    print("🏆 Sanitización completada: URL codificada, saltos normalizados y tarjetas falsas erradicadas.")

if __name__ == "__main__":
    main()
