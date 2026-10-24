#!/usr/bin/env python3
"""
mcp/crm_tools.py — Suite 3: CRM, Prevención de Churn & TM Forum ODA (TMF680/TMF620)
====================================================================================
Proyecto: AI_Movilnet_300926 / Antigravity Level 5 Architecture
Estándar: Model Context Protocol (MCP) JSON-RPC 2.0 & TM Forum Open Digital Architecture
Estándares ODA: TMF620 (Product Catalog Management) / TMF680 (Recommendation Management)

Herramientas MCP Expuestas:
  1. mcp_crm_get_product_catalog: Catálogo oficial de planes y paquetes 4GMAX (TMF620)
  2. mcp_crm_evaluate_churn_risk: Algoritmo predictivo de riesgo de abandono y deserción
  3. mcp_crm_recommend_offering: Motor de recomendación proactiva y paquetes contextuales (TMF680)
  4. mcp_crm_apply_retention_coupon: Activación y acreditación de bonos de fidelización
"""

from __future__ import annotations

import os
import sys
import json
import time
import math
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Modelos de Datos Tipados TM Forum ODA
# ============================================================================

@dataclass
class TMF620ProductOffering:
    id: str
    name: str
    category: str
    data_mb: int
    voice_minutes: int
    sms_count: int
    price_usd: float
    description: str
    is_active: bool = True


# ============================================================================
# Catálogo TM Forum TMF620 de Movilnet
# ============================================================================

_OFFICIAL_TMF620_CATALOG: List[TMF620ProductOffering] = [
    TMF620ProductOffering(
        id="PLAN_INTELIPLAN_10GB",
        name="Inteliplan 10GB 4GMAX",
        category="PLAN_BASE",
        data_mb=10240,
        voice_minutes=1000,
        sms_count=1000,
        price_usd=6.50,
        description="Plan mensual estándar con cobertura nacional ultrarrápida 4GMAX."
    ),
    TMF620ProductOffering(
        id="PLAN_INTELIPLAN_20GB",
        name="Inteliplan 20GB Pro 4GMAX",
        category="PLAN_BASE",
        data_mb=20480,
        voice_minutes=2000,
        sms_count=2000,
        price_usd=11.90,
        description="Plan de alta capacidad para usuarios intensivos de datos y streaming."
    ),
    TMF620ProductOffering(
        id="PLAN_CONECTA_PLUS",
        name="Conecta Plus 5GB",
        category="PLAN_BASE",
        data_mb=5120,
        voice_minutes=500,
        sms_count=500,
        price_usd=3.75,
        description="Plan económico de entrada para navegación y mensajería instantánea."
    ),
    TMF620ProductOffering(
        id="PKG_EXTRA_2GB",
        name="Paquete Extra 4GMAX 2GB",
        category="ADDON_DATA",
        data_mb=2048,
        voice_minutes=0,
        sms_count=0,
        price_usd=1.75,
        description="Bolsa adicional de 2GB de datos para recarga inmediata al agotarse el cupo."
    ),
    TMF620ProductOffering(
        id="PKG_EXTRA_5GB",
        name="Paquete Extra 4GMAX 5GB",
        category="ADDON_DATA",
        data_mb=5120,
        voice_minutes=0,
        sms_count=0,
        price_usd=3.50,
        description="Bolsa extendida de 5GB de datos para continuidad operativa sin interrupciones."
    ),
    TMF620ProductOffering(
        id="PKG_NOCHE_ILIMITADA",
        name="Paquete Noches Libres 4GMAX",
        category="ADDON_SPECIAL",
        data_mb=50000,
        voice_minutes=0,
        sms_count=0,
        price_usd=2.00,
        description="Navegación ilimitada nocturna desde las 11:00 PM hasta las 6:00 AM."
    )
]

# Registro de cupones de fidelización asignados
_APPLIED_RETENTION_COUPONS: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Herramientas MCP Suite 3
# ============================================================================

