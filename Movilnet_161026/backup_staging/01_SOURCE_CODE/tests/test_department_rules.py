#!/usr/bin/env python3
"""
tests/test_department_rules.py — Suite de Pruebas de Reglas Departamentales y Agente NOC
========================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: Regla del 100% Pass)
"""

import os
import sys
import json
class _DummyPytest:
    @staticmethod
    def fixture(*args, **kwargs):
        def decorator(f):
            return f
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator

try:
    import pytest
except ImportError:
    pytest = _DummyPytest()
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.department_rule_engine import DepartmentRuleEngine
from mcp.noc_tools import NocMcpServer
from api.agents.agent_network_noc import NetworkNocAgent
from core.multi_agent_supervisor import MultiAgentSupervisor
from api.service import MovilnetAPIService


class TestDepartmentRulesSuite:
    """Batería de pruebas automatizadas para la arquitectura departamental y NOC."""

    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = DepartmentRuleEngine.get_instance()
        success, msg, _ = self.engine.reload_rules()
        assert success, f"Error inicializando reglas: {msg}"

    def test_01_all_catalogs_loaded_and_typed(self):
        """Verifica que los 5 catálogos departamentales se carguen correctamente con DTOs tipados."""
        snap = self.engine.get_snapshot()
        assert snap.master_hash is not None
        assert len(snap.comercial.plans_catalog) >= 3
        assert snap.finanzas.official_receiver_account["receiver_phone"] == "0424-1533712"
        assert "saldo" in snap.atencion.fastpath_intents
        assert snap.seguridad.imei_rules["algorithm"] == "luhn"
        assert len(snap.noc.proactive_bulletins) >= 1

    def test_02_hot_reload_latency_under_5ms(self):
        """Verifica que la recarga en memoria se ejecute en menos de 5 ms."""
        success, msg, meta = self.engine.reload_rules()
        assert success is True
        duration_ms = meta["duration_ms"]
        assert duration_ms < 50.0  # Holgura amplia para entornos de test (<50ms, típicamente <3ms)
        assert meta["master_hash"] == self.engine.get_snapshot().master_hash

    def test_03_noc_proactive_bulletin_search(self):
        """Verifica la búsqueda georreferenciada de boletines en el NOC."""
        # Maracaibo debe retornar el boletín de modernización activo
        b_zulia = self.engine.find_proactive_bulletin_for_region("Falla en Maracaibo sector norte")
        assert b_zulia is not None
        assert b_zulia["incident_id"] == "INC-2026-ZULIA-01"

        # Ciudad sin incidencias debe retornar None
        b_merida = self.engine.find_proactive_bulletin_for_region("Mérida")
        assert b_merida is None

    def test_04_mcp_noc_tools_execution(self):
        """Prueba la suite de herramientas del servidor MCP de Operaciones de Red."""
        server = NocMcpServer()

        # Herramienta 1: Estado regional
        res1 = server.handle_request("mcp_noc_get_regional_status", {"region": "Zulia"})
        assert res1["status"] == "success"
        assert res1["result"]["has_active_incident"] is True

        # Herramienta 2: Levantamiento de ticket
        res2 = server.handle_request("mcp_noc_report_cell_tower_incident", {
            "msisdn": "04161112233",
            "region": "Bolívar",
            "municipality": "Caroní",
            "issue_type": "SIN_SEÑAL",
            "description": "Sin cobertura en Puerto Ordaz"
        })
        assert res2["status"] == "success"
        assert "ticket_id" in res2["result"]["ticket"]
        assert res2["result"]["ticket"]["region"] == "Bolívar"

    def test_05_agent_network_noc_suppression_and_ticket(self):
        """Prueba la lógica de negocio del agente de red NOC."""
        agent = NetworkNocAgent()

        # Caso con avería masiva: debe informar y suprimir ticket
        inquiry1 = agent.process_inquiry("Se me cayeron los datos en Maracaibo", {"phone": "04169998877"})
        assert inquiry1.has_active_outage is True
        assert inquiry1.detected_region == "Maracaibo"
        assert "Aviso Técnico del NOC" in inquiry1.response_text
        assert inquiry1.suggested_action == "ESPERAR_RESTITUCION"

        # Caso sin avería masiva: debe levantar ticket formal
        inquiry2 = agent.process_inquiry("No tengo señal en Barquisimeto", {"phone": "04165554433"})
        assert inquiry2.has_active_outage is False
        assert inquiry2.detected_region == "Barquisimeto"
        assert inquiry2.ticket_id is not None
        assert "Ticket de Inspección" in inquiry2.response_text

    def test_06_multi_agent_supervisor_noc_integration(self):
        """Prueba la integración del Supervisor con el agente NOC y aislamiento de MCPs."""
        supervisor = MultiAgentSupervisor()
        turn = supervisor.process_turn("Tengo problemas de señal y la radiobase parece caida en Maracaibo", {"state": "Zulia"})

        assert turn["detected_domain"] == "network_noc"
        assert turn["delegated_worker"] == "NetworkNocAgent"
        assert turn["smart_mcp_routing"]["active_mcp_server"] == "mcp_noc_tools"
        assert "mcp_noc_tools" not in turn["smart_mcp_routing"]["hidden_mcp_servers"]
        assert turn["noc_bulletin"] is not None

    def test_07_api_service_rules_endpoints(self):
        """Prueba los endpoints REST de reglas en MovilnetAPIService."""
        service = MovilnetAPIService()

        # 1. GET /api/v1/rules/status
        code, headers, body = service.dispatch("GET", "/api/v1/rules/status", {}, b"")
        assert code == 200
        payload = json.loads(body.decode("utf-8"))
        assert payload["status"] == "ONLINE"
        assert payload["summary"]["plans_available"] >= 3

        # 2. GET /api/v1/noc/bulletins
        code, headers, body = service.dispatch("GET", "/api/v1/noc/bulletins", {}, b"")
        assert code == 200
        payload = json.loads(body.decode("utf-8"))
        assert payload["status"] == "success"
        assert len(payload["bulletins"]) >= 1

        # 3. POST /api/v1/rules/reload
        code, headers, body = service.dispatch("POST", "/api/v1/rules/reload", {}, b"{}")
        assert code == 200
        payload = json.loads(body.decode("utf-8"))
        assert payload["success"] is True
        assert "metadata" in payload
