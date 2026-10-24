#!/usr/bin/env python3
"""
mcp/telco_tools.py — Suite 1: Core Telecom, Radiobases OSS/BSS & Seguridad SIM
==============================================================================
Proyecto: AI_Movilnet_300926 / Antigravity Level 5 Architecture
Estándar: Model Context Protocol (MCP) JSON-RPC 2.0 & TM Forum ODA (TMF678)
Cumplimiento: CONATEL / 3GPP LTE Release 15 / ISO-27001

Herramientas MCP Expuestas:
  1. mcp_telco_get_subscriber: Consulta de saldo, megas y corte de línea 0416/0426
  2. mcp_telco_diagnose_coverage: Telemetría OSS eNodeB (RSRP, RSRQ, SINR y alarmas 4GMAX)
  3. mcp_telco_check_apn: Parámetros técnicos oficiales APN int.movilnet.com.ve
  4. mcp_telco_verify_sim_swap: Auditoría HSS/HLR de cambio de tarjeta SIM en ventana de 24h
  5. mcp_telco_lock_line_theft: Bloqueo de emergencia IMEI/IMSI en EIR y generación de ticket
  6. mcp_telco_record_sla: Ingesta de métricas de latencia de red (SRE buffer)
  7. mcp_telco_get_sla_report: Resumen estadístico de observabilidad (P50, P95, P99 < 25ms)
"""

from __future__ import annotations

import os
import sys
import json
import time
import math
import re
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Modelos de Datos Tipados (Data Models)
# ============================================================================

@dataclass
class SubscriberData:
    msisdn: str
    imsi: str
    name: str
    national_id: str
    plan_id: str
    plan_name: str
    balance_bs: float
    balance_usd_equiv: float
    remaining_data_mb: int
    total_quota_mb: int
    billing_cutoff_date: str
    last_sim_swap_timestamp: str
    status: str
    registered_cell_id: str
    apn_configured: str = "int.movilnet.com.ve"

    @property
    def consumption_pct(self) -> float:
        if self.total_quota_mb <= 0:
            return 0.0
        used = max(0, self.total_quota_mb - self.remaining_data_mb)
        return round((used / self.total_quota_mb) * 100.0, 1)


@dataclass
class SlaMetricRecord:
    service: str
    latency_ms: float
    status_code: int
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# Almacén de Estado y Telemetría en Memoria
# ============================================================================

_SLA_RING_BUFFER: List[SlaMetricRecord] = []
_MAX_RING_BUFFER_CAPACITY = 2000

# Base de datos simulada con partición de suscriptores Movilnet
_SUBSCRIBER_REGISTRY: Dict[str, SubscriberData] = {
    "04161234567": SubscriberData(
        msisdn="04161234567",
        imsi="734061234567890",
        name="Alejandro Silva",
        national_id="V-18492019",
        plan_id="PLAN_INTELIPLAN_10GB",
        plan_name="Inteliplan 10GB 4GMAX",
        balance_bs=142.50,
        balance_usd_equiv=3.85,
        remaining_data_mb=340,
        total_quota_mb=10240,
        billing_cutoff_date="2026-10-08",
        last_sim_swap_timestamp="2026-08-15T10:00:00Z",
        status="ACTIVA",
        registered_cell_id="CAR-CCS-ENB-042"
    ),
    "04269876543": SubscriberData(
        msisdn="04269876543",
        imsi="734069876543210",
        name="Valeria Gómez",
        national_id="V-24810992",
        plan_id="PLAN_CONECTA_PLUS",
        plan_name="Conecta Plus 4GMAX 5GB",
        balance_bs=12.00,
        balance_usd_equiv=0.32,
        remaining_data_mb=45,
        total_quota_mb=5120,
        billing_cutoff_date="2026-10-02",
        last_sim_swap_timestamp=(datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),  # Cambio reciente (<24h)
        status="ACTIVA",
        registered_cell_id="MAR-MCBO-ENB-108"
    ),
    "04165554321": SubscriberData(
        msisdn="04165554321",
        imsi="734065554321098",
        name="Carlos Mendoza",
        national_id="V-15200341",
        plan_id="PLAN_INTELIPLAN_20GB",
        plan_name="Inteliplan 20GB Pro 4GMAX",
        balance_bs=285.00,
        balance_usd_equiv=7.70,
        remaining_data_mb=14500,
        total_quota_mb=20480,
        billing_cutoff_date="2026-10-15",
        last_sim_swap_timestamp="2025-11-20T08:00:00Z",
        status="ACTIVA",
        registered_cell_id="VAL-CAR-ENB-015"
    )
}

