#!/usr/bin/env python3
"""
api/agents/agent_commercial_directory.py — Sub-Agente de Datos Comerciales y Directorio
========================================================================================
Proyecto: AI_Movilnet_300926 / Módulo Geoespacial Nivel 5
Función: Estructuración, limpieza y enriquecimiento de locales comerciales,
         farmacias, clínicas y torres empresariales en esquemas normalizados.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from mcp.geo_tools import mcp_geo_structured_query, mcp_geo_ingest_feature


@dataclass
class CommercialEntityRecord:
    name: str
    category: str
    sub_category: str
    state: str
    municipality: str
    parish: str
    latitude: float
    longitude: float
    address: str
    phone: Optional[str] = None
    opening_hours: Optional[str] = None
    emergency_service_24h: bool = False
    metadata: Dict[str, Any] = None


class CommercialDirectoryAgent:
    """Sub-Agente de Datos Comerciales y Directorio."""

    def __init__(self):
        self.agent_name = "Sub-Agente de Datos Comerciales y Directorio"
        self.role = "Normalización y curaduría de entidades comerciales"

    def clean_phone_number(self, raw_phone: Optional[str]) -> Optional[str]:
        """Normaliza números telefónicos a formato venezolano E.164 (+58)."""
        if not raw_phone:
            return None
        cleaned = re.sub(r"[^\d+]", "", raw_phone)
        if cleaned.startswith("0"):
            cleaned = "+58" + cleaned[1:]
        elif cleaned.startswith("58"):
            cleaned = "+" + cleaned
        return cleaned

    def query_directory(
        self,
        category: Optional[str] = None,
        municipality: Optional[str] = None,
        state: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """Consulta registros estructurados en el directorio de comercios y salud."""
        return mcp_geo_structured_query(
            state=state,
            municipality=municipality,
            category=category,
            keyword=keyword
        )

    def normalize_and_ingest(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Limpia el registro crudo y lo almacena mediante la herramienta MCP."""
        cleaned_phone = self.clean_phone_number(raw_record.get("phone"))
        raw_record["phone"] = cleaned_phone

        # Normalizar capitalización de nombres y dirección
        if "name" in raw_record:
            raw_record["name"] = raw_record["name"].strip()
        if "address" in raw_record:
            raw_record["address"] = raw_record["address"].strip()

        return mcp_geo_ingest_feature(feature=raw_record, source_format="agent_sanitized")
