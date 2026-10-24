#!/usr/bin/env python3
"""
agent_n8n_dispatcher.py — Subagente Despachador Bidireccional n8n ↔ Movilnet Core
================================================================================
Maneja el ciclo completo:
Movilnet (Abonado) ↔ Input (n8n) ↔ Nodos (n8n) ↔ Output (n8n) ↔ Movilnet
"""

import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.n8n_webhook_payload_extractor import N8nWebhookPayloadExtractor, NormalizedInboundMessage
from db.repository import MovilnetRepository


@dataclass
class N8nEgressMessage:
    """Modelo formal de salida estructurada hacia el nodo HTTP Request de n8n."""
    instance_id: str
    recipient_jid: str
    text_content: str
    delay_ms: int = 1500
    source_intent: str = "UNKNOWN"
    latency_mode: str = "FAST_PATH"

    def to_evolution_payload(self) -> Dict[str, Any]:
        """Formatea el payload exacto esperado por Evolution API /message/sendText."""
        return {
            "instanceId": self.instance_id,
            "number": self.recipient_jid,
            "options": {
                "delay": self.delay_ms,
                "linkPreview": False
            },
            "text": self.text_content
        }

    def to_meta_payload(self) -> Dict[str, Any]:
        """Formatea el payload exacto esperado por Meta WhatsApp Business Cloud API v21.0 (CERO Celular)."""
        import re
        clean_num = re.sub(r"\D", "", self.recipient_jid.split("@")[0].strip())
        if clean_num.startswith("04") and len(clean_num) == 11:
            clean_num = "58" + clean_num[1:]
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_num,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": self.text_content
            }
        }



class N8nDispatcherAgent:
    """Subagente orquestador del puente bidireccional entre n8n y Movilnet Core."""

    def __init__(self, repository: Optional[MovilnetRepository] = None):
        self.repository = repository or MovilnetRepository()

    def process_inbound_webhook(self, webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Paso integral de recepción, clasificación, resolución en DB ODA
        y empaquetado para despacho hacia n8n Output.
        """
        # 1. Extrae y normaliza el mensaje
        normalized = N8nWebhookPayloadExtractor.extract_universal(webhook_payload)
        if not normalized or not normalized.phone:
            return {
                "status": "error",
                "code": "ERR_INVALID_PAYLOAD",
                "message": "No se pudo extraer el remitente o teléfono del payload de n8n."
            }

        # 2. Resuelve en Movilnet Core
        core_res = N8nWebhookPayloadExtractor.execute_in_movilnet_core(normalized, self.repository)
        reply_text = core_res.get("reply_text", "Estimado abonado, su consulta fue recibida.")

        # 3. Construye el mensaje de salida para n8n Egress
        raw_jid = normalized.raw_phone or f"58{normalized.phone[1:]}@s.whatsapp.net"
        instance = normalized.instance_id or "Viki LPGTEC"

        egress = N8nEgressMessage(
            instance_id=instance,
            recipient_jid=raw_jid,
            text_content=reply_text,
            delay_ms=1500,
            source_intent=normalized.intent,
            latency_mode=core_res.get("latency_mode", "FAST_PATH_DETERMINISTIC")
        )

        return {
            "status": "success",
            "phone": normalized.phone,
            "sender_name": normalized.sender_name,
            "intent": normalized.intent,
            "reply_text": reply_text,
            "subscriber": core_res.get("subscriber"),
            "plan": core_res.get("plan"),
            "balance": core_res.get("balance"),
            "latency_mode": egress.latency_mode,
            "tokens_cost_usd": 0.0,
            "n8n_egress_payload": egress.to_evolution_payload(),
            "meta_cloud_payload": egress.to_meta_payload()
        }



def run_self_test() -> bool:
    """Auto-verificación formal del subagente despachador."""
    agent = N8nDispatcherAgent()
    sample = {
        "event": "messages.upsert",
        "instance": "Viki LPGTEC",
        "data": {
            "key": {
                "remoteJid": "584160000001@s.whatsapp.net",
                "id": "DISPATCH-TEST-001"
            },
            "pushName": "Abonado Movilnet",
            "message": {
                "conversation": "Saludo informa contrato"
            }
        }
    }
    result = agent.process_inbound_webhook(sample)
    assert result["status"] == "success"
    assert result["phone"] == "04160000001"
    assert result["intent"] == "CONTRACT_INFO"
    assert "Inteliplan 10GB 4GMAX" in result["reply_text"]
    assert result["n8n_egress_payload"]["number"] == "584160000001@s.whatsapp.net"
    assert result["n8n_egress_payload"]["instanceId"] == "Viki LPGTEC"
    print("✅ [DISPATCHER AGENT TEST PASS]: Subagente despachador n8n 100% verificado.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Subagente Despachador n8n ↔ Movilnet Core")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-test")
    parser.add_argument("--sample", action="store_true", help="Procesar payload de prueba")
    args = parser.parse_args()

    if args.test:
        run_self_test()
    elif args.sample:
        agent = N8nDispatcherAgent()
        sample = {
            "event": "messages.upsert",
            "instance": "Viki LPGTEC",
            "data": {
                "key": {"remoteJid": "584160000001@s.whatsapp.net", "id": "SAMPLE-01"},
                "pushName": "Abonado Movilnet",
                "message": {"conversation": "Saludo informa contrato"}
            }
        }
        print(json.dumps(agent.process_inbound_webhook(sample), indent=2, ensure_ascii=False))
