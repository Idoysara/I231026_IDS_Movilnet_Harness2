#!/usr/bin/env python3
"""
api/agents/agent_geo_validation.py — Sub-Agente de Validación y Calidad Territorial
====================================================================================
Proyecto: AI_Movilnet_300926 / Módulo Geoespacial Nivel 5
Función: Auditoría de integridad cartográfica; valida que las coordenadas GPS
         caigan dentro de las demarcaciones territoriales oficiales de Venezuela.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.geo_tools import mcp_geo_validate_boundaries


class GeoValidationAgent:
    """Sub-Agente de Validación y Calidad Cartográfica."""

    def __init__(self):
        self.agent_name = "Sub-Agente de Validación y Calidad Territorial"
        self.role = "Auditoría de integridad espacial y control de fronteras político-territoriales"

    def audit_record(
        self,
        latitude: float,
        longitude: float,
        state: str,
        municipality: str,
        parish: Optional[str] = None
    ) -> Dict[str, Any]:
        """Audita el registro contra la demarcación oficial INE/IGVSB."""
        start = time.time()
        mcp_res = mcp_geo_validate_boundaries(
            latitude=latitude,
            longitude=longitude,
            declared_state=state,
            declared_municipality=municipality,
            declared_parish=parish
        )

        return {
            "audited_by": self.agent_name,
            "validation_result": mcp_res,
            "is_certified": mcp_res.get("is_valid", False),
            "execution_ms": round((time.time() - start) * 1000, 2)
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sub-Agente de Validación Territorial Movilnet")
    parser.add_argument("--test", action="store_true", help="Auto-verificación de límites territoriales")
    args = parser.parse_args()
    if args.test:
        agent = GeoValidationAgent()
        res = agent.audit_record(
            latitude=10.4965, longitude=-66.8505,
            state="Miranda", municipality="Chacao", parish="Chacao"
        )
        assert res["is_certified"] is True, "Fallo en validación territorial"
        print(f"✅ [GEO_VALIDATION_AGENT]: Auto-verificación superada (Status: {res['validation_result']['status']} en {res['execution_ms']} ms).")

