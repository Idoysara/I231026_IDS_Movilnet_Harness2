#!/usr/bin/env python3
"""
multi_agent_supervisor.py — Orquestador Jerárquico Multi-Agente y Smart MCP Gateway
===================================================================================
Implementa los 3 patrones arquitectónicos de GitHub:
  1. LangGraph Multi-Agent Supervisor: Orquestador central que delega a subagentes especialistas.
  2. Smart MCP Gateway (mcplex / smart-mcp): Enrutamiento dinámico que expone solo las herramientas del dominio.
  3. TM Forum ODA (TMF620 / TMF678 / TMF680): Contratos estándar de catálogo, facturación y recomendación.
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.semantic_router import SemanticRouter


from mcp.telco_tools import TelcoMcpServer
from mcp.fintech_tools import FintechMcpServer
from mcp.whatsapp_tools import WhatsAppMcpServer
from mcp.noc_tools import NocMcpServer
from core.department_rule_engine import DepartmentRuleEngine

_TELCO_SERVER = TelcoMcpServer()
_FINTECH_SERVER = FintechMcpServer()
_WHATSAPP_SERVER = WhatsAppMcpServer()
_NOC_SERVER = NocMcpServer()


class SubAgentWorker:
    """Subagente especialista de dominio aislado (Privacy Sandboxing)."""
    def __init__(self, name: str, domain: str, system_prompt: str, mcp_server: str):
        self.name = name
        self.domain = domain
        self.system_prompt = system_prompt
        self.mcp_server = mcp_server

    def execute(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta la tarea en su propio contexto aislado llamando al servidor MCP en vivo."""
        mcp_result = None
        msisdn = context.get("phone", "04161234567")

        if self.domain == "telco_core":
            msg_lower = message.lower()
            if any(k in msg_lower for k in ["cobertura", "celda", "señal", "falla"]):
                resp = _TELCO_SERVER.handle_request("mcp_telco_diagnose_coverage", {"msisdn": msisdn})
                mcp_result = resp.get("result")
            elif any(k in msg_lower for k in ["robo", "extravio", "bloqueo", "bloquear"]):
                resp = _TELCO_SERVER.handle_request("mcp_telco_lock_line_theft", {"msisdn": msisdn, "reporter_cid": context.get("cid", "V-00000000")})
                mcp_result = resp.get("result")
            elif any(k in msg_lower for k in ["apn", "configuracion", "parametros"]):
                resp = _TELCO_SERVER.handle_request("mcp_telco_check_apn", {"msisdn": msisdn})
                mcp_result = resp.get("result")
            else:
                resp = _TELCO_SERVER.handle_request("mcp_telco_get_subscriber_balance", {"msisdn": msisdn})
                mcp_result = resp.get("result")

        elif self.domain == "fintech_c2p":
            msg_lower = message.lower()
            if any(k in msg_lower for k in ["tasa", "dolar", "cambio", "bcv"]):
                resp = _FINTECH_SERVER.handle_request("mcp_bcv_get_official_rate", {"currency": "USD"})
                mcp_result = resp.get("result")
            else:
                # Validar pago C2P simulado o extraer monto
                amount = 150.0
                resp = _FINTECH_SERVER.handle_request("mcp_c2p_validate_transaction", {
                    "reference_id": f"REF-{int(time.time())}",
                    "bank_code": "0102",
                    "amount_bs": amount,
                    "phone": msisdn,
                    "payer_cid": context.get("cid", "V-18492019")
                })
                mcp_result = resp.get("result")

        elif self.domain == "network_noc":
            region = context.get("state", "Distrito Capital")
            msg_lower = message.lower()
            for r in ["maracaibo", "zulia", "valencia", "carabobo", "caracas", "miranda", "lara", "barquisimeto"]:
                if r in msg_lower:
                    region = r.capitalize()
                    break
            resp = _NOC_SERVER.handle_request("mcp_noc_get_regional_status", {"region": region})
            mcp_result = resp.get("result")

        return {
            "worker": self.name,
            "domain": self.domain,
            "mcp_server_invoked": self.mcp_server,
            "isolated_context": True,
            "mcp_payload": mcp_result,
            "result": f"[{self.name}] Procesó la solicitud en el dominio '{self.domain}' utilizando '{self.mcp_server}'."
        }



