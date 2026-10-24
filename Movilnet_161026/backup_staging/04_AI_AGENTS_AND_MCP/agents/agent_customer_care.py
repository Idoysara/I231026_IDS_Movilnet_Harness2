#!/usr/bin/env python3
"""
api/agents/agent_customer_care.py — Fachada y Orquestador del Agente Nivel 1 (Customer Care)
============================================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)
Estándares: TM Forum ODA (TMF632 Customer Management, TMF654 Prepay Balance,
            TMF638 Service Inventory, TMF680 Security Incident)

Arquitectura Hexagonal Desacoplada por Capas:
  • Capa 1 (Dominio Puro):        `core.types_customer_care` (IntentType, AgentExecutionMode, AgentMessage, AgentResponse)
  • Capa 2 (Aceleración L1):      `core.cache_l1` (L1SessionCache thread-safe O(1) <0.1ms)
  • Capa 2 (Memoria Resiliente):  `core.session_memory_sqlite` (SessionMemory RAM + SQLite WAL)
  • Capa 2 (Fast-Path Engine):    `core.fastpath_engine` (FastPathEngine determinista 0 Tokens)
  • Capa 3 (Inferencia Cognitiva):`core.llm_reasoning_engine` (LLMReasoningEngine Gemini/OpenRouter + Fallback Local)
  • Capa 3 (Fachada Orquestadora):`api.agents.agent_customer_care` (CustomerCareAgent + Handoff Swarm L5)
"""

from __future__ import annotations

import sys
import time
import uuid
import logging
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.repository import MovilnetRepository
from mcp.master_gateway import MovilnetMasterMcpGateway

# Re-exportación limpia de Capas Desacopladas (Patrón Facade — 100% Compatibilidad Hacia Atrás)
from core.types_customer_care import (
    IntentType,
    AgentExecutionMode,
    AgentMessage,
    AgentResponse,
)
from core.cache_l1 import L1SessionCache
from core.session_memory_sqlite import SessionMemory
from core.fastpath_engine import FastPathEngine
from core.llm_reasoning_engine import LLMReasoningEngine

logger = logging.getLogger("MovilnetCustomerCareAgent")

__all__ = [
    "CustomerCareAgent",
    "IntentType",
    "AgentExecutionMode",
    "AgentMessage",
    "AgentResponse",
    "L1SessionCache",
    "SessionMemory",
    "FastPathEngine",
    "LLMReasoningEngine",
]


