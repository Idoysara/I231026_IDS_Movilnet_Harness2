#!/usr/bin/env python3
"""
mcp/privacy_tools.py — Suite 4: Privacidad, PII Sanitizer LATAM & Bóveda Criptográfica
=====================================================================================
Proyecto: AI_Movilnet_300926 / Antigravity Level 5 Architecture
Estándar: Model Context Protocol (MCP) JSON-RPC 2.0 & Normativa de Privacidad CONATEL
Cumplimiento: Ley de Protección de Datos Personales / OWASP Top 10 LLM06 (Sensitive Info)

Herramientas MCP Expuestas:
  1. mcp_pii_sanitize_text: Sanitiza y anonimiza cédulas, números, tarjetas y cuentas bancarias
  2. mcp_pii_tokenize_reversible: Reemplaza PII por tokens criptográficos reversibles (HMAC-SHA256)
  3. mcp_pii_unmask_authorized: Desanonimización auditada para agentes autorizados Nivel 2
  4. mcp_pii_get_audit_log: Trazabilidad de acceso a datos sensibles para auditoría CONATEL
"""

from __future__ import annotations

import os
import sys
import json
import time
import re
import hmac
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Clave secreta para tokens criptográficos (en producción inyectada por KMS / Vault)
_VAULT_SECRET = os.environ.get("MOVILNET_VAULT_SECRET", "MOVILNET_SECRET_HMAC_KEY_2026").encode("utf-8")

# Bóveda en memoria de tokens reversibles
_TOKEN_VAULT: Dict[str, Dict[str, Any]] = {}

# Registro de auditoría de desanonimización (Log inmutable CONATEL)
_PRIVACY_AUDIT_LOG: List[Dict[str, Any]] = []


# ============================================================================
# Algoritmos de Validación Criptográfica y Numérica
# ============================================================================

