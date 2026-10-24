#!/usr/bin/env python3
"""
core/types_customer_care.py — Capa de Dominio Puro: Tipos, Modelos y Enumeraciones
===================================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilar I & Pilar III)
Propósito: Entidades y DTOs puros sin dependencias de red, base de datos ni frameworks.
"""

from __future__ import annotations

import sys
import argparse
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class IntentType(str, Enum):
    """Catálogo de intenciones formales del Agente Nivel 1 (Customer Care)."""
    BALANCE_QUERY = "BALANCE_QUERY"
    DATA_QUOTA_QUERY = "DATA_QUOTA_QUERY"
    PLAN_QUERY = "PLAN_QUERY"
    LINE_STATUS_QUERY = "LINE_STATUS_QUERY"
    APN_TECH_SUPPORT = "APN_TECH_SUPPORT"
    OFFICE_LOCATION_QUERY = "OFFICE_LOCATION_QUERY"
    GOOGLE_SUITE_DISPATCH = "GOOGLE_SUITE_DISPATCH"
    HANDOFF_FINTECH_C2P = "HANDOFF_FINTECH_C2P"
    HANDOFF_EMERGENCY_EIR = "HANDOFF_EMERGENCY_EIR"
    HANDOFF_RETENTION_CHURN = "HANDOFF_RETENTION_CHURN"
    GENERAL_FAQ = "GENERAL_FAQ"
    UNKNOWN = "UNKNOWN"


class AgentExecutionMode(str, Enum):
    """Modo operacional de despacho del agente."""
    FAST_PATH = "FAST_PATH"
    LLM_REASONING = "LLM_REASONING"


@dataclass
class AgentMessage:
    """Mensaje entrante del abonado normalizado para el agente."""
    text: str
    msisdn: Optional[str] = None
    session_id: Optional[str] = None
    channel: str = "whatsapp"  # "whatsapp", "telegram", "web", "api"
    subscriber_cid: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    device_info: Optional[Dict[str, Any]] = None
    sender_name: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        """Invariantes de Dominio (Pilar III: Type Safety y Guardas de Frontera)."""
        if not isinstance(self.text, str):
            raise TypeError("El texto del mensaje debe ser de tipo str")
        if self.msisdn:
            self.msisdn = str(self.msisdn).strip()


@dataclass
class AgentResponse:
    """Respuesta estructurada emitida por el agente con telemetría Carrier-Grade."""
    response_text: str
    intent: IntentType
    execution_mode: AgentExecutionMode
    latency_ms: float
    tokens_consumed: int
    cost_usd: float
    handoff_required: bool
    target_agent: Optional[str] = None
    interactive_options: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialización a diccionario JSON serializable."""
        data = asdict(self)
        data["intent"] = self.intent.value if isinstance(self.intent, IntentType) else str(self.intent)
        data["execution_mode"] = self.execution_mode.value if isinstance(self.execution_mode, AgentExecutionMode) else str(self.execution_mode)
        return data


def _run_self_tests() -> None:
    """Auto-verificación formal con aserciones matemáticas y de invariantes (Pilar II)."""
    print("=" * 80)
    print("🧪 [TEST]: Auto-verificación de core/types_customer_care.py")
    print("=" * 80)

    # 1. Test DTO AgentMessage
    msg = AgentMessage(text="Consulta de saldo", msisdn="04161234567")
    assert msg.text == "Consulta de saldo"
    assert msg.msisdn == "04161234567"
    assert msg.channel == "whatsapp"
    print("  [PASS] AgentMessage Invariants: Creación y valores por defecto correctos.")

    # 2. Test DTO AgentResponse y to_dict
    resp = AgentResponse(
        response_text="Tu saldo es Bs. 150",
        intent=IntentType.BALANCE_QUERY,
        execution_mode=AgentExecutionMode.FAST_PATH,
        latency_ms=0.85,
        tokens_consumed=0,
        cost_usd=0.0,
        handoff_required=False,
        session_id="sess-test-01"
    )
    d = resp.to_dict()
    assert d["intent"] == "BALANCE_QUERY"
    assert d["execution_mode"] == "FAST_PATH"
    assert d["latency_ms"] == 0.85
    assert d["tokens_consumed"] == 0
    print("  [PASS] AgentResponse Serialization: to_dict() cumple esquema ODA.")

    # 3. Test Enumeraciones
    assert len(IntentType) >= 12
    assert IntentType.HANDOFF_FINTECH_C2P.value == "HANDOFF_FINTECH_C2P"
    print("  [PASS] IntentType Catalogs: 12 intenciones formales validadas.")

    print("=" * 80)
    print("🏆 [RESULTADO]: 100% PASS (0 fallos en Dominio Puro)")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tipos de Dominio Puro para Customer Care")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación formal del módulo")
    args = parser.parse_args()

    if args.test or len(sys.argv) == 1:
        _run_self_tests()