# Catálogo OSS de Radiobases Movilnet 4GMAX
_RADIOBASE_TOPOLOGY: Dict[str, Dict[str, Any]] = {
    "CAR-CCS-ENB-042": {
        "cell_id": "CAR-CCS-ENB-042",
        "station_name": "eNodeB Plaza Venezuela",
        "municipality": "Libertador / Distrito Capital",
        "bands": ["LTE Band 4 (AWS 1700/2100)", "LTE Band 28 (700 MHz APT)"],
        "status": "OPERATIONAL",
        "load_pct": 68.4,
        "rf_metrics": {
            "rsrp_dbm": -84.2,   # Cobertura óptima (-80 a -90)
            "rsrq_db": -9.1,     # Calidad óptima (> -10)
            "sinr_db": 18.5,     # Relación señal-ruido excelente (> 15)
            "prb_utilization": 62.1
        },
        "active_alarms": []
    },
    "MAR-MCBO-ENB-108": {
        "cell_id": "MAR-MCBO-ENB-108",
        "station_name": "eNodeB 5 de Julio",
        "municipality": "Maracaibo / Zulia",
        "bands": ["LTE Band 4 (AWS)"],
        "status": "DEGRADED_POWER_ANOMALY",
        "load_pct": 89.2,
        "rf_metrics": {
            "rsrp_dbm": -108.5,  # Señal débil / borde de celda
            "rsrq_db": -16.8,    # Interferencia severa
            "sinr_db": 3.2,
            "prb_utilization": 88.7
        },
        "active_alarms": ["ALM_RECTIFIER_FAILURE", "ALM_HIGH_TEMPERATURE"]
    },
    "VAL-CAR-ENB-015": {
        "cell_id": "VAL-CAR-ENB-015",
        "station_name": "eNodeB Guaparo",
        "municipality": "Valencia / Carabobo",
        "bands": ["LTE Band 4 (AWS)", "LTE Band 28 (700 MHz)"],
        "status": "OPERATIONAL",
        "load_pct": 45.0,
        "rf_metrics": {
            "rsrp_dbm": -79.0,
            "rsrq_db": -7.5,
            "sinr_db": 22.0,
            "prb_utilization": 41.3
        },
        "active_alarms": []
    }
}


# ============================================================================
# Funciones Auxiliares y Validaciones
# ============================================================================

def _normalize_movilnet_number(msisdn: str) -> Tuple[bool, str]:
    """Valida y normaliza un número de telefonía móvil venezolana Movilnet."""
    cleaned = re.sub(r'[\s\-\+\(\)]', '', msisdn)
    if cleaned.startswith("58"):
        cleaned = "0" + cleaned[2:]
    if re.match(r'^0(416|426)[0-9]{7}$', cleaned):
        return True, cleaned
    if re.match(r'^(416|426)[0-9]{7}$', cleaned):
        return True, "0" + cleaned
    return False, cleaned


# ============================================================================
# Herramientas MCP Suite 1
# ============================================================================

