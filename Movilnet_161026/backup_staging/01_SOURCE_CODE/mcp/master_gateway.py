#!/usr/bin/env python3
"""
mcp/master_gateway.py — Pasarela Maestra Unificada de Servidores MCP Movilnet
=============================================================================
Proyecto: AI_Movilnet_300926 / Antigravity Level 5 Architecture
Estándar: Model Context Protocol (MCP) JSON-RPC 2.0 (Especificación 2024-11-05)

Integra las 5 Suites Especializadas:
  1. Suite 1: mcp_telco_tools (Core Telecom, OSS/BSS, Radiobases, Saldo, SIM-Swap)
  2. Suite 2: mcp_fintech_c2p (Pasarela Financiera, Tasas BCV, Cobro C2P, Antifraude)
  3. Suite 3: mcp_crm_retention (CRM, Prevención de Churn, TM Forum TMF620/TMF680)
  4. Suite 4: mcp_privacy_guard (Privacidad CONATEL, PII Sanitizer LATAM & Bóveda)
  5. Suite 5: mcp_omnichannel_whatsapp (Meta Cloud API, Botones, Listas, n8n Bridge)
"""

from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.telco_tools import TelcoMcpServer
from mcp.fintech_tools import FintechMcpServer
from mcp.crm_tools import CrmRetentionMcpServer
from mcp.privacy_tools import PrivacyGuardMcpServer
from mcp.whatsapp_tools import WhatsAppMcpServer
from mcp.geo_tools import GeoVenezuelaMcpServer


class MovilnetMasterMcpGateway:
    """Pasarela unificada que enruta peticiones MCP hacia cualquiera de las 6 suites."""

    def __init__(self):
        self.telco_suite = TelcoMcpServer()
        self.fintech_suite = FintechMcpServer()
        self.crm_suite = CrmRetentionMcpServer()
        self.privacy_suite = PrivacyGuardMcpServer()
        self.whatsapp_suite = WhatsAppMcpServer()
        self.geo_suite = GeoVenezuelaMcpServer()

        # Mapa de métodos hacia suites
        self.routing_table: Dict[str, Any] = {}
        for tool_name in self.telco_suite.TOOLS:
            self.routing_table[tool_name] = self.telco_suite
        for tool_name in self.fintech_suite.TOOLS:
            self.routing_table[tool_name] = self.fintech_suite
        for tool_name in self.crm_suite.TOOLS:
            self.routing_table[tool_name] = self.crm_suite
        for tool_name in self.privacy_suite.TOOLS:
            self.routing_table[tool_name] = self.privacy_suite
        for tool_name in self.whatsapp_suite.TOOLS:
            self.routing_table[tool_name] = self.whatsapp_suite
        for tool_name in self.geo_suite.TOOLS:
            self.routing_table[tool_name] = self.geo_suite

    def list_all_tools(self) -> List[Dict[str, Any]]:
        """Retorna el catálogo unificado de herramientas de las 6 suites."""
        catalog = []
        catalog.extend(self.telco_suite.get_manifest())
        catalog.extend(self.fintech_suite.get_manifest())
        catalog.extend(self.crm_suite.get_manifest())
        catalog.extend(self.privacy_suite.get_manifest())
        catalog.extend(self.whatsapp_suite.get_manifest())
        catalog.extend(self.geo_suite.get_manifest())
        return catalog

    def dispatch(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Any = 1) -> Dict[str, Any]:
        """Despacha la petición a la suite correspondiente."""
        params = params or {}
        suite = self.routing_table.get(method)
        if not suite:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found across any of the 5 Movilnet MCP Suites."
                },
                "id": request_id
            }

        return suite.handle_request(method, params, request_id)

    def handle_mcp_protocol(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Maneja el protocolo estándar MCP (initialize, tools/list, tools/call)."""
        rpc_method = payload.get("method")
        rpc_id = payload.get("id", 1)
        params = payload.get("params", {})

        if rpc_method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "movilnet-master-mcp-gateway",
                        "version": "1.0.0",
                        "architecture": "Antigravity Level 5 Swarm"
                    },
                    "capabilities": {"tools": {}}
                },
                "id": rpc_id
            }

        elif rpc_method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": self.list_all_tools()
                },
                "id": rpc_id
            }

        elif rpc_method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            return self.dispatch(tool_name, tool_args, rpc_id)

        else:
            # Despacho directo por nombre de método
            return self.dispatch(rpc_method, params, rpc_id)


def main():
    gateway = MovilnetMasterMcpGateway()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd in ["--manifest", "-m"]:
            tools = gateway.list_all_tools()
            print(json.dumps({"total_tools": len(tools), "tools": tools}, indent=2, ensure_ascii=False))
            return
        elif cmd in ["--call", "-c"] and len(sys.argv) > 2:
            tool_name = sys.argv[2]
            args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
            res = gateway.dispatch(tool_name, args)
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return

    # Modo Stdio / Interactivo
    print("=" * 70)
    print("🚀 PASARELA MAESTRA MCP MOVILNET (5 SUITES UNIFICADAS)")
    print(f"📦 Total de Herramientas Registradas: {len(gateway.routing_table)}")
    print("=" * 70)
    for suite_name, count in [
        ("Suite 1: Core Telecom", len(gateway.telco_suite.TOOLS)),
        ("Suite 2: Fintech C2P & BCV", len(gateway.fintech_suite.TOOLS)),
        ("Suite 3: CRM & Churn TM Forum", len(gateway.crm_suite.TOOLS)),
        ("Suite 4: Privacidad & PII LATAM", len(gateway.privacy_suite.TOOLS)),
        ("Suite 5: Omnicanal WhatsApp Meta", len(gateway.whatsapp_suite.TOOLS)),
    ]:
        print(f"  • {suite_name}: {count} herramientas disponibles")
    print("=" * 70)


if __name__ == "__main__":
    main()
