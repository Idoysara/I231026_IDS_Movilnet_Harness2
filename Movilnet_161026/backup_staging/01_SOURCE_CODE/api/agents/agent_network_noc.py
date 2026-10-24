#!/usr/bin/env python3
"""
api/agents/agent_network_noc.py — Agente Especialista en Operaciones de Red (NOC)
================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal

Atiende consultas e incidencias de radiobases, cobertura 4GMAX, caídas de señal y
mantenimientos técnicos programados en Venezuela, interactuando con `mcp_noc_tools`.
"""

from __future__ import annotations

import os
import sys
import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.noc_tools import NocMcpServer
from core.department_rule_engine import DepartmentRuleEngine

VENEZUELA_REGIONS = [
    "Amazonas", "Anzoátegui", "Anzoategui", "Apure", "Aragua", "Barinas", "Bolívar", "Bolivar",
    "Carabobo", "Cojedes", "Delta Amacuro", "Distrito Capital", "Caracas", "Falcón", "Falcon",
    "Guárico", "Guarico", "Lara", "Mérida", "Merida", "Miranda", "Monagas", "Nueva Esparta",
    "Margarita", "Portuguesa", "Sucre", "Táchira", "Tachira", "Trujillo", "La Guaira", "Vargas",
    "Yaracuy", "Zulia", "Maracaibo", "Valencia", "Barquisimeto", "Maracay", "San Cristobal", "Puerto La Cruz"
]


@dataclass
class NetworkInquiryResult:
    msisdn: str
    detected_region: str
    has_active_outage: bool
    response_text: str
    ticket_id: Optional[str] = None
    suggested_action: Optional[str] = None
    telemetry_quality: Optional[str] = None


class NetworkNocAgent:
    """Sub-Agente Autónomo del NOC y Operaciones de Red Movilnet."""

    def __init__(self):
        self.agent_name = "NetworkNocAgent"
        self.department = "Operaciones de Red, Infraestructura y Monitoreo (NOC)"
        self.mcp_server = NocMcpServer()
        self.rule_engine = DepartmentRuleEngine.get_instance()

    def extract_region(self, text: str, fallback: str = "Distrito Capital") -> str:
        """Extrae la entidad federal o ciudad mencionada en el mensaje del usuario."""
        text_lower = text.lower()
        for region in VENEZUELA_REGIONS:
            # Match de palabra completa
            if re.search(rf"\b{re.escape(region.lower())}\b", text_lower):
                return region
        return fallback

    def process_inquiry(self, message: str, context: Optional[Dict[str, Any]] = None) -> NetworkInquiryResult:
        """
        Procesa la consulta de red del abonado:
        1. Identifica región o zona afectada.
        2. Verifica si el NOC tiene boletín preventivo/correctivo activo.
        3. Si hay boletín, emite aviso proactivo con tiempo de restitución.
        4. Si no hay incidencia masiva, diagnostica parámetros de señal o genera ticket.
        """
        ctx = context or {}
        msisdn = ctx.get("phone", "04160000000")
        detected_region = self.extract_region(message, fallback=ctx.get("state", "Distrito Capital"))

        # 1. Consultar estado regional en MCP
        reg_check = self.mcp_server.get_regional_status(detected_region)

        if reg_check.get("has_active_incident"):
            # Caso A: Incidencia masiva o modernización en curso (Supresión Proactiva de Ticket)
            bulletin_msg = reg_check.get("message")
            eta = reg_check.get("estimated_restoration", "en las próximas horas")
            response = (
                f"📡 *Aviso Técnico del NOC Movilnet:*\n\n"
                f"{bulletin_msg}\n\n"
                f"⏳ *Hora estimada de normalización:* {eta}\n"
                f"💡 No es necesario reportar avería individual; nuestras cuadrillas ya se encuentran laborando en sitio."
            )
            return NetworkInquiryResult(
                msisdn=msisdn,
                detected_region=detected_region,
                has_active_outage=True,
                response_text=response,
                ticket_id=reg_check.get("incident_id"),
                suggested_action="ESPERAR_RESTITUCION"
            )

        # Caso B: Sin incidencia masiva reportada en la zona
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["apn", "configuracion", "parametros", "datos lentos"]):
            # Respuesta rápida de optimización técnica
            response = (
                f"📡 *Diagnóstico de Señal ({detected_region}):*\n"
                f"Nuestras radiobases en {detected_region} reportan operación normal 4GMAX.\n\n"
                f"🔧 *Verifica la configuración de tu APN:*\n"
                f"• Nombre: Movilnet 4G\n"
                f"• APN: `int.movilnet.com.ve`\n"
                f"• Tipo de autenticación: PAP\n"
                f"Guarda y activa el Modo Avión durante 10 segundos para reconectar a la radiobase más cercana."
            )
            return NetworkInquiryResult(
                msisdn=msisdn,
                detected_region=detected_region,
                has_active_outage=False,
                response_text=response,
                suggested_action="OPTIMIZAR_APN",
                telemetry_quality="BUENA"
            )

        # Caso C: Reporte puntual de sin señal / avería
        ticket_res = self.mcp_server.report_incident(
            msisdn=msisdn,
            region=detected_region,
            municipality=ctx.get("municipality", "General"),
            issue_type="DEGRADACION_COBERTURA",
            description=message[:150]
        )
        ticket_id = ticket_res["ticket"]["ticket_id"]
        response = (
            f"📡 *Soporte Técnico de Red Movilnet 4GMAX:*\n"
            f"No registramos fallas masivas en {detected_region}, por lo que hemos generado una orden de revisión técnica.\n\n"
            f"🎫 *Ticket de Inspección:* `#{ticket_id}`\n"
            f"Nuestros ingenieros de guardia monitorizarán la radiobase asignada a su sector."
        )
        return NetworkInquiryResult(
            msisdn=msisdn,
            detected_region=detected_region,
            has_active_outage=False,
            response_text=response,
            ticket_id=ticket_id,
            suggested_action="TICKET_GENERADO",
            telemetry_quality="OPTIMAL"
        )


if __name__ == "__main__":
    agent = NetworkNocAgent()
    print("=" * 70)
    print("📡 AGENTE DE OPERACIONES DE RED (NOC) — AUTO-TEST")
    print("=" * 70)

    # Test 1: Zona con mantenimiento activo (Maracaibo)
    q1 = "Tengo problemas con los datos en Maracaibo no me carga nada"
    res1 = agent.process_inquiry(q1, {"phone": "04161234567"})
    print(f"\nPregunta: \"{q1}\"")
    print(f"Región Detectada: {res1.detected_region}")
    print(f"Tiene Avería Masiva: {res1.has_active_outage}")
    print(f"Respuesta:\n{res1.response_text}")

    # Test 2: Zona operativa normal (Caracas)
    q2 = "No me levanta 4G en Caracas, necesito configurar el apn"
    res2 = agent.process_inquiry(q2, {"phone": "04167654321"})
    print(f"\nPregunta: \"{q2}\"")
    print(f"Región Detectada: {res2.detected_region}")
    print(f"Tiene Avería Masiva: {res2.has_active_outage}")
    print(f"Respuesta:\n{res2.response_text}")
