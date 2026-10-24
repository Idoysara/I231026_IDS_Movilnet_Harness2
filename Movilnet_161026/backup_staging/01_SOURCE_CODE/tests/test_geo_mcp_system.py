#!/usr/bin/env python3
"""
tests/test_geo_mcp_system.py — Pruebas Unitarias para Suite MCP Geoespacial y Sub-Agentes
========================================================================================
Proyecto: AI_Movilnet_300926 / Módulo Geoespacial de Venezuela
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from mcp.geo_tools import (
    mcp_geo_spatial_search,
    mcp_geo_structured_query,
    mcp_geo_ingest_feature,
    mcp_geo_validate_boundaries,
    GeoVenezuelaMcpServer
)
from mcp.master_gateway import MovilnetMasterMcpGateway
from api.agents.agent_geo_spatial import GeoSpatialAgent, GeoSpatialTaskRequest
from api.agents.agent_commercial_directory import CommercialDirectoryAgent
from api.agents.agent_geo_validation import GeoValidationAgent


class TestGeoMcpSystem(unittest.TestCase):
    """Pruebas de la Suite MCP Geoespacial y sus Sub-Agentes."""

    def test_01_spatial_search_pharmacies_in_chacao(self):
        """Búsqueda espacial de farmacias en Los Palos Grandes / Chacao."""
        # Coordenadas Plaza Altamira (10.4958, -66.8530)
        res = mcp_geo_spatial_search(latitude=10.4958, longitude=-66.8530, radius_meters=1500, category="farmacia")
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["total_matches"], 1)
        first_place = res["results"][0]
        self.assertEqual(first_place["municipality"], "Chacao")
        self.assertIn("farmatodo", first_place["name"].lower())

    def test_02_structured_query_by_municipality(self):
        """Consulta estructurada por municipio Chacao y categoría salud_clinica."""
        res = mcp_geo_structured_query(municipality="Chacao", category="salud_clinica")
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["total_records_found"], 1)
        names = [r["name"] for r in res["records"]]
        self.assertTrue(any("Clínica El Ávila" in n for n in names))

    def test_03_ingest_and_normalize_feature(self):
        """Ingestión de un feature cartográfico tipo GeoJSON OSM."""
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-66.8670, 10.4890]},
            "properties": {
                "name": "Sede Corporativa Cantv / Movilnet",
                "amenity": "telecommunication",
                "office": "company",
                "state": "Miranda",
                "municipality": "Chacao",
                "parish": "Chacao",
                "address": "Av. Venezuela, El Rosal"
            }
        }
        res = mcp_geo_ingest_feature(feature)
        self.assertTrue(res["success"])
        self.assertEqual(res["category"], "edificio_corporativo")

    def test_04_territorial_boundary_validation_success(self):
        """Validación de coordenadas dentro de Chacao, Miranda."""
        res = mcp_geo_validate_boundaries(
            latitude=10.4965,
            longitude=-66.8505,
            declared_state="Miranda",
            declared_municipality="Chacao",
            declared_parish="Chacao"
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["status"], "TERRITORIO_VALIDADO_CONFORME")

    def test_05_territorial_boundary_validation_outside_venezuela(self):
        """Rechazo inmediato de coordenadas fuera de Venezuela (ej. Miami)."""
        res = mcp_geo_validate_boundaries(
            latitude=25.7617,
            longitude=-80.1918,
            declared_state="Miranda",
            declared_municipality="Chacao"
        )
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["error_code"], "ERR_OUTSIDE_VENEZUELA")

    def test_06_master_mcp_gateway_integration(self):
        """Verificar que la suite geoespacial esté expuesta en el Master Gateway."""
        gw = MovilnetMasterMcpGateway()
        tools = gw.list_all_tools()
        tool_names = [t["name"] for t in tools]
        self.assertIn("mcp_geo_spatial_search", tool_names)
        self.assertIn("mcp_geo_structured_query", tool_names)
        self.assertIn("mcp_geo_ingest_feature", tool_names)
        self.assertIn("mcp_geo_validate_boundaries", tool_names)

        # Dispatch de prueba
        dispatch_res = gw.dispatch(
            "mcp_geo_spatial_search",
            {"latitude": 10.4958, "longitude": -66.8530, "radius_meters": 1000}
        )
        self.assertEqual(dispatch_res.get("jsonrpc"), "2.0")
        self.assertTrue(dispatch_res["result"]["success"])

    def test_07_sub_agents_collaboration_pipeline(self):
        """Validar ejecución coordinada de los sub-agentes."""
        geo_agent = GeoSpatialAgent()
        comm_agent = CommercialDirectoryAgent()
        val_agent = GeoValidationAgent()

        # 1. Validación de coordenadas de entrada
        val_res = val_agent.audit_record(
            latitude=10.4965, longitude=-66.8505,
            state="Miranda", municipality="Chacao", parish="Chacao"
        )
        self.assertTrue(val_res["is_certified"])

        # 2. Búsqueda espacial
        geo_res = geo_agent.execute_spatial_search(
            GeoSpatialTaskRequest(latitude=10.4965, longitude=-66.8505, radius_meters=2000, category="farmacia")
        )
        self.assertTrue(geo_res.success)
        self.assertGreater(geo_res.places_found, 0)

        # 3. Consulta estructurada en directorio
        dir_res = comm_agent.query_directory(municipality="Chacao", category="salud_clinica")
        self.assertTrue(dir_res["success"])


if __name__ == "__main__":
    unittest.main()
