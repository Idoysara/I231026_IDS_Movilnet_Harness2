#!/usr/bin/env python3
"""
scripts/n8n_client.py — Cliente CLI Autónomo para Orquestación de n8n
=====================================================================
Proyecto: AI_Movilnet_300926 / Telecomunicaciones Movilnet C.A.

Permite a los ingenieros y agentes interactuar con la instancia n8n desde la terminal:
- Consultar estado y latencia
- Desplegar workflows pre-compilados
- Probar webhooks con datos sintéticos de prueba
"""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.n8n_tools import (
    mcp_n8n_status,
    mcp_n8n_list_workflows,
    mcp_n8n_deploy_workflow,
    mcp_n8n_trigger_webhook,
    N8N_BASE_URL
)


def main():
    parser = argparse.ArgumentParser(description="Cliente CLI n8n para Movilnet AI")
    parser.add_argument("--status", action="store_true", help="Verificar conectividad con la instancia n8n")
    parser.add_argument("--list", action="store_true", help="Listar workflows en n8n")
    parser.add_argument("--deploy", type=str, help="Ruta al archivo workflow JSON a desplegar")
    parser.add_argument("--activate", action="store_true", help="Activar workflow al desplegar")
    parser.add_argument("--test-webhook", type=str, help="Ruta del webhook a probar (ej: movilnet-whatsapp-webhook)")
    parser.add_argument("--payload", type=str, help="JSON payload para el webhook")

    args = parser.parse_args()

    if args.status:
        res = mcp_n8n_status()
        print("\n📊 ESTADO DE INSTANCIA N8N:")
        print(json.dumps(res, indent=2))
        return

    if args.list:
        res = mcp_n8n_list_workflows()
        print("\n📋 WORKFLOWS EN N8N:")
        print(json.dumps(res, indent=2))
        return

    if args.deploy:
        file_path = Path(args.deploy)
        if not file_path.exists():
            print(f"❌ Error: Archivo {file_path} no encontrado.")
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        res = mcp_n8n_deploy_workflow(data, activate=args.activate)
        print(f"\n🚀 RESULTADO DE DESPLIEGUE:")
        print(json.dumps(res, indent=2))
        return

    if args.test_webhook:
        payload = {"phone": "04161234567", "message": "Hola, consulta de saldo"}
        if args.payload:
            try:
                payload = json.loads(args.payload)
            except Exception as e:
                print(f"⚠️ Payload no es JSON válido, usando default: {e}")
        res = mcp_n8n_trigger_webhook(args.test_webhook, payload)
        print(f"\n⚡ RESPUESTA DE WEBHOOK:")
        print(json.dumps(res, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