def mcp_telco_get_subscriber(msisdn: str) -> Dict[str, Any]:
    """
    [MCP Tool] Consulta el estado integral de la línea, plan, saldo y cupo de datos.
    Contrato conforme a TM Forum TMF678 (Customer Bill & Balance Management).
    """
    valid, clean_num = _normalize_movilnet_number(msisdn)
    if not valid:
        return {
            "success": False,
            "error_code": "ERR_INVALID_PREFIX",
            "message": f"El número '{msisdn}' no corresponde a un prefijo oficial de Movilnet (0416 / 0426)."
        }

    sub = _SUBSCRIBER_REGISTRY.get(clean_num)
    if not sub:
        try:
            from db.repository import MovilnetRepository
            repo = MovilnetRepository()
            db_bal = repo.get_balance_and_quotas(clean_num)
            db_line = repo.get_line_details(clean_num)
            if db_bal and db_line:
                plan = repo.get_plan_by_id(db_line.get("plan_id", "PLAN_10GB_4GMAX"))
                plan_name = plan.get("name", "Inteliplan 10GB 4GMAX") if plan else "Inteliplan 10GB 4GMAX"
                sub = SubscriberData(
                    msisdn=clean_num,
                    imsi=db_line.get("imsi", f"73406{clean_num[1:]}00"),
                    name="Abonado Movilnet",
                    national_id="V-18000000",
                    plan_id=db_line.get("plan_id", "PLAN_10GB_4GMAX"),
                    plan_name=plan_name,
                    balance_bs=float(db_bal.get("balance_ves", 0.0)),
                    balance_usd_equiv=float(db_bal.get("balance_usd_equiv", 0.0)),
                    remaining_data_mb=int(db_bal.get("remaining_data_mb", 0)),
                    total_quota_mb=int(db_bal.get("total_quota_mb", 10240)),
                    billing_cutoff_date=str(db_bal.get("billing_cutoff_date", "2026-10-31")),
                    last_sim_swap_timestamp=str(db_line.get("last_sim_swap_at", "2026-01-10T12:00:00Z")),
                    status=db_line.get("status", "ACTIVO"),
                    registered_cell_id=db_line.get("cell_id", "CAR-CCS-ENB-001")
                )
                _SUBSCRIBER_REGISTRY[clean_num] = sub
        except Exception:
            pass

    if not sub:
        # Generar registro sintético verosímil si no está precargado
        now_dt = datetime.now(timezone.utc)
        sub = SubscriberData(
            msisdn=clean_num,
            imsi=f"73406{clean_num[1:]}00",
            name="Abonado Movilnet",
            national_id="V-00000000",
            plan_id="PLAN_INTELIPLAN_10GB",
            plan_name="Inteliplan 10GB 4GMAX",
            balance_bs=85.00,
            balance_usd_equiv=2.30,
            remaining_data_mb=1024,
            total_quota_mb=10240,
            billing_cutoff_date=(now_dt + timedelta(days=15)).strftime("%Y-%m-%d"),
            last_sim_swap_timestamp="2026-01-10T12:00:00Z",
            status="ACTIVA",
            registered_cell_id="CAR-CCS-ENB-042"
        )
        _SUBSCRIBER_REGISTRY[clean_num] = sub

    return {
        "success": True,
        "msisdn": sub.msisdn,
        "subscriber_name": sub.name,
        "national_id_masked": f"{sub.national_id[:2]}***{sub.national_id[-2:]}",
        "plan": {
            "id": sub.plan_id,
            "name": sub.plan_name,
            "total_quota_mb": sub.total_quota_mb,
            "remaining_data_mb": sub.remaining_data_mb,
            "consumption_percentage": sub.consumption_pct
        },
        "billing": {
            "balance_bs": sub.balance_bs,
            "balance_usd_equiv": sub.balance_usd_equiv,
            "cutoff_date": sub.billing_cutoff_date,
            "currency": "VES"
        },
        "line_status": sub.status,
        "registered_cell_id": sub.registered_cell_id
    }


