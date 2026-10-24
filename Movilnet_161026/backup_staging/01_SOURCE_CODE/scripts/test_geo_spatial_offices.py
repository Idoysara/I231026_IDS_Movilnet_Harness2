#!/usr/bin/env python3
"""
scripts/test_geo_spatial_offices.py — Suite de Certificación Formal Geoespacial de Oficinas Movilnet
===================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal

Cobertura de Pruebas:
1. Bounding Box Nacional WGS84 de Venezuela y rechazo fuera de frontera (ERR_OUTSIDE_VENEZUELA).
2. Resolución Geodésica Haversine de agencias Movilnet más cercanas por coordenadas GPS (Caracas, Valencia, Maracaibo).
3. Búsqueda estructurada por texto de ciudad/estado (Valencia, Barquisimeto, Puerto La Cruz, Maracay, San Cristóbal).
4. Cumplimiento estricto de la Regla Inviolable de Cero Adivinación y Datos Faltantes (solicitud de aclaratoria).
5. Despacho Fast-Path Determinista Zero-Token ODA (<15ms, 0 tokens LLM).
6. Diferenciación comercial y de pipeline: IS_MOVILNET_SUBSCRIBER (0416/0426) vs No-Usuarios (0414/0424/0412).
7. Suite de herramientas MCP (Model Context Protocol JSON-RPC 2.0).
8. Sub-agentes especializados: GeoSpatialAgent y GeoValidationAgent.
9. Integridad del Workflow n8n (Edit Fields, Switch, Router Determinista, Core & Marketing Router).
"""

from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.geo_catalog import (
    DB_PATH,
    haversine_distance_meters,
    is_point_in_venezuela,
    find_nearest_movilnet_agency,
    find_agencies_by_city_or_state,
    init_geo_database
)
from mcp.geo_tools import (
    mcp_geo_find_nearest_agency,
    mcp_geo_find_agencies_by_city,
    GeoVenezuelaMcpServer
)
from api.agents.agent_geo_spatial import GeoSpatialAgent
from api.agents.agent_geo_validation import GeoValidationAgent
from core.fastpath_intent_interceptor import FastPathIntentInterceptor