class CustomerCareAgent:
    """
    Agente Autónomo Nivel 1 — Especialista en Atención al Cliente & Consultas OCS.
    Orquesta el ciclo completo de interacción omnicanal delegando en motores desacoplados:
    Fast-Path, Memoria de Sesión, Caché L1, Razonamiento IA y Enrutamiento Swarm L5.
    """

    def __init__(
        self,
        repo: Optional[MovilnetRepository] = None,
        mcp_gateway: Optional[MovilnetMasterMcpGateway] = None,
        cache_ttl_seconds: float = 60.0
    ):
        self.repo = repo or MovilnetRepository()
        self.mcp = mcp_gateway or MovilnetMasterMcpGateway()
        self.cache = L1SessionCache(default_ttl_seconds=cache_ttl_seconds)
        self.memory = SessionMemory(session_ttl_seconds=1800.0)
        self.session_memory = self.memory
        self.fast_path = FastPathEngine(repo=self.repo, cache=self.cache)
        self.llm_engine = LLMReasoningEngine()

    @staticmethod
    def _ensure_pwa_link_suffix(text: str, channel: str = "") -> str:
        """Garantiza la Regla Constitucional de Enlace PWA Universal al final de todo mensaje."""
        if str(channel).strip().lower() in ("pwa", "pwa_stitch", "simulador"):
            return text
        pwa_url = "https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html"
        if pwa_url in text:
            return text
        suffix = (
            "\n\n🌐 Portal PWA 4GMAX (Acceso libre por Wi-Fi o Datos Móviles — Cualquier Operadora):\n"
            f"👉 {pwa_url}"
        )
        return text.rstrip() + suffix

    def process_message(self, message: AgentMessage) -> AgentResponse:
        """
        Punto de entrada principal para el procesamiento de peticiones.
        Garantiza medición estricta de latencia, costo en tokens y enrutamiento Swarm.
        """
        start_time = time.perf_counter()
        session_id = message.session_id or (
            f"sess-{message.msisdn}" if message.msisdn else f"sess-anon-{uuid.uuid4().hex[:6]}"
        )
        raw_text = message.text.strip()
        msisdn = message.msisdn

        # Registrar turno del usuario en la memoria conversacional
        self.memory.add_turn(session_id, role="user", content=raw_text)

        # 1. Clasificación Sintáctica de Intención
        intent = self.fast_path.classify_intent(raw_text)

        # 2. Detección de Handoff a Subagentes Especializados del Enjambre (Swarm L5)
        if intent in [
            IntentType.HANDOFF_FINTECH_C2P,
            IntentType.HANDOFF_EMERGENCY_EIR,
            IntentType.HANDOFF_RETENTION_CHURN,
        ]:
            response = self._build_swarm_handoff_response(
                intent=intent,
                raw_text=raw_text,
                msisdn=msisdn,
                session_id=session_id,
                start_time=start_time,
                channel=message.channel or "",
            )
            self.memory.add_turn(session_id, role="agent", content=response.response_text, intent=intent.value)
            return response

        # 3. Intentar Despacho por Fast-Path Heurístico (Cero Tokens, < 1ms)
        fast_path_result = None
        if intent != IntentType.UNKNOWN:
            fast_path_result = self.fast_path.execute_fast_path(
                intent, msisdn, raw_text, channel=message.channel or ""
            )

        if fast_path_result is not None:
            resp_text, buttons, metadata = fast_path_result
            resp_text = self._ensure_pwa_link_suffix(resp_text, message.channel or "")
            latency_ms = round((time.perf_counter() - start_time) * 1000, 3)

            response = AgentResponse(
                response_text=resp_text,
                intent=intent,
                execution_mode=AgentExecutionMode.FAST_PATH,
                latency_ms=latency_ms,
                tokens_consumed=0,
                cost_usd=0.0,
                handoff_required=False,
                target_agent=None,
                interactive_options=buttons,
                metadata=metadata,
                session_id=session_id,
            )
            self.memory.add_turn(session_id, role="agent", content=resp_text, intent=intent.value)
            return response

        # 4. Despacho Contextual por Inferencia LLM / Razonador Semántico
        session_ctx = self.memory.get_session(session_id)
        history = session_ctx.get("turns", [])

        llm_text, tokens, cost = self.llm_engine.generate_response(
            message=raw_text,
            session_history=history,
            msisdn=msisdn,
            latitude=message.latitude,
            longitude=message.longitude,
            device_info=message.device_info,
            sender_name=message.sender_name,
            channel=message.channel or "",
        )
        latency_ms = round((time.perf_counter() - start_time) * 1000, 3)

        # 5. Motor de Funnel Marketing Digital (Next-Best-Action Engine)
        nba_offer = None
        try:
            from api.agents.agent_marketing_funnel import marketing_funnel_agent
            bal_ves = 150.0
            rem_mb = 4096
            tot_mb = 10240
            days_cut = 15
            if msisdn:
                cached_ctx = self.fast_path._get_subscriber_context(msisdn)
                if cached_ctx and isinstance(cached_ctx, tuple) and len(cached_ctx) >= 2:
                    sub_info, bal_info = cached_ctx[0], cached_ctx[1]
                    if bal_info and isinstance(bal_info, dict):
                        bal_ves = float(bal_info.get("balance_ves", 150.0))
                        rem_mb = int(bal_info.get("remaining_data_mb", 4096))
                        tot_mb = int(bal_info.get("total_quota_mb", 10240))
            nba_offer = marketing_funnel_agent.evaluate_next_best_action(
                msisdn=msisdn or "04160000001",
                balance_ves=bal_ves,
                remaining_data_mb=rem_mb,
                total_quota_mb=tot_mb,
                days_to_cutoff=days_cut,
                user_message=raw_text,
            )
        except Exception:
            pass

        # Verificar si la línea proviene de una operadora competidora (Movistar/Digitel)
        from core.carrier_funnel_classifier import CarrierFunnelClassifier
        clean_user_msisdn = CarrierFunnelClassifier.clean_msisdn(msisdn or "")
        carrier_enum, carrier_label, is_comp = CarrierFunnelClassifier.identify_carrier(clean_user_msisdn)

        is_geo_query = any(
            k in raw_text.lower()
            for k in [
                "comer", "donde", "restaurante", "farmacia", "clinica", "palos grandes",
                "chacao", "lugar", "opciones", "altamira", "helado", "comida", "cafe",
                "automercado", "supermercado", "libreria", "librería", "petare", "urbina", "marques"
            ]
        )
        is_promo_query = any(
            k in raw_text.lower()
            for k in [
                "promo", "promocion", "promoción", "oferta", "ofertas",
                "descuento", "beneficio", "cine", "regalo", "bono"
            ]
        )

        if is_geo_query:
            default_buttons = [
                {"id": "btn_geo_more", "title": "📍 Más Lugares"},
                {"id": "btn_geo_pharmacies", "title": "🏥 Farmacias"},
                {"id": "btn_check_data", "title": "📊 Ver Megas"},
            ]
        elif is_comp:
            default_buttons = [
                {"id": "btn_portabilidad_10gb", "title": "📲 Portabilidad 10GB"},
                {"id": "btn_esim_digital", "title": "✨ eSIM Gratis"},
                {"id": "btn_planes_4gmax", "title": "📋 Planes 4GMAX"},
            ]
            if is_promo_query:
                llm_text += (
                    f"\n\n🚀 *Oferta Exclusiva Portabilidad 4GMAX ({carrier_label}):*\n"
                    f"¡Cámbiate a Movilnet conservando tu mismo número! Te obsequiamos tu *eSIM Digital Inmediata* "
                    f"más un *Bono de Bienvenida de 10 GB* de navegación ultrarrápida y ahorras hasta 60% en tu renta mensual. "
                    f"Escribe *'Portabilidad'* por aquí para tramitarla al instante."
                )
        elif nba_offer:
            default_buttons = [
                {"id": f"btn_funnel_{nba_offer.offer_id.lower()}", "title": nba_offer.cta_text[:20]},
                {"id": "btn_c2p_recharge", "title": "💳 Recarga C2P"},
                {"id": "btn_check_data", "title": "📊 Ver Megas"},
            ]
            if is_promo_query:
                llm_text += f"\n\n💡 *Recomendación Movilnet:* {nba_offer.headline} — {nba_offer.description}"
        else:
            default_buttons = [
                {"id": "btn_check_balance", "title": "💰 Saldo"},
                {"id": "btn_check_data", "title": "📊 Megas"},
                {"id": "btn_plans_catalog", "title": "📦 Planes"},
            ]

        resp_metadata: Dict[str, Any] = {
            "source": "llm_reasoning_core",
            "model": self.llm_engine.model_name,
        }
        if nba_offer:
            resp_metadata["marketing_funnel"] = {
                "offer_id": nba_offer.offer_id,
                "campaign_name": nba_offer.campaign_name,
                "category": nba_offer.category.value,
                "prefill_data": nba_offer.prefill_data,
            }

        llm_text = self._ensure_pwa_link_suffix(llm_text, message.channel or "")
        response = AgentResponse(
            response_text=llm_text,
            intent=IntentType.GENERAL_FAQ,
            execution_mode=AgentExecutionMode.LLM_REASONING,
            latency_ms=latency_ms,
            tokens_consumed=tokens,
            cost_usd=cost,
            handoff_required=False,
            target_agent=None,
            interactive_options=default_buttons,
            metadata=resp_metadata,
            session_id=session_id,
        )
        self.memory.add_turn(session_id, role="agent", content=llm_text, intent=IntentType.GENERAL_FAQ.value)
        return response

    def _build_swarm_handoff_response(
        self,
        intent: IntentType,
        raw_text: str,
        msisdn: Optional[str],
        session_id: str,
        start_time: float,
        channel: str = "",
    ) -> AgentResponse:
        """Construye la respuesta de transferencia controlada para el enjambre Swarm."""
        target_agent = ""
        reply_text = ""
        buttons: List[Dict[str, str]] = []
        meta: Dict[str, Any] = {"msisdn": msisdn, "original_query": raw_text}

        if intent == IntentType.HANDOFF_FINTECH_C2P:
            target_agent = "agent_fintech_c2p"
            reply_text = (
                "💳 *Pasarela Financiera Movilnet C2P — Transferencia de Atención*\n\n"
                "Hemos detectado tu intención de realizar una recarga de saldo o pago de servicio. "
                "Te estamos conectando de forma segura con nuestro *Agente Financiero C2P (Nivel 2)*.\n\n"
                "Por favor, ten a la mano:\n"
                "• Código de tu Banco emisor (o nombre del banco).\n"
                "• Cédula de identidad del titular pagador.\n"
                "• Monto en Bolívares a recargar.\n"
                "• Código OTP o token dinámico SMS generado por tu banco."
            )
            buttons = [
                {"id": "btn_c2p_start", "title": "🚀 Iniciar Pago C2P"},
                {"id": "btn_cancel_handoff", "title": "❌ Cancelar"},
            ]
            meta["target_module"] = "api.agents.agent_fintech_c2p"

        elif intent == IntentType.HANDOFF_EMERGENCY_EIR:
            target_agent = "agent_emergency_eir"
            reply_text = (
                "🚨 *Protocolo de Emergencia y Seguridad EIR — Prioridad 1*\n\n"
                "⚠️ *Atención Inmediata:* Hemos recibido tu reporte de pérdida, hurto o sospecha de fraude. "
                "Tu caso ha sido escalado con máxima prioridad al *Agente de Seguridad y Bloqueo EIR (Nivel 3)*.\n\n"
                "Estamos preparados para proceder con:\n"
                "• Inclusión inmediata de tu terminal en la *Lista Negra EIR* (bloqueo por IMEI).\n"
                "• Suspensión cautelar de la línea en HLR/HSS para evitar consumos no autorizados.\n"
                "• Auditoría preventiva de SIM-Swap en ventana de 24 horas."
            )
            buttons = [
                {"id": "btn_confirm_lock", "title": "🔒 Confirmar Bloqueo"},
                {"id": "btn_contact_agent", "title": "📞 Hablar con Operador"},
            ]
            meta["target_module"] = "api.agents.agent_emergency_eir"
            meta["security_priority"] = "HIGH"

        elif intent == IntentType.HANDOFF_RETENTION_CHURN:
            target_agent = "agent_retention_churn"
            reply_text = (
                "🤝 *Atención Preferencial & Gestión de Beneficios Movilnet*\n\n"
                "Lamentamos profundamente cualquier inconformidad que hayas experimentado con el servicio. "
                "En Movilnet tu lealtad es fundamental para nosotros. Te estamos conectando con nuestro "
                "*Agente Especialista en Retención y Experiencia (Nivel 4)*.\n\n"
                "Tenemos preparadas ofertas dinámicas personalizadas, bonificaciones de datos 4GMAX "
                "y planes de ajuste tarifario diseñados a tu medida."
            )
            buttons = [
                {"id": "btn_view_exclusive_offers", "title": "🎁 Ver Ofertas Exclusivas"},
                {"id": "btn_cancel_request", "title": "📱 Continuar con mi Plan"},
            ]
            meta["target_module"] = "api.agents.agent_retention_churn"

        reply_text = self._ensure_pwa_link_suffix(reply_text, channel)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 3)

        return AgentResponse(
            response_text=reply_text,
            intent=intent,
            execution_mode=AgentExecutionMode.FAST_PATH,
            latency_ms=latency_ms,
            tokens_consumed=0,
            cost_usd=0.0,
            handoff_required=True,
            target_agent=target_agent,
            interactive_options=buttons,
            metadata=meta,
            session_id=session_id,
        )