def mcp_crm_get_product_catalog(category: Optional[str] = None) -> Dict[str, Any]:
    """
    [MCP Tool: TM Forum TMF620]
    Retorna el catálogo oficial de planes y paquetes comerciales activos de Movilnet.
    """
    items = _OFFICIAL_TMF620_CATALOG
    if category:
        cat_upper = category.upper().strip()
        items = [p for p in items if p.category == cat_upper]

    serialized = [asdict(p) for p in items]
    return {
        "success": True,
        "standard": "TM_Forum_TMF620_ProductCatalog_v4",
        "total_offerings": len(serialized),
        "filter_category": category,
        "product_offerings": serialized
    }


def mcp_crm_evaluate_churn_risk(
    msisdn: str,
    days_unpaid: int = 15,
    complaint_tickets: int = 0,
    data_drop_pct: float = 0.0
) -> Dict[str, Any]:
    """
    [MCP Tool: telco-churn-predictor]
    Evalúa el riesgo de deserción del abonado mediante un modelo heurístico ponderado:
      - Antigüedad de pago vencido (peso 40%)
      - Frecuencia de incidencias técnicas reportadas (peso 35%)
      - Contracción en consumo habitual de datos (peso 25%)
    """
    # 1. Componente morosidad
    p_unpaid = min(40.0, (days_unpaid / 30.0) * 40.0)
    # 2. Componente insatisfacción técnica
    p_complaints = min(35.0, complaint_tickets * 11.5)
    # 3. Componente desuso
    p_drop = min(25.0, (data_drop_pct / 100.0) * 25.0)

    total_score = round(min(100.0, p_unpaid + p_complaints + p_drop), 1)

    if total_score >= 70.0:
        risk_tier = "CRITICAL_CHURN_RISK"
        action = "RESCUE_PROMO_50_OFF"
        benefit = "50% de descuento en la próxima mensualidad + 2GB de datos de cortesía."
    elif total_score >= 40.0:
        risk_tier = "MODERATE_CHURN_RISK"
        action = "LOYALTY_BONUS_1GB"
        benefit = "1GB adicional de cortesía por recargar antes de la fecha de corte."
    else:
        risk_tier = "HEALTHY_LOYAL"
        action = "VIP_CLUB_INVITE"
        benefit = "Acceso a sorteos y preventas exclusivas Movilnet."

    return {
        "success": True,
        "msisdn": msisdn,
        "churn_risk_score": total_score,
        "risk_tier": risk_tier,
        "evaluation_factors": {
            "days_unpaid": days_unpaid,
            "complaint_tickets": complaint_tickets,
            "data_consumption_drop": f"{data_drop_pct:.1f}%"
        },
        "retention_strategy": {
            "recommended_action": action,
            "subscriber_benefit": benefit,
            "urgency": "HIGH" if total_score >= 70 else "NORMAL"
        }
    }


def mcp_crm_recommend_offering(
    msisdn: str,
    remaining_mb: int = 350,
    current_plan: Optional[str] = None
) -> Dict[str, Any]:
    """
    [MCP Tool: TM Forum TMF680]
    Motor de Recomendación Contextual. Dispara ofertas proactivas en tiempo real
    si el cupo de datos del abonado entra en zona crítica (<500 MB).
    """
    if remaining_mb > 500:
        return {
            "success": True,
            "standard": "TM_Forum_TMF680_Recommendation_v4",
            "recommendation_triggered": False,
            "msisdn": msisdn,
            "message": "El abonado dispone de cupo suficiente de navegación. No se requiere oferta adicional."
        }

    # Recomendación óptima según perfil
    recommended_product = _OFFICIAL_TMF620_CATALOG[3]  # Paquete Extra 2GB
    return {
        "success": True,
        "standard": "TM_Forum_TMF680_Recommendation_v4",
        "recommendation_triggered": True,
        "trigger_event": "LOW_DATA_THRESHOLD_REACHED",
        "msisdn": msisdn,
        "current_quota_remaining_mb": remaining_mb,
        "recommended_offering": {
            "id": recommended_product.id,
            "name": recommended_product.name,
            "data_mb": recommended_product.data_mb,
            "price_usd": recommended_product.price_usd,
            "payment_flow": "PAGO_MOVIL_C2P"
        },
        "conversational_call_to_action": (
            f"Te quedan solo {remaining_mb} MB disponibles. "
            f"¿Deseas activar un {recommended_product.name} por ${recommended_product.price_usd:.2f} USD "
            "vía Pago Móvil para continuar navegando a máxima velocidad 4GMAX?"
        )
    }


