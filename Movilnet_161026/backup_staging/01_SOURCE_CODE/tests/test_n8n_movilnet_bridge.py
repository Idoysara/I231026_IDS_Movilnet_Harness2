#!/usr/bin/env python3
"""
test_n8n_movilnet_bridge.py — Suite de Pruebas Unitarias para el Puente Bidireccional
====================================================================================
Valida la comunicación certificada:
Input (Evolution API) <--> n8n Webhook <--> Antigravity Movilnet Core <--> Output WhatsApp
"""

import hmac
import hashlib
import time
import json
try:
    import pytest
except ImportError:
    pytest = None
from core.n8n_webhook_payload_extractor import N8nWebhookPayloadExtractor, NormalizedInboundMessage
from api.webhook_bridge import (
    DEFAULT_WEBHOOK_SECRET,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    DELIVERY_ID_HEADER,
    MAX_TIMESTAMP_TOLERANCE_SECONDS
)


def generate_hmac_signature(body_str: str, timestamp: int, secret: str = DEFAULT_WEBHOOK_SECRET) -> str:
    """Genera la firma HMAC-SHA256 estándar para el apretón de manos."""
    message = f"{timestamp}.{body_str}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_hmac_handshake(signature: str, body_str: str, timestamp: int, secret: str = DEFAULT_WEBHOOK_SECRET) -> bool:
    """Verifica la firma HMAC y valida que el timestamp esté dentro de la ventana segura."""
    now = int(time.time())
    if abs(now - timestamp) > MAX_TIMESTAMP_TOLERANCE_SECONDS:
        return False
    expected = generate_hmac_signature(body_str, timestamp, secret)
    return hmac.compare_digest(signature, expected)


def test_hmac_handshake_success():
    """Valida que un apretón de manos legítimo sea aceptado al 100%."""
    now = int(time.time())
    payload = json.dumps({"event": "messages.upsert", "phone": "04142650088"})
    sig = generate_hmac_signature(payload, now)
    
    assert verify_hmac_handshake(sig, payload, now) is True


def test_hmac_handshake_tampered_payload_rejected():
    """Valida que si el payload es adulterado en tránsito, se rechace."""
    now = int(time.time())
    payload = json.dumps({"event": "messages.upsert", "phone": "04142650088"})
    sig = generate_hmac_signature(payload, now)
    tampered_payload = json.dumps({"event": "messages.upsert", "phone": "04140000000"})
    
    assert verify_hmac_handshake(sig, tampered_payload, now) is False


def test_hmac_handshake_expired_timestamp_rejected():
    """Valida que un evento con más de 5 minutos sea rechazado por Anti-Replay."""
    old_time = int(time.time()) - 400
    payload = json.dumps({"event": "messages.upsert", "phone": "04142650088"})
    sig = generate_hmac_signature(payload, old_time)
    
    assert verify_hmac_handshake(sig, payload, old_time) is False


def test_end_to_end_bridge_roundtrip():
    """Valida el ciclo completo Input -> Normalización -> DB ODA -> Output Formatter."""
    # 1. Input desde Evolution API
    evolution_payload = {
        "event": "messages.upsert",
        "instance": "Viki LPGTEC",
        "data": {
            "key": {
                "remoteJid": "584142650088@s.whatsapp.net",
                "id": "MSG-TRANS-778899"
            },
            "pushName": "Francisco Landaeta",
            "message": {
                "conversation": "Saludo informa contrato"
            },
            "source": "ios"
        }
    }
    
    # 2. Extracción y Normalización en Antigravity Movilnet
    norm = N8nWebhookPayloadExtractor.extract_universal(evolution_payload)
    assert norm.phone == "04142650088"
    assert norm.intent == "CONTRACT_INFO"
    
    # 3. Resolución en Movilnet Core
    result = N8nWebhookPayloadExtractor.execute_in_movilnet_core(norm)
    assert result["status"] == "success"
    assert "Inteliplan 10GB 4GMAX" in result["reply_text"]
    assert result["tokens_cost_usd"] == 0.0
    
    # 4. Formateo de Salida para el nodo HTTP Request de n8n hacia Evolution API
    egress_payload = {
        "instanceId": norm.instance_id,
        "number": norm.raw_phone,
        "options": {
            "delay": 1200
        },
        "text": result["reply_text"]
    }
    
    assert egress_payload["instanceId"] == "Viki LPGTEC"
    assert egress_payload["number"] == "584142650088@s.whatsapp.net"
    assert "Estimado(a) Francisco Landaeta" in egress_payload["text"]