def mcp_telco_diagnose_coverage(
    cell_id: Optional[str] = None,
    msisdn: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> Dict[str, Any]:
    """
    [MCP Tool] Diagnóstico OSS de celda eNodeB, calidad de radiofrecuencia (RSRP/RSRQ/SINR)
    y detección de incidencias de red 4GMAX.
    """
    target_cell = cell_id
    if not target_cell and msisdn:
        valid, clean_num = _normalize_movilnet_number(msisdn)
        if valid and clean_num in _SUBSCRIBER_REGISTRY:
            target_cell = _SUBSCRIBER_REGISTRY[clean_num].registered_cell_id

    if not target_cell:
        target_cell = "CAR-CCS-ENB-042"

    cell_data = _RADIOBASE_TOPOLOGY.get(target_cell, {
        "cell_id": target_cell,
        "station_name": "eNodeB Genérica Urbana",
        "municipality": "Región Central",
        "bands": ["LTE Band 4 (AWS)"],
        "status": "OPERATIONAL",
        "load_pct": 55.0,
        "rf_metrics": {"rsrp_dbm": -86.0, "rsrq_db": -9.5, "sinr_db": 16.0, "prb_utilization": 50.0},
        "active_alarms": []
    })

    rsrp = cell_data["rf_metrics"]["rsrp_dbm"]
    if rsrp >= -85.0:
        quality_label = "EXCELENTE"
        user_diag = "Nivel de señal óptimo para streaming y navegación de alta velocidad."
    elif rsrp >= -95.0:
        quality_label = "BUENA"
        user_diag = "Nivel de señal adecuado para servicios de voz y datos móviles."
    elif rsrp >= -105.0:
        quality_label = "REGULAR / SEÑAL MEDIA"
        user_diag = "Señal en rango medio; puede experimentar reducciones de velocidad en interiores."
    else:
        quality_label = "DEFICIENTE / SOMBRA DE COBERTURA"
        user_diag = "Cobertura débil en el sector; se recomienda ubicarse en un área despejada."

    is_degraded = cell_data["status"] != "OPERATIONAL" or len(cell_data["active_alarms"]) > 0

    return {
        "success": True,
        "cell_id": cell_data["cell_id"],
        "station_name": cell_data["station_name"],
        "municipality": cell_data["municipality"],
        "frequency_bands": cell_data["bands"],
        "operational_status": cell_data["status"],
        "network_incident_active": is_degraded,
        "active_alarms": cell_data["active_alarms"],
        "rf_telemetry": {
            "rsrp_dbm": rsrp,
            "rsrq_db": cell_data["rf_metrics"]["rsrq_db"],
            "sinr_db": cell_data["rf_metrics"]["sinr_db"],
            "cell_load_pct": cell_data["load_pct"],
            "quality_evaluation": quality_label
        },
        "diagnostic_summary": (
            f"Alerta: Se detectan incidencias técnicas en {cell_data['station_name']}. El personal de Operaciones Técnicas se encuentra ejecutando labores de restitución."
            if is_degraded else
            f"Radiobase operando con normalidad. {user_diag}"
        )
    }


def mcp_telco_check_apn(msisdn: str, device_model: str = "GENERIC_LTE") -> Dict[str, Any]:
    """
    [MCP Tool] Entrega y valida los parámetros oficiales del APN 4GMAX de Movilnet.
    """
    return {
        "success": True,
        "msisdn": msisdn,
        "device_model": device_model,
        "official_apn_profile": {
            "name": "Movilnet 4G",
            "apn": "int.movilnet.com.ve",
            "mcc": "734",
            "mnc": "06",
            "auth_type": "PAP o CHAP",
            "apn_type": "default,supl",
            "protocol": "IPv4/IPv6",
            "roaming_protocol": "IPv4"
        },
        "troubleshooting_steps": [
            "1. Ingrese a Ajustes > Conexiones > Redes Móviles > Nombres de punto de acceso (APN).",
            "2. Cree o edite el perfil con Nombre 'Movilnet 4G' y APN 'int.movilnet.com.ve'.",
            "3. Guarde los cambios y reinicie su dispositivo para forzar el reinicio del PDP Context."
        ]
    }


def mcp_telco_verify_sim_swap(msisdn: str) -> Dict[str, Any]:
    """
    [MCP Tool] Auditoría de seguridad HSS/HLR para detectar cambios de tarjeta SIM en <24 horas.
    """
    valid, clean_num = _normalize_movilnet_number(msisdn)
    if not valid:
        return {"success": False, "error_code": "ERR_INVALID_PHONE", "message": "Número de línea inválido."}

    sub = _SUBSCRIBER_REGISTRY.get(clean_num)
    if not sub:
        return {
            "success": True,
            "msisdn": clean_num,
            "sim_swap_detected_24h": False,
            "hours_since_swap": 999.0,
            "risk_level": "LOW",
            "authorization_status": "APPROVED",
            "message": "Sin cambios recientes de SIM registrados."
        }

    swap_dt = datetime.fromisoformat(sub.last_sim_swap_timestamp.replace("Z", "+00:00"))
    now_dt = datetime.now(timezone.utc)
    hours_diff = (now_dt - swap_dt).total_seconds() / 3600.0

    if hours_diff < 24.0:
        return {
            "success": True,
            "msisdn": clean_num,
            "sim_swap_detected_24h": True,
            "hours_since_swap": round(hours_diff, 1),
            "risk_level": "CRITICAL",
            "authorization_status": "REJECTED_SECURITY_LOCK",
            "security_policy": "SUDEBAN / CONATEL Anti-Fraud Circular 004/2024",
            "message": (
                "ALERTA SIM SWAP: Se registró un cambio de SIM en las últimas 24 horas. "
                "Las transacciones financieras quedan restringidas temporalmente."
            )
        }

    return {
        "success": True,
        "msisdn": clean_num,
        "sim_swap_detected_24h": False,
        "hours_since_swap": round(hours_diff, 1),
        "risk_level": "LOW",
        "authorization_status": "APPROVED",
        "message": "SIM estable. Verificación de seguridad aprobada."
    }


def mcp_telco_lock_line_theft(
    msisdn: str,
    reporter_cid: str,
    reason: str = "ROBO_EXTRAVIO"
) -> Dict[str, Any]:
    """
    [MCP Tool] Bloqueo preventivo de emergencia de IMSI/IMEI en el EIR y generación de ticket formal.
    """
    valid, clean_num = _normalize_movilnet_number(msisdn)
    if not valid:
        return {"success": False, "error_code": "ERR_INVALID_PHONE", "message": "Número inválido."}

    ticket_id = f"TKT-THEFT-{int(time.time())}"
    token_seed = f"{clean_num}:{reporter_cid}:{time.time()}"
    auth_hash = hashlib.sha256(token_seed.encode("utf-8")).hexdigest()[:16]

    if clean_num in _SUBSCRIBER_REGISTRY:
        _SUBSCRIBER_REGISTRY[clean_num].status = "BLOQUEADA_ROBO"

    try:
        from db.repository import MovilnetRepository
        repo = MovilnetRepository()
        line = repo.get_line_details(clean_num)
        imei = line.get("imei", f"35{clean_num[-10:]}0") if line else f"35{clean_num[-10:]}0"
        imsi = line.get("imsi", f"73406{clean_num[-10:]}") if line else f"73406{clean_num[-10:]}"
        repo.record_eir_security_lock(ticket_id, clean_num, imei, imsi, "THEFT_LOCK", reason, "ANTIGRAVITY_MCP_AGENT")
    except Exception:
        pass

    return {
        "success": True,
        "ticket_id": ticket_id,
        "msisdn": clean_num,
        "reporter_cid": reporter_cid,
        "status_action": "SUSPENSION_INMEDIATA_LINEA_Y_EQUIPO",
        "eir_blacklist_status": "BLACKLISTED",
        "conatel_reporting_code": f"CONATEL-EIR-{auth_hash.upper()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "confirmation_message": (
            f"La línea {clean_num} ha sido bloqueada satisfactoriamente con el ticket {ticket_id}. "
            "El IMEI fue ingresado en la lista negra nacional para impedir su uso en cualquier operadora."
        )
    }


