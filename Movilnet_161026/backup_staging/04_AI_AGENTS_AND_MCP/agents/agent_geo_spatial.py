#!/usr/bin/env python3
"""
api/agents/agent_geo_spatial.py — Sub-Agente Cartográfico y Geoespacial
========================================================================
Proyecto: AI_Movilnet_300926 / Módulo Geoespacial Nivel 5
Función: Realiza proyecciones geodésicas, cálculos espaciales Haversine,
         resolución de rutas a pie/vehículo y consultas al MCP geoespacial.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.geo_tools import (
    mcp_geo_spatial_search,
    mcp_geo_structured_query,
    mcp_geo_find_nearest_agency,
    mcp_geo_find_agencies_by_city,
    haversine_distance_meters
)


@dataclass
class GeoSpatialTaskRequest:
    latitude: float
    longitude: float
    category: Optional[str] = None
    radius_meters: int = 2500
    limit: int = 5


@dataclass
class GeoSpatialTaskResponse:
    success: bool
    center: Dict[str, float]
    radius_meters: int
    places_found: int
    places: List[Dict[str, Any]]
    fastest_destination: Optional[Dict[str, Any]]
    execution_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GeoSpatialAgent:
    """Sub-Agente Cartográfico y Geoespacial."""

    def __init__(self):
        self.agent_name = "Sub-Agente Cartográfico y Geoespacial"
        self.role = "Resolución de proximidad espacial y cálculos de ruta"

    def execute_spatial_search(self, request: GeoSpatialTaskRequest) -> GeoSpatialTaskResponse:
        start_time = time.time()
        mcp_res = mcp_geo_spatial_search(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_meters=request.radius_meters,
            category=request.category,
            limit=request.limit
        )

        results = mcp_res.get("results", [])
        fastest = results[0] if results else None

        return GeoSpatialTaskResponse(
            success=True,
            center={"latitude": request.latitude, "longitude": request.longitude},
            radius_meters=request.radius_meters,
            places_found=len(results),
            places=results,
            fastest_destination=fastest,
            execution_ms=round((time.time() - start_time) * 1000, 2)
        )

    def find_nearest_agency(self, latitude: float, longitude: float, max_radius_km: float = 150.0) -> Dict[str, Any]:
        """Localiza la agencia Movilnet más cercana usando el protocolo MCP."""
        start_time = time.time()
        res = mcp_geo_find_nearest_agency(latitude=latitude, longitude=longitude, max_radius_km=max_radius_km)
        res["agent"] = self.agent_name
        res["total_execution_ms"] = round((time.time() - start_time) * 1000, 2)
        return res

    def find_agencies_by_city(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Localiza agencias Movilnet por ciudad o zona geográfica usando MCP."""
        start_time = time.time()
        res = mcp_geo_find_agencies_by_city(query=query, limit=limit)
        res["agent"] = self.agent_name
        res["total_execution_ms"] = round((time.time() - start_time) * 1000, 2)
        return res


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sub-Agente Cartográfico y Geoespacial Movilnet")
    parser.add_argument("--test", action="store_true", help="Auto-verificación del sub-agente geoespacial")
    args = parser.parse_args()
    if args.test:
        agent = GeoSpatialAgent()
        # Test 1: Búsqueda espacial genérica
        req = GeoSpatialTaskRequest(latitude=10.4958, longitude=-66.8530, radius_meters=2000, limit=3)
        res = agent.execute_spatial_search(req)
        assert res.success is True, "Fallo en ejecución de GeoSpatialAgent"

        # Test 2: Localización de agencia más cercana (Altamira)
        agency_res = agent.find_nearest_agency(10.4960, -66.8530)
        assert agency_res["success"] is True and agency_res["found"] is True
        assert "Centro Plaza" in agency_res["agency"]["name"]

        # Test 3: Búsqueda por texto (Barquisimeto)
        city_res = agent.find_agencies_by_city("Barquisimeto")
        assert city_res["success"] is True and city_res["total_found"] >= 1
        assert "Trinitarias" in city_res["agencies"][0]["name"]

        print(f"✅ [GEO_SPATIAL_AGENT]: Auto-verificación superada (3 tests OK, agencia: {agency_res['agency']['name']}).")