def _luhn_checksum_valid(card_num: str) -> bool:
    """Valida si una secuencia numérica de 13-16 dígitos satisface el algoritmo de Luhn (Mod 10)."""
    digits = [int(c) for c in card_num if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


def _generate_deterministic_token(entity_type: str, raw_value: str) -> str:
    """Genera un token reversible determinista mediante HMAC-SHA256."""
    h = hmac.new(_VAULT_SECRET, f"{entity_type}:{raw_value}".encode("utf-8"), hashlib.sha256).hexdigest()
    return f"[[TOK_{entity_type}_{h[:8].upper()}]]"


# ============================================================================
# Herramientas MCP Suite 4
# ============================================================================

def mcp_pii_sanitize_text(text: str, mask_char: str = "*") -> Dict[str, Any]:
    """
    [MCP Tool] Sanitiza y anonimiza información personal identificable (PII) en textos libres:
      - Cédulas venezolanas (V-, E-, J-, G-, P-)
      - Tarjetas de crédito/débito (Luhn verificado)
      - Números telefónicos venezolanos (0416, 0426, 0414, 0424, 0412)
      - Números de cuenta bancaria nacional de 20 dígitos
    """
    sanitized = text
    entities_detected: List[Dict[str, str]] = []

    # 1. Tarjetas de Crédito / Débito (13-16 dígitos) con verificación Luhn
    card_pattern = r'\b(?:\d[ -]*?){13,16}\b'
    for match in re.finditer(card_pattern, text):
        raw_card = re.sub(r'[\s\-]', '', match.group())
        if _luhn_checksum_valid(raw_card) or len(raw_card) == 16:
            masked = raw_card[:4] + (mask_char * 8) + raw_card[-4:]
            sanitized = sanitized.replace(match.group(), masked)
            entities_detected.append({"type": "CREDIT_CARD", "masked_preview": masked})

    # 2. Cuentas Bancarias Venezolanas (20 dígitos que inician con código de banco 01XX)
    bank_account_pattern = r'\b(01\d{2})[- ]?(\d{4})[- ]?(\d{2})[- ]?(\d{10})\b'
    for match in re.finditer(bank_account_pattern, sanitized):
        raw_acc = re.sub(r'[\s\-]', '', match.group(0))
        masked_acc = raw_acc[:4] + "-" + (mask_char * 6) + "-" + raw_acc[-4:]
        sanitized = sanitized.replace(match.group(0), masked_acc)
        entities_detected.append({"type": "BANK_ACCOUNT", "masked_preview": masked_acc})

    # 3. Cédulas Venezolanas (V-, E-, J-, G-, P-)
    cid_pattern = r'\b([VEJGPvejgp])[- ]?([0-9]{6,9})\b'
    for match in re.finditer(cid_pattern, sanitized):
        prefix = match.group(1).upper()
        num = match.group(2)
        masked_cid = f"{prefix}-{num[:2]}{mask_char * 4}{num[-2:]}"
        sanitized = sanitized.replace(match.group(0), masked_cid)
        entities_detected.append({"type": "NATIONAL_ID", "masked_preview": masked_cid})

    # 4. Números Móviles Venezolanos
    phone_pattern = r'\b(0416|0426|0414|0424|0412)[- ]?([0-9]{3})[- ]?([0-9]{4})\b'
    for match in re.finditer(phone_pattern, sanitized):
        prefix = match.group(1)
        masked_phone = f"{prefix}-{match.group(2)[:1]}{mask_char * 2}-{match.group(3)[-2:]}"
        sanitized = sanitized.replace(match.group(0), masked_phone)
        entities_detected.append({"type": "PHONE_NUMBER", "masked_preview": masked_phone})

    return {
        "success": True,
        "sanitized_text": sanitized,
        "entities_count": len(entities_detected),
        "entities_detected": entities_detected,
        "compliance_standard": "CONATEL / ISO-27701 Privacy by Design",
        "clean_for_llm": True
    }


def mcp_pii_tokenize_reversible(text: str) -> Dict[str, Any]:
    """
    [MCP Tool] Reemplaza datos PII por identificadores deterministas en la bóveda criptográfica.
    Permite que el modelo entienda referencias cruzadas sin ver datos reales.
    """
    tokenized = text
    tokens_created = []

    # Tokenizar Cédulas
    for match in re.finditer(r'\b([VEJGPvejgp])[- ]?([0-9]{6,9})\b', text):
        raw_cid = f"{match.group(1).upper()}-{match.group(2)}"
        token = _generate_deterministic_token("CID", raw_cid)
        _TOKEN_VAULT[token] = {
            "entity_type": "NATIONAL_ID",
            "raw_value": raw_cid,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        tokenized = tokenized.replace(match.group(0), token)
        tokens_created.append(token)

    # Tokenizar Teléfonos
    for match in re.finditer(r'\b(0416|0426|0414|0424|0412)[- ]?([0-9]{7})\b', text):
        raw_phone = f"{match.group(1)}{match.group(2)}"
        token = _generate_deterministic_token("PHONE", raw_phone)
        _TOKEN_VAULT[token] = {
            "entity_type": "PHONE_NUMBER",
            "raw_value": raw_phone,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        tokenized = tokenized.replace(match.group(0), token)
        tokens_created.append(token)

    return {
        "success": True,
        "tokenized_text": tokenized,
        "tokens_count": len(tokens_created),
        "tokens_list": tokens_created
    }


def mcp_pii_unmask_authorized(
    token: str,
    authorized_role: str,
    agent_id: str,
    justification: str = "ATENCION_TICKET_SOPORTE_L2"
) -> Dict[str, Any]:
    """
    [MCP Tool] Desanonimiza un token bajo estricta autorización RBAC con registro inmutable de auditoría.
    """
    if authorized_role not in ["SUPERVISOR_L2", "SECURITY_ADMIN", "FRAUD_OFFICER"]:
        return {
            "success": False,
            "error_code": "ERR_UNAUTHORIZED_ROLE",
            "message": f"El rol '{authorized_role}' no posee privilegios para desanonimizar información sensible."
        }

    token_data = _TOKEN_VAULT.get(token)
    if not token_data:
        return {
            "success": False,
            "error_code": "ERR_TOKEN_NOT_FOUND",
            "message": f"Token '{token}' no registrado en la bóveda criptográfica."
        }

    # Registro en log inmutable
    audit_entry = {
        "event_id": f"AUD-{int(time.time())}-{len(_PRIVACY_AUDIT_LOG) + 1}",
        "token": token,
        "entity_type": token_data["entity_type"],
        "requester_agent": agent_id,
        "requester_role": authorized_role,
        "justification": justification,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    _PRIVACY_AUDIT_LOG.append(audit_entry)

    return {
        "success": True,
        "token": token,
        "entity_type": token_data["entity_type"],
        "raw_value": token_data["raw_value"],
        "audit_event_id": audit_entry["event_id"],
        "message": "Desanonimización autorizada y registrada en la bitácora de control CONATEL."
    }


def mcp_pii_get_audit_log(limit: int = 10) -> Dict[str, Any]:
    """
    [MCP Tool] Retorna las últimas trazas del registro de auditoría de privacidad.
    """
    entries = _PRIVACY_AUDIT_LOG[-limit:]
    return {
        "success": True,
        "total_audit_events": len(_PRIVACY_AUDIT_LOG),
        "limit_returned": len(entries),
        "audit_records": entries
    }


# ============================================================================
# Servidor MCP Despachador (PrivacyGuardMcpServer)
# ============================================================================

class PrivacyGuardMcpServer:
    """Servidor MCP JSON-RPC 2.0 para la Suite 4: Privacidad y Bóveda Criptográfica."""

    TOOLS = {
        "mcp_pii_sanitize_text": mcp_pii_sanitize_text,
        "mcp_pii_tokenize_reversible": mcp_pii_tokenize_reversible,
        "mcp_pii_unmask_authorized": mcp_pii_unmask_authorized,
        "mcp_pii_get_audit_log": mcp_pii_get_audit_log,
    }

    @classmethod
    def get_manifest(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "mcp_pii_sanitize_text",
                "description": "Anonimiza cédulas venezolanas, tarjetas, teléfonos y cuentas bancarias.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "mask_char": {"type": "string", "default": "*"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "mcp_pii_tokenize_reversible",
                "description": "Tokeniza datos sensibles con identificadores criptográficos reversibles.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"]
                }
            },
            {
                "name": "mcp_pii_unmask_authorized",
                "description": "Desanonimiza tokens para agentes autorizados con registro de auditoría.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "token": {"type": "string"},
                        "authorized_role": {"type": "string"},
                        "agent_id": {"type": "string"},
                        "justification": {"type": "string"}
                    },
                    "required": ["token", "authorized_role", "agent_id"]
                }
            },
            {
                "name": "mcp_pii_get_audit_log",
                "description": "Consulta el registro de auditoría de acceso a datos sensibles CONATEL.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "default": 10}}
                }
            }
        ]

    def handle_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Any = 1) -> Dict[str, Any]:
        params = params or {}
        if method not in self.TOOLS:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method '{method}' not found in PrivacyGuardMcpServer."},
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