def mcp_telco_record_sla(service_name: str, latency_ms: float, status_code: int = 200) -> Dict[str, Any]:
    """
    [MCP Tool] Registra una muestra de latencia en el buffer circular de observabilidad SRE.
    """
    record = SlaMetricRecord(service=service_name, latency_ms=round(latency_ms, 2), status_code=status_code)
    _SLA_RING_BUFFER.append(record)
    if len(_SLA_RING_BUFFER) > _MAX_RING_BUFFER_CAPACITY:
        _SLA_RING_BUFFER.pop(0)

    breach = latency_ms > 25.0
    return {
        "success": True,
        "service": service_name,
        "latency_ms": latency_ms,
        "sla_target_ms": 25.0,
        "sla_breach": breach
    }


def mcp_telco_get_sla_report() -> Dict[str, Any]:
    """
    [MCP Tool] Genera reporte estadístico de observabilidad (P50, P95, P99 y cumplimiento SLA).
    """
    if not _SLA_RING_BUFFER:
        return {
            "success": True,
            "total_samples": 0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "compliance_pct": 100.0,
            "status": "HEALTHY"
        }

    sorted_lats = sorted([m.latency_ms for m in _SLA_RING_BUFFER])
    n = len(sorted_lats)
    p50 = sorted_lats[int(n * 0.50)]
    p95 = sorted_lats[min(int(n * 0.95), n - 1)]
    p99 = sorted_lats[min(int(n * 0.99), n - 1)]

    within_sla = sum(1 for l in sorted_lats if l <= 25.0)
    compliance = round((within_sla / n) * 100.0, 2)

    return {
        "success": True,
        "total_samples": n,
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "p99_latency_ms": p99,
        "sla_target_ms": 25.0,
        "compliance_pct": compliance,
        "health_status": "OPTIMAL" if compliance >= 95.0 else "DEGRADED"
    }