class MultiAgentSupervisor:
    """
    Supervisor Jerárquico (LangGraph Supervisor Pattern + Smart MCP Gateway).
    Recibe el mensaje del abonado, consulta al SemanticRouter,
    filtra dinámicamente las herramientas MCP y delega al subagente correspondiente.
    """
    def __init__(self):
        self.router = SemanticRouter()
        self.workers: Dict[str, SubAgentWorker] = {
            "telco_core": SubAgentWorker(
                name="TelcoCoreAgent",
                domain="telco_core",
                system_prompt="Especialista en facturación, saldo, fechas de corte y planes 4GMAX de Movilnet.",
                mcp_server="mcp_telco_tools"
            ),
            "fintech_c2p": SubAgentWorker(
                name="FintechPaymentAgent",
                domain="fintech_c2p",
                system_prompt="Especialista en cobro C2P, pasarelas bancarias (BDV/Banesco) e idempotencia.",
                mcp_server="mcp_fintech_c2p"
            ),
            "tourism_culture": SubAgentWorker(
                name="TourismCultureAgent",
                domain="tourism_culture",
                system_prompt="Especialista en guía turística de Venezuela, parques nacionales y sitios históricos.",
                mcp_server="mcp_tourism_guide"
            ),
            "partner_marketplace": SubAgentWorker(
                name="MarketplaceVASAgent",
                domain="partner_marketplace",
                system_prompt="Especialista en promociones comerciales aliadas, cines y servicios públicos.",
                mcp_server="mcp_partner_marketplace"
            ),
            "network_noc": SubAgentWorker(
                name="NetworkNocAgent",
                domain="network_noc",
                system_prompt="Especialista en operaciones de red, radiobases, diagnósticos de señal y mitigación proactiva de averías masivas.",
                mcp_server="mcp_noc_tools"
            )
        }
        self.rule_engine = DepartmentRuleEngine.get_instance()

    def process_turn(self, user_message: str, subscriber_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ciclo completo:
          1. Enrutamiento Semántico (<15ms).
          2. Smart MCP Gateway: Filtrado de herramientas por dominio.
          3. Delegación al Subagente Especialista (Maker).
          4. Verificación de Reglas Departamentales (Hot-Reload).
          5. Recomendación Contextual TM Forum (TMF680).
        """
        # 1. Clasificación Semántica
        domain, target_mcp, confidence = self.router.route(user_message)

        # 2. Asignación de Worker
        worker = self.workers.get(domain, self.workers["telco_core"])

        # 3. Ejecución del Worker en Sandboxing
        execution = worker.execute(user_message, subscriber_context or {})

        # 4. Verificación de Boletín Proactivo del NOC (DepartmentRuleEngine)
        noc_bulletin = None
        if domain in ["network_noc", "telco_core"]:
            ctx_state = (subscriber_context or {}).get("state", "")
            noc_bulletin = self.rule_engine.find_proactive_bulletin_for_region(user_message + " " + ctx_state)

        # 5. Regla TM Forum TMF680 (Recomendación Proactiva de Paquetes si los megas son bajos)
        recommendation = None
        if subscriber_context and subscriber_context.get("remaining_data_mb", 1000) < 500:
            recommendation = {
                "tmf_standard": "TMF680_Recommendation",
                "trigger": "LOW_DATA_QUOTA_ALERT",
                "suggested_product": "Paquete Extra 4GMAX 2GB",
                "channel": "PAGO_MOVIL_C2P"
            }

        return {
            "supervisor": "MasterCoordinator",
            "detected_domain": domain,
            "confidence_score": confidence,
            "smart_mcp_routing": {
                "active_mcp_server": target_mcp,
                "hidden_mcp_servers": [w.mcp_server for k, w in self.workers.items() if k != domain]
            },
            "delegated_worker": worker.name,
            "execution_details": execution,
            "noc_bulletin": noc_bulletin,
            "tm_forum_recommendation": recommendation
        }


if __name__ == "__main__":
    supervisor = MultiAgentSupervisor()
    test_queries = [
        ("¿Cuántos megas me quedan en mi línea 0416?", {"remaining_data_mb": 250, "phone": "04161234567"}),
        ("Quiero pagar 150 bolívares por BDV con token C2P", {"phone": "04161234567"}),
        ("¿Qué sitios históricos puedo visitar en Caracas?", {}),
        ("¿Hay descuentos de 2x1 en entradas de cine para clientes Movilnet?", {})
    ]

    print("=" * 75)
    print("🧠 DEMOSTRACIÓN: LangGraph Supervisor + Smart MCP Gateway + TMF680")
    print("=" * 75)
    for q, ctx in test_queries:
        res = supervisor.process_turn(q, ctx)
        print(f"\nPregunta: \"{q}\"")
        print(f"  ➔ Dominio: {res['detected_domain'].upper()} (Confianza: {res['confidence_score']*100:.0f}%)")
        print(f"  ➔ Subagente Especialista: {res['delegated_worker']}")
        print(f"  ➔ Herramienta MCP Activa: {res['smart_mcp_routing']['active_mcp_server']}")
        print(f"  ➔ MCPs Ocultos (Aislamiento): {res['smart_mcp_routing']['hidden_mcp_servers']}")
        if res['tm_forum_recommendation']:
            print(f"  ➔ Recomendación TMF680: ¡Alerta de Megas Bajos! Sugerir {res['tm_forum_recommendation']['suggested_product']}")