def mcp_crm_apply_retention_coupon(
    msisdn: str,
    offer_id: str,
    channel: str = "WHATSAPP_BOT"
) -> Dict[str, Any]:
    """
    [MCP Tool] Aplica y acredita un beneficio de retención en la línea del abonado.
    """
    coupon_id = f"CPN-{int(time.time())}-{hashlib.md5(f'{msisdn}:{offer_id}'.encode()).hexdigest()[:6].upper()}"
    record = {
        "coupon_id": coupon_id,
        "msisdn": msisdn,
        "offer_id": offer_id,
        "channel": channel,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "status": "APPLIED_ACTIVE"
    }
    _APPLIED_RETENTION_COUPONS[coupon_id] = record

    return {
        "success": True,
        "coupon_id": coupon_id,
        "msisdn": msisdn,
        "offer_id": offer_id,
        "status": "BENEFIT_ACCREDITED",
        "message": f"Beneficio '{offer_id}' acreditado exitosamente a la línea {msisdn} con cupón {coupon_id}."
    }


# ============================================================================
# Servidor MCP Despachador (CrmRetentionMcpServer)
# ============================================================================

class CrmRetentionMcpServer:
    """Servidor MCP JSON-RPC 2.0 para la Suite 3: CRM y Retención TM Forum."""

    TOOLS = {
        "mcp_crm_get_product_catalog": mcp_crm_get_product_catalog,
        "mcp_crm_evaluate_churn_risk": mcp_crm_evaluate_churn_risk,
        "mcp_crm_recommend_offering": mcp_crm_recommend_offering,
        "mcp_crm_apply_retention_coupon": mcp_crm_apply_retention_coupon,
    }

    @classmethod
    def get_manifest(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "mcp_crm_get_product_catalog",
                "description": "Retorna el catálogo TM Forum TMF620 de planes y paquetes 4GMAX.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"category": {"type": "string"}}
                }
            },
            {
                "name": "mcp_crm_evaluate_churn_risk",
                "description": "Calcula el riesgo de abandono y sugiere estrategia de fidelización.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "msisdn": {"type": "string"},
                        "days_unpaid": {"type": "integer"},
                        "complaint_tickets": {"type": "integer"},
                        "data_drop_pct": {"type": "number"}
                    },
                    "required": ["msisdn"]
                }
            },
            {
                "name": "mcp_crm_recommend_offering",
                "description": "Motor de recomendación contextual TM Forum TMF680 ante cupo de datos crítico.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "msisdn": {"type": "string"},
                        "remaining_mb": {"type": "integer"},
                        "current_plan": {"type": "string"}
                    },
                    "required": ["msisdn"]
                }
            },
            {
                "name": "mcp_crm_apply_retention_coupon",
                "description": "Acredita un cupón de retención a la línea del abonado.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "msisdn": {"type": "string"},
                        "offer_id": {"type": "string"},
                        "channel": {"type": "string"}
                    },
                    "required": ["msisdn", "offer_id"]
                }
            }
        ]

    def handle_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Any = 1) -> Dict[str, Any]:
        params = params or {}
        if method not in self.TOOLS:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method '{method}' not found in CrmRetentionMcpServer."},
                "id": request_id
            }

        start = time.time()
        try:
            handler = self.TOOLS[method]
            result = handler(**params)
            duration_ms = round((time.time() - start) * 1000, 2)

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