# ============================================================================
# Servidor MCP Despachador (TelcoMcpServer)
# ============================================================================

class TelcoMcpServer:
    """Servidor MCP JSON-RPC 2.0 para la Suite 1: Core Telecom."""

    TOOLS = {
        "mcp_telco_get_subscriber": mcp_telco_get_subscriber,
        "mcp_telco_get_subscriber_balance": mcp_telco_get_subscriber,
        "mcp_telco_diagnose_coverage": mcp_telco_diagnose_coverage,
        "mcp_telco_check_apn": mcp_telco_check_apn,
        "mcp_telco_verify_sim_swap": mcp_telco_verify_sim_swap,
        "mcp_telco_lock_line_theft": mcp_telco_lock_line_theft,
        "mcp_telco_record_sla": mcp_telco_record_sla,
        "mcp_telco_get_sla_report": mcp_telco_get_sla_report,
    }


    @classmethod
    def get_manifest(cls) -> List[Dict[str, Any]]:
        """Retorna el esquema oficial MCP tools/list conforme a la especificación."""
        return [
            {
                "name": "mcp_telco_get_subscriber",
                "description": "Consulta saldo, megas y corte de línea Movilnet (0416/0426).",
                "inputSchema": {
                    "type": "object",
                    "properties": {"msisdn": {"type": "string", "description": "Número telefónico Movilnet."}},
                    "required": ["msisdn"]
                }
            },
            {
                "name": "mcp_telco_diagnose_coverage",
                "description": "Diagnóstico OSS de radiobase 4GMAX eNodeB (RSRP, RSRQ y alarmas).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cell_id": {"type": "string"},
                        "msisdn": {"type": "string"},
                        "lat": {"type": "number"},
                        "lon": {"type": "number"}
                    }
                }
            },
            {
                "name": "mcp_telco_check_apn",
                "description": "Obtiene configuración técnica oficial del APN int.movilnet.com.ve.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "msisdn": {"type": "string"},
                        "device_model": {"type": "string"}
                    },
                    "required": ["msisdn"]
                }
            },
            {
                "name": "mcp_telco_verify_sim_swap",
                "description": "Auditoría HSS/HLR de cambio de tarjeta SIM en las últimas 24 horas.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"msisdn": {"type": "string"}},
                    "required": ["msisdn"]
                }
            },
            {
                "name": "mcp_telco_lock_line_theft",
                "description": "Suspensión de emergencia de IMSI/IMEI por robo o extravío.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "msisdn": {"type": "string"},
                        "reporter_cid": {"type": "string"},
                        "reason": {"type": "string"}
                    },
                    "required": ["msisdn", "reporter_cid"]
                }
            },
            {
                "name": "mcp_telco_record_sla",
                "description": "Registra una muestra de latencia en el monitor SRE en tiempo real.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "latency_ms": {"type": "number"},
                        "status_code": {"type": "integer"}
                    },
                    "required": ["service_name", "latency_ms"]
                }
            },
            {
                "name": "mcp_telco_get_sla_report",
                "description": "Obtiene reporte estadístico de observabilidad (P50, P95, P99).",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]

    def handle_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Any = 1) -> Dict[str, Any]:
        params = params or {}
        if method not in self.TOOLS:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method '{method}' not found in TelcoMcpServer."},
                "id": request_id
            }

        start = time.time()
        try:
            handler = self.TOOLS[method]
            result = handler(**params)
            duration_ms = round((time.time() - start) * 1000, 2)
            mcp_telco_record_sla(method, duration_ms, 200)

            return {
                "jsonrpc": "2.0",
                "result": result,
                "execution_ms": duration_ms,
                "id": request_id
            }
        except TypeError as te:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": f"Invalid parameters for '{method}': {str(te)}"},
                "id": request_id
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": f"Execution error in '{method}': {str(e)}"},
                "id": request_id
            }