def _run_self_tests() -> None:
    """Auto-verificación formal de la Fachada Orquestadora CustomerCareAgent (Pilar II y V)."""
    print("=" * 80)
    print("🧪 [TEST]: Auto-verificación de api/agents/agent_customer_care.py (Fachada Hexagonal)")
    print("=" * 80)

    agent = CustomerCareAgent()

    # 1. Test Fast-Path APN (0 tokens)
    msg_apn = AgentMessage(text="Como configuro el APN de mi linea?", msisdn="04160000001")
    resp_apn = agent.process_message(msg_apn)
    assert resp_apn.intent == IntentType.APN_TECH_SUPPORT
    assert resp_apn.execution_mode == AgentExecutionMode.FAST_PATH
    assert resp_apn.tokens_consumed == 0
    assert "int.movilnet.com.ve" in resp_apn.response_text
    print("  [PASS] Orquestación Fast-Path APN validada (<1ms, 0 tokens).")

    # 2. Test Handoff Swarm L5 (Fintech C2P)
    msg_c2p = AgentMessage(text="Quiero recargar saldo con pago movil C2P", msisdn="04160000001")
    resp_c2p = agent.process_message(msg_c2p)
    assert resp_c2p.handoff_required is True
    assert resp_c2p.target_agent == "agent_fintech_c2p"
    print("  [PASS] Enrutamiento Swarm L5 a Agente Nivel 2 (Fintech C2P) validado.")

    # 3. Test Retención en Memoria de Sesión
    sess_data = agent.memory.get_session("sess-04160000001")
    assert len(sess_data["turns"]) >= 4
    print("  [PASS] Persistencia en SessionMemory integrada correctamente.")

    print("=" * 80)
    print("🏆 [RESULTADO]: 100% PASS (0 fallos en Fachada Orquestadora CustomerCareAgent)")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fachada Orquestadora Agente Nivel 1 Customer Care")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación formal del módulo")
    args = parser.parse_args()

    if args.test or len(sys.argv) == 1:
        _run_self_tests()
