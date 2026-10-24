#!/usr/bin/env python3
"""
scripts/apply_ai_agent_circuit_breaker.py — Configuración de Resiliencia en AI Agent (n8n Cloud)
=================================================================================================
Configura Continue On Fail = True, Retry On Fail = 2 (maxTries=3), waitBetweenTries=1000ms
en el nodo 'AI Agent' del workflow sNMbtiEiTkuQ9OCY.
"""

import os
import sys
import json
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

def get_n8n_creds():
    api_key = None
    base_url = "https://n8n.lpgtec.net"
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("N8N_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                elif line.startswith("N8N_BASE_URL="):
                    base_url = line.split("=", 1)[1].strip()
    return base_url, api_key

def main():
    base_url, api_key = get_n8n_creds()
    if not api_key:
        print("ERROR: N8N_API_KEY no encontrada en .env")
        sys.exit(1)

    wf_id = "sNMbtiEiTkuQ9OCY"
    headers = {
        "X-N8N-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    # 1. Obtener workflow actual
    get_url = f"{base_url}/api/v1/workflows/{wf_id}"
    req = urllib.request.Request(get_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        wf_data = json.loads(resp.read().decode())

    print(f"Workflow recuperado: {wf_data.get('name')} (ID: {wf_id})")

    # 2. Modificar nodo AI Agent
    ai_agent_found = False
    for node in wf_data.get("nodes", []):
        if node.get("name") == "AI Agent":
            ai_agent_found = True
            node["onError"] = "continueRegularOutput"
            node["retryOnFail"] = True
            node["maxTries"] = 3
            node["waitBetweenTries"] = 1000
            print(f"Modificado nodo '{node['name']}': onError={node['onError']}, retryOnFail={node['retryOnFail']}, maxTries={node['maxTries']}")
            break

    if not ai_agent_found:
        print("ERROR: Nodo 'AI Agent' no encontrado en el workflow.")
        sys.exit(1)

    # 3. Preparar payload de actualización para n8n REST API
    # n8n espera: { "name": ..., "nodes": ..., "connections": ..., "settings": ... }
    update_payload = {
        "name": wf_data.get("name"),
        "nodes": wf_data.get("nodes"),
        "connections": wf_data.get("connections"),
        "settings": wf_data.get("settings", {})
    }

    req_put = urllib.request.Request(
        get_url,
        data=json.dumps(update_payload).encode("utf-8"),
        headers=headers,
        method="PUT"
    )

    with urllib.request.urlopen(req_put) as resp:
        result = json.loads(resp.read().decode())
        print(f"✅ Workflow actualizado exitosamente: {result.get('name')}")
        # Verificar
        updated_agent = next((n for n in result.get("nodes", []) if n.get("name") == "AI Agent"), None)
        if updated_agent:
            print("Verificación de nodo 'AI Agent':")
            print(f"  onError: {updated_agent.get('onError')}")
            print(f"  retryOnFail: {updated_agent.get('retryOnFail')}")
            print(f"  maxTries: {updated_agent.get('maxTries')}")
            print(f"  waitBetweenTries: {updated_agent.get('waitBetweenTries')}")

if __name__ == "__main__":
    main()
