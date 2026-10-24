#!/usr/bin/env python3
"""
scripts/fix_n8n_gemini_and_egress.py
====================================
Aplica el blindaje definitivo en el flujo de n8n Cloud (ID: sNMbtiEiTkuQ9OCY):
1. Actualiza 'Google Gemini Chat Model' a 'models/gemini-3.8-flash' con credencial 'Google Gemini PrePaid' (2LyFhAKm2IiUM6aT).
2. Configura 'onError': 'continueRegularOutput' en 'AI Agent' para evitar fallos catastróficos que detengan el flujo.
3. Actualiza nodos de transcripción, imagen y video a 'models/gemini-3.8-flash' con 'Google Gemini PrePaid'.
4. Actualiza 'HTTP Request' con resolución blindada E.164 (soporte LID @lid, fallback a Edit Fields y delay estocástico).
5. Sincroniza el JSON local y emite el payload listo para update_workflow.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def build_fixed_workflow(input_json_path: Path, output_json_path: Path) -> dict:
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    wf = data["workflow"] if "workflow" in data else data

    # 1. Google Gemini Chat Model
    gemini = next(n for n in wf["nodes"] if n["name"] == "Google Gemini Chat Model")
    gemini["parameters"]["modelName"] = "models/gemini-3.8-flash"
    gemini["credentials"] = {
        "googlePalmApi": {
            "id": "2LyFhAKm2IiUM6aT",
            "name": "Google Gemini PrePaid"
        }
    }

    # 2. AI Agent onError: continueRegularOutput
    ai_agent = next(n for n in wf["nodes"] if n["name"] == "AI Agent")
    ai_agent["onError"] = "continueRegularOutput"

    # 3. HTTP Request
    http_req = next(n for n in wf["nodes"] if n["name"] == "HTTP Request")
    http_req["onError"] = "continueRegularOutput"
    http_req["parameters"]["body"] = (
        "={{\n"
        "  (() => {\n"
        "    const wh = $('Webhook').item.json.body || {};\n"
        "    const whData = Array.isArray(wh.data) ? wh.data[0] : (wh.data || {});\n"
        "    const key = whData.key || {};\n"
        "    let jid = key.remoteJid || whData.remoteJid || ($('Edit Fields').item.json.body && $('Edit Fields').item.json.body.phone) || '';\n"
        "    const altJid = key.remoteJidAlt || '';\n"
        "    if (jid.endsWith('@lid') && altJid && !altJid.endsWith('@lid')) {\n"
        "      jid = altJid;\n"
        "    }\n"
        "    const cleanNum = jid.replace(/@.*/, '').replace(/\\D/g, '') || $json.carrier_phone || '';\n"
        "    return JSON.stringify({\n"
        '      "number": cleanNum,\n'
        '      "options": {\n'
        '        "delay": ($json.human_delay_ms || 1200),\n'
        '        "presence": "composing",\n'
        '        "linkPreview": false\n'
        "      },\n"
        '      "text": $json.final_text\n'
        "    });\n"
        "  })()\n"
        "}}"
    )

    # 4. Multimedia Gemini nodes
    for g_name in ["Transcribe a recording", "Analyze image", "Analyze video"]:
        node = next((n for n in wf["nodes"] if n["name"] == g_name), None)
        if node:
            if "modelId" in node.get("parameters", {}):
                node["parameters"]["modelId"]["value"] = "models/gemini-3.8-flash"
                node["parameters"]["modelId"]["cachedResultName"] = "models/gemini-3.8-flash"
            node["credentials"] = {
                "googlePalmApi": {
                    "id": "2LyFhAKm2IiUM6aT",
                    "name": "Google Gemini PrePaid"
                }
            }

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2)

    return wf

if __name__ == "__main__":
    src_file = Path("/Users/ismael/.gemini/antigravity/brain/b650e2a7-a3b8-4154-b697-ccd2006dfbc4/.system_generated/steps/2772/output.txt")
    dest_file = PROJECT_ROOT / "api" / "n8n_workflows" / "viki_lpgtec_v2_ids_with_google_suite.json"
    wf_fixed = build_fixed_workflow(src_file, dest_file)
    print(f"Workflow reparado con éxito: {len(wf_fixed['nodes'])} nodos guardados en {dest_file}")
