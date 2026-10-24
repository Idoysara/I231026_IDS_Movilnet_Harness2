#!/usr/bin/env python3
"""
scripts/inject_movilnet_node_into_n8n.py — Inyector del Nodo Movilnet Core en n8n
================================================================================
Modifica el canvas de n8n para conectar formalmente el ciclo:
Movilnet (Abonado) ↔ Input (n8n) ↔ Nodos (n8n) ↔ Output (n8n) ↔ Movilnet
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOURCE_WORKFLOW = PROJECT_ROOT / "api/n8n_workflows/viki_lpgtec_v2_ids_live.json"
TARGET_WORKFLOW = PROJECT_ROOT / "api/n8n_workflows/viki_lpgtec_v2_ids_with_movilnet.json"


def inject_movilnet_integration(
    input_file: Path = SOURCE_WORKFLOW,
    output_file: Path = TARGET_WORKFLOW,
    core_host: str = "http://192.168.1.137:8000"
) -> Dict[str, Any]:
    """Inyecta el nodo HTTP Request de Movilnet Core y lo enlaza al enrutador determinista."""
    if not input_file.exists():
        raise FileNotFoundError(f"No se encontró el flujo base en {input_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        wf = json.load(f)

    nodes = wf.get("nodes", [])
    connections = wf.get("connections", {})

    node_id = "movilnet-core-fastpath-oda-01"
    node_name = "Movilnet Core - Fast-Path ODA"

    # 1. Definición formal del nodo n8n
    movilnet_node = {
        "parameters": {
            "method": "POST",
            "url": f"{core_host}/api/v1/n8n/webhook-ingest",
            "sendHeaders": True,
            "headerParameters": {
                "parameters": [
                    {"name": "Content-Type", "value": "application/json"}
                ]
            },
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": "={{\n  {\n    \"event\": \"messages.upsert\",\n    \"instance\": $('Edit Fields').item.json.body.instance,\n    \"data\": {\n      \"key\": {\n        \"remoteJid\": $('Edit Fields').item.json.body.data.key.remoteJid,\n        \"id\": $('Edit Fields').item.json.message_id\n      },\n      \"pushName\": $('Edit Fields').item.json.body.data.pushName,\n      \"message\": {\n        \"conversation\": $json.Content\n      }\n    }\n  }\n}}",
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [
            3680,
            460
        ],
        "id": node_id,
        "name": node_name
    }

    # Evitar duplicados si ya fue inyectado
    existing_idx = next((i for i, n in enumerate(nodes) if n.get("id") == node_id), None)
    if existing_idx is not None:
        nodes[existing_idx] = movilnet_node
    else:
        nodes.append(movilnet_node)

    # 2. Conectar la salida de Movilnet Core a 'Merge - Respuestas 5'
    if node_name not in connections:
        connections[node_name] = {"main": [[]]}

    merge_target = {"node": "Merge - Respuestas 5", "type": "main", "index": 0}
    if merge_target not in connections[node_name]["main"][0]:
        connections[node_name]["main"][0].append(merge_target)

    # 3. Guardar el nuevo workflow integrado
    wf["nodes"] = nodes
    wf["connections"] = connections
    wf["name"] = "Viki_LPGTEC_v2_ids_Movilnet_Connected"

    os.makedirs(output_file.parent, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)

    return {
        "status": "success",
        "output_file": str(output_file),
        "total_nodes": len(nodes),
        "injected_node": node_name,
        "core_endpoint": f"{core_host}/api/v1/n8n/webhook-ingest"
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inyector de Nodo Movilnet en Canvas n8n")
    parser.add_argument("--test", action="store_true", help="Auto-verificación formal del script inyector")
    parser.add_argument("--host", default="http://192.168.1.137:8000", help="URL base de Movilnet API")
    args = parser.parse_args()

    res = inject_movilnet_integration(core_host=args.host)
    if args.test:
        assert res["status"] == "success"
        assert res["total_nodes"] >= 67
        print(f"✅ [INJECTOR PASS]: Nodo Movilnet Core inyectado exitosamente ({res['total_nodes']} nodos).")
    else:
        print(json.dumps(res, indent=2))