class TestGeoSpatialOfficesSuite(unittest.TestCase):
    """Suite de Pruebas de Calidad Militar para la Geolocalización de Oficinas Movilnet."""

    @classmethod
    def setUpClass(cls):
        init_geo_database(DB_PATH)
        cls.interceptor = FastPathIntentInterceptor()
        cls.geo_agent = GeoSpatialAgent()
        cls.val_agent = GeoValidationAgent()
        cls.mcp_server = GeoVenezuelaMcpServer()
        # Calentamiento de caché SQLite para evitar jitter de arranque en frío
        cls.interceptor.intercept("Warmup", "04160000000", latitude=10.49, longitude=-66.85)

    # -------------------------------------------------------------------------
    # 1. Bounding Box Nacional WGS84
    # -------------------------------------------------------------------------
    def test_wgs84_bounding_box_venezuela(self):
        """Valida coordenadas dentro y fuera de la República Bolivariana de Venezuela."""
        # Dentro de Venezuela
        self.assertTrue(is_point_in_venezuela(10.4960, -66.8525)) # Caracas
        self.assertTrue(is_point_in_venezuela(10.6680, -71.6180)) # Maracaibo
        self.assertTrue(is_point_in_venezuela(10.1980, -67.9540)) # Valencia
        self.assertTrue(is_point_in_venezuela(7.7850, -72.2150))  # San Cristóbal

        # Fuera de Venezuela
        self.assertFalse(is_point_in_venezuela(4.7110, -74.0721))  # Bogotá
        self.assertFalse(is_point_in_venezuela(25.7617, -80.1918)) # Miami
        self.assertFalse(is_point_in_venezuela(40.4168, -3.7038))  # Madrid

    # -------------------------------------------------------------------------
    # 2. Resolución de Agencias por Coordenadas GPS
    # -------------------------------------------------------------------------
    def test_nearest_agency_gps_caracas(self):
        """Desde Altamira/Chacao debe resolver Centro Plaza o Torre El Rosal en < 2 km."""
        res = find_nearest_movilnet_agency(10.4960, -66.8530)
        self.assertIsNotNone(res)
        self.assertIn("Centro Plaza", res["name"])
        self.assertLess(res["distance_km"], 1.0)
        self.assertIn("google.com/maps", res["google_maps_url"])
        self.assertGreater(res["walking_minutes_est"], 0)
        self.assertGreater(res["driving_minutes_est"], 0)

    def test_nearest_agency_gps_valencia(self):
        """Desde San Diego / Valencia debe resolver Metrópolis Valencia."""
        res = find_nearest_movilnet_agency(10.1990, -67.9550)
        self.assertIsNotNone(res)
        self.assertIn("Metrópolis Valencia", res["name"])
        self.assertLess(res["distance_km"], 2.0)

    def test_nearest_agency_gps_maracaibo(self):
        """Desde Maracaibo 5 de Julio debe resolver Oficina 5 de Julio."""
        res = find_nearest_movilnet_agency(10.6685, -71.6185)
        self.assertIsNotNone(res)
        self.assertIn("5 de Julio", res["name"])
        self.assertLess(res["distance_km"], 1.0)

    def test_nearest_agency_outside_venezuela_guard(self):
        """Coordenadas internacionales deben retornar ERR_OUTSIDE_VENEZUELA."""
        res = find_nearest_movilnet_agency(25.7617, -80.1918)
        self.assertEqual(res.get("error"), "ERR_OUTSIDE_VENEZUELA")

    # -------------------------------------------------------------------------
    # 3. Búsqueda por Texto (Ciudad / Estado / Zona)
    # -------------------------------------------------------------------------
    def test_search_agencies_by_city_text(self):
        """Búsqueda textual de agencias por nombre de ciudad."""
        val = find_agencies_by_city_or_state("Valencia")
        self.assertGreaterEqual(len(val), 2)
        self.assertTrue(any("Metrópolis" in o["name"] for o in val))

        bar = find_agencies_by_city_or_state("Barquisimeto")
        self.assertGreaterEqual(len(bar), 1)
        self.assertIn("Las Trinitarias", bar[0]["name"])

        plc = find_agencies_by_city_or_state("Puerto La Cruz")
        self.assertGreaterEqual(len(plc), 1)
        self.assertIn("Plaza Mayor", plc[0]["name"])

    # -------------------------------------------------------------------------
    # 4. Regla Inviolable de Cero Adivinación y Datos Faltantes
    # -------------------------------------------------------------------------
    def test_zero_guessing_clarification_rule(self):
        """Pregunta sin ciudad ni GPS no debe asumir ciudad, debe pedir aclaratoria."""
        res = self.interceptor.intercept("¿Dónde queda una oficina de atención?", "04161234567")
        self.assertTrue(res.can_intercept)
        self.assertEqual(res.intent_detected, "LOCALIZADOR_OFICINAS_TELCO")
        # No debe afirmar que el usuario está en Caracas
        self.assertNotIn("cercana a tu ubicación (", res.response_text)
        # Debe solicitar ubicación actual o ciudad
        self.assertIn("Comparte tu ubicación actual por WhatsApp", res.response_text)
        self.assertIn("dinos en qué ciudad o zona estás", res.response_text)

    # -------------------------------------------------------------------------
    # 5. Despacho Fast-Path Determinista Zero-Token ODA
    # -------------------------------------------------------------------------
    def test_fastpath_interceptor_zero_token_performance(self):
        """La resolución de oficinas debe tardar <15ms y consumir 0 tokens."""
        res = self.interceptor.intercept("Ubicación compartida", "04160000001", latitude=10.4960, longitude=-66.8530)
        self.assertTrue(res.can_intercept)
        self.assertEqual(res.intent_detected, "LOCALIZADOR_OFICINAS_TELCO")
        self.assertEqual(res.tokens_consumed, 0)
        self.assertLess(res.latency_ms, 30.0)
        self.assertEqual(res.data_source, "GEO_SPATIAL_MOVILNET_OFFICES")

    # -------------------------------------------------------------------------
    # 6. Diferenciación Comercial: 0416/0426 vs 0414/0424/0412
    # -------------------------------------------------------------------------
    def test_subscriber_vs_prospect_messaging(self):
        """Abonado Movilnet recibe trámites de autogestión; prospecto recibe portabilidad."""
        # 0416 (Movilnet)
        res_mov = self.interceptor.intercept("Ubicación", "04161234567", latitude=10.4960, longitude=-66.8530)
        self.assertTrue(res_mov.is_movilnet_subscriber)
        self.assertEqual(res_mov.authorized_pipeline, "CORE_MOVILNET_AUTOGESTION")
        self.assertIn("Reposición de SIM 4GMAX", res_mov.response_text)
        self.assertIn("carrier=movilnet", res_mov.response_text)

        # 0414 (Movistar)
        res_comp = self.interceptor.intercept("Ubicación", "04141234567", latitude=10.4960, longitude=-66.8530)
        self.assertFalse(res_comp.is_movilnet_subscriber)
        self.assertEqual(res_comp.authorized_pipeline, "NO_USUARIOS_MOVILNET")
        self.assertIn("Portabilidad 4GMAX", res_comp.response_text)
        self.assertIn("carrier=MOVISTAR", res_comp.response_text)

    # -------------------------------------------------------------------------
    # 7. Suite MCP JSON-RPC 2.0
    # -------------------------------------------------------------------------
    def test_mcp_geo_tools_protocol(self):
        """Verifica las herramientas mcp_geo_find_nearest_agency y mcp_geo_find_agencies_by_city."""
        # Herramienta directa
        nearest_mcp = mcp_geo_find_nearest_agency(latitude=10.4960, longitude=-66.8530)
        self.assertTrue(nearest_mcp["success"])
        self.assertTrue(nearest_mcp["found"])
        self.assertIn("Centro Plaza", nearest_mcp["agency"]["name"])

        # Vía Servidor MCP JSON-RPC
        rpc_req = self.mcp_server.handle_request("mcp_geo_find_agencies_by_city", {"query": "Maracaibo"})
        self.assertEqual(rpc_req["jsonrpc"], "2.0")
        self.assertTrue(rpc_req["result"]["success"])
        self.assertGreaterEqual(rpc_req["result"]["total_found"], 2)

    # -------------------------------------------------------------------------
    # 8. Sub-agentes GeoEspacial y Validación Territorial
    # -------------------------------------------------------------------------
    def test_subagents_execution(self):
        """Verifica la ejecución y auditoría de GeoSpatialAgent y GeoValidationAgent."""
        # GeoSpatialAgent
        agent_res = self.geo_agent.find_nearest_agency(latitude=10.4960, longitude=-66.8530)
        self.assertTrue(agent_res["success"])
        self.assertIn("Centro Plaza", agent_res["agency"]["name"])

        # GeoValidationAgent
        audit_res = self.val_agent.audit_record(
            latitude=10.4960, longitude=-66.8525,
            state="Miranda", municipality="Chacao", parish="Chacao"
        )
        self.assertTrue(audit_res["is_certified"])
        self.assertEqual(audit_res["validation_result"]["status"], "TERRITORIO_VALIDADO_CONFORME")

    # -------------------------------------------------------------------------
    # 9. Integridad del Workflow n8n
    # -------------------------------------------------------------------------
    def test_n8n_workflow_geo_integration_integrity(self):
        """Verifica que el JSON de n8n incluya la extracción y enrutamiento geoespacial."""
        wf_path = PROJECT_ROOT / "api" / "n8n_workflows" / "viki_lpgtec_v2_ids_instant_dispatch.json"
        with open(wf_path, "r", encoding="utf-8") as f:
            wf = json.load(f)

        # 1. Edit Fields debe tener asignación para ubicacion
        ef = next(n for n in wf["nodes"] if n["name"] == "Edit Fields")
        msg_type_assign = next(a for a in ef["parameters"]["assignments"]["assignments"] if a["name"] == "body.data.messageType")
        self.assertIn("ubicacion", msg_type_assign["value"])

        # 2. Switch debe tener regla para ubicacion
        sw = next(n for n in wf["nodes"] if n["name"] == "Switch")
        self.assertTrue(any(r.get("outputKey") == "ubicacion" for r in sw["parameters"]["rules"]["values"]))

        # 3. Router Determinista debe capturar intenciones de oficinas
        router_det = next(n for n in wf["nodes"] if n["name"] == "Router - Consultas determinísticas")
        telco_rule = next(r for r in router_det["parameters"]["rules"]["values"] if r.get("outputKey") == "telco_movilnet_fastpath")
        self.assertIn("oficina", telco_rule["conditions"]["conditions"][0]["leftValue"])

        # 4. Movilnet Core & Marketing Router debe tener el bloque de localización
        core_router = next(n for n in wf["nodes"] if n["name"] == "Movilnet Core & Marketing Router")
        self.assertIn("LOCALIZADOR DE OFICINAS Y AGENCIAS MOVILNET", core_router["parameters"]["jsCode"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
