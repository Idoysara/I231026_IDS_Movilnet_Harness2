#!/usr/bin/env python3
"""
mcp/fintech_tools.py — Suite 2: Pasarela Financiera C2P, Tasas BCV & Antifraude
================================================================================
Proyecto: AI_Movilnet_300926 / Antigravity Level 5 Architecture
Estándar: Model Context Protocol (MCP) JSON-RPC 2.0 & Normativas SUDEBAN / BCV
Cumplimiento: Resolución BCV N° 19-05-01 / Circular SUDEBAN SIB-II-GG-02888

Herramientas MCP Expuestas:
  1. mcp_bcv_get_official_rate: Tasa oficial de cambio del Banco Central de Venezuela
  2. mcp_bcv_convert_to_bolivares: Conversión formal de USD a Bolívares (VES)
  3. mcp_bcv_convert_to_usd: Conversión formal de Bolívares (VES) a USD
  4. mcp_c2p_validate_transaction: Validador antifraude de transacciones Pago Móvil C2P
  5. mcp_c2p_generate_otp_challenge: Generador de desafío dinámico OTP de 6 dígitos
  6. mcp_c2p_confirm_payment: Verificador de OTP y liquidación transaccional
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Modelos de Datos Tipados (Data Models)
# ============================================================================

@dataclass
class BcvRateSnapshot:
    rates: Dict[str, float]
    synced_at: str
    source: str
    ttl_seconds: int = 3600


@dataclass
class C2PTransactionRecord:
    reference_id: str
    bank_code: str
    bank_name: str
    amount_bs: float
    phone: str
    payer_cid: str
    timestamp: str
    status: str
    risk_score: float


# ============================================================================
# Catálogo de Bancos SUDEBAN y Almacenes Transaccionales
# ============================================================================

_SUDEBAN_BANKS: Dict[str, str] = {
    "0102": "Banco de Venezuela, S.A. Banco Universal",
    "0104": "Venezolano de Crédito, S.A. Banco Universal",
    "0105": "Banco Mercantil, C.A. Banco Universal",
    "0108": "Banco Provincial, S.A. Banco Universal",
    "0114": "Bancaribe, C.A. Banco Universal",
    "0115": "Banco Exterior, C.A. Banco Universal",
    "0134": "Banesco Banco Universal, C.A.",
    "0151": "BFC Banco Fondo Común, C.A.",
    "0163": "Banco del Tesoro, C.A. Banco Universal",
    "0172": "Bancamiga Banco Universal, C.A.",
    "0175": "Banco Bicentenario del Pueblo, Banco Universal, C.A."
}

# Caché Oficial BCV con tasas de referencia
_BCV_CACHE = BcvRateSnapshot(
    rates={"USD": 36.85, "EUR": 40.12, "CNY": 5.15, "RUB": 0.40},
    synced_at="2026-09-30T14:00:00Z",
    source="Banco Central de Venezuela (BCV Oficial)",
    ttl_seconds=3600
)

# Almacén de referencias C2P ya asentadas (prevención de ataques de replay e idempotencia)
_SETTLED_C2P_TRANSACTIONS: Dict[str, C2PTransactionRecord] = {}

# Almacén de desafíos OTP activos con expiración
_ACTIVE_OTP_STORE: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Herramientas MCP Suite 2
# ============================================================================

def mcp_bcv_get_official_rate(currency: str = "USD") -> Dict[str, Any]:
    """
    [MCP Tool] Obtiene la tasa de cambio oficial del BCV para la divisa solicitada.
    Garantiza cálculo formal de precios para planes y recargas en Bolívares.
    """
    curr = currency.upper().strip()
    rate = _BCV_CACHE.rates.get(curr, _BCV_CACHE.rates["USD"])

    return {
        "success": True,
        "currency": curr,
        "exchange_rate_ves": rate,
        "source": _BCV_CACHE.source,
        "synced_at": _BCV_CACHE.synced_at,
        "legal_basis": "Resolución N° 19-05-01 del Banco Central de Venezuela.",
        "currency_symbol": "Bs."
    }


def mcp_bcv_convert_to_bolivares(usd_amount: float) -> Dict[str, Any]:
    """
    [MCP Tool] Convierte un monto denominado en USD a Bolívares (VES) a tasa oficial BCV.
    """
    if usd_amount < 0:
        return {"success": False, "error_code": "ERR_INVALID_AMOUNT", "message": "El monto no puede ser negativo."}

    rate = _BCV_CACHE.rates["USD"]
    ves_total = round(usd_amount * rate, 2)
    return {
        "success": True,
        "usd_amount": usd_amount,
        "bcv_rate": rate,
        "ves_amount": ves_total,
        "formatted_text": f"{ves_total:,.2f} Bs. (Tasa oficial BCV: {rate:.2f} Bs/USD)"
    }


def mcp_bcv_convert_to_usd(ves_amount: float) -> Dict[str, Any]:
    """
    [MCP Tool] Convierte un monto denominado en Bolívares a su equivalente en USD a tasa oficial BCV.
    """
    if ves_amount < 0:
        return {"success": False, "error_code": "ERR_INVALID_AMOUNT", "message": "El monto no puede ser negativo."}

    rate = _BCV_CACHE.rates["USD"]
    usd_equiv = round(ves_amount / rate, 2)
    return {
        "success": True,
        "ves_amount": ves_amount,
        "bcv_rate": rate,
        "usd_equivalent": usd_equiv,
        "formatted_text": f"${usd_equiv:.2f} USD"
    }


def mcp_c2p_validate_transaction(
    reference_id: str,
    bank_code: str,
    amount_bs: float,
    phone: str,
    payer_cid: str
) -> Dict[str, Any]:
    """
    [MCP Tool] Validador transaccional y motor antifraude para pagos móviles C2P.
    Inspecciona normativas SUDEBAN, duplicidad de referencia y evaluación ponderada de riesgo.
    """
    clean_ref = reference_id.strip()
    clean_phone = re.sub(r'[\s\-\+]', '', phone)
    if clean_phone.startswith("58"):
        clean_phone = "0" + clean_phone[2:]

    # 1. Validación de código de banco nacional
    bank_name = _SUUDEBAN_NAME = _SUDEBAN_BANKS.get(bank_code)
    if not bank_name:
        return {
            "success": False,
            "status": "REJECTED_UNKNOWN_BANK",
            "error_code": "ERR_INVALID_SUDEBAN_BANK",
            "risk_score": 95.0,
            "message": f"El código de banco '{bank_code}' no existe en la red del Sistema Bancario Nacional (SUDEBAN)."
        }

    # 2. Control de Idempotencia / Detección de Ataques de Repetición (Replay Attack)
    try:
        from db.repository import MovilnetRepository
        _repo = MovilnetRepository()
        if _repo.is_reference_duplicate(clean_ref):
            return {
                "success": False,
                "status": "REJECTED_DUPLICATE_REFERENCE",
                "error_code": "ERR_DUPLICATE_REFERENCE",
                "risk_score": 100.0,
                "message": f"La referencia '{clean_ref}' ya fue procesada en la base de datos. Operación rechazada por duplicidad."
            }
    except Exception:
        _repo = None

    if clean_ref in _SETTLED_C2P_TRANSACTIONS:
        prev = _SETTLED_C2P_TRANSACTIONS[clean_ref]
        return {
            "success": False,
            "status": "REJECTED_DUPLICATE_REFERENCE",
            "error_code": "ERR_DUPLICATE_REFERENCE",
            "risk_score": 100.0,
            "message": f"La referencia '{clean_ref}' ya fue procesada el {prev.timestamp}. Operación rechazada por duplicidad."
        }

    # 3. Motor de Ponderación de Riesgo Antifraude
    risk_score = 5.0

    # Monto superior a 15,000 Bs requiere doble factor obligatorio
    requires_otp = False
    if amount_bs > 15000.0:
        risk_score += 40.0
        requires_otp = True
    elif amount_bs > 5000.0:
        risk_score += 15.0

    # Línea origen no perteneciente a prefijos Movilnet (pago inter-operadora)
    if not (clean_phone.startswith("0416") or clean_phone.startswith("0426")):
        risk_score += 8.0

    # Evaluación del umbral de corte
    if risk_score <= 60.0 and not requires_otp:
        tx_record = C2PTransactionRecord(
            reference_id=clean_ref,
            bank_code=bank_code,
            bank_name=bank_name,
            amount_bs=amount_bs,
            phone=clean_phone,
            payer_cid=payer_cid,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="APPROVED_SETTLED",
            risk_score=risk_score
        )
        _SETTLED_C2P_TRANSACTIONS[clean_ref] = tx_record

        if _repo:
            try:
                bcv_rate = _BCV_RATES.get("USD", 36.85)
                usd_equiv = round(amount_bs / bcv_rate, 2)
                _repo.record_c2p_transaction(
                    reference_id=clean_ref,
                    msisdn=clean_phone,
                    bank_code=bank_code,
                    amount_ves=amount_bs,
                    amount_usd=usd_equiv,
                    bcv_rate=bcv_rate,
                    payer_cid=payer_cid,
                    status="COMPLETADO"
                )
            except Exception:
                pass

        return {
            "success": True,
            "status": "APPROVED",
            "reference_id": clean_ref,
            "bank_name": bank_name,
            "amount_bs": amount_bs,
            "risk_score": round(risk_score, 1),
            "requires_otp_challenge": False,
            "settlement_code": f"SETTLE-C2P-{clean_ref[-6:]}",
            "message": f"Pago Móvil C2P de {amount_bs:,.2f} Bs. aprobado y conciliado instantáneamente."
        }

    # Si supera el umbral o el monto es crítico, exigir OTP
    return {
        "success": False,
        "status": "REQUIRES_OTP_CHALLENGE",
        "reference_id": clean_ref,
        "bank_name": bank_name,
        "amount_bs": amount_bs,
        "risk_score": round(risk_score, 1),
        "requires_otp_challenge": True,
        "message": "Por políticas de seguridad bancaria, la transacción requiere confirmación mediante clave dinámica OTP."
    }


def mcp_c2p_generate_otp_challenge(phone: str, transaction_id: str) -> Dict[str, Any]:
    """
    [MCP Tool] Genera un código OTP de 6 dígitos y lo asocia a la sesión transaccional con TTL de 300s.
    """
    clean_phone = re.sub(r'[\s\-\+]', '', phone)
    token_seed = f"{clean_phone}:{transaction_id}:{time.time()}"
    raw_hash = hashlib.sha256(token_seed.encode("utf-8")).hexdigest()
    otp_code = str(int(raw_hash[:8], 16) % 900000 + 100000)

    _ACTIVE_OTP_STORE[transaction_id] = {
        "phone": clean_phone,
        "otp_hash": hashlib.sha256(otp_code.encode("utf-8")).hexdigest(),
        "expires_at": time.time() + 300,
        "attempts": 0
    }

    masked_phone = f"{clean_phone[:4]}***{clean_phone[-2:]}" if len(clean_phone) >= 10 else clean_phone
    return {
        "success": True,
        "transaction_id": transaction_id,
        "phone_masked": masked_phone,
        "ttl_seconds": 300,
        "channel": "SMS_MOVILNET_NOTIFICATION",
        "mock_debug_otp": otp_code,
        "message": f"Clave dinámica enviada al número {masked_phone}. Válida por 5 minutos."
    }


def mcp_c2p_confirm_payment(transaction_id: str, otp_code: str) -> Dict[str, Any]:
    """
    [MCP Tool] Valida el token OTP suministrado por el abonado y liquida el pago C2P.
    """
    session = _ACTIVE_OTP_STORE.get(transaction_id)
    if not session:
        return {
            "success": False,
            "status": "CHALLENGE_NOT_FOUND",
            "message": "La sesión de pago no existe o ya fue finalizada."
        }

    if time.time() > session["expires_at"]:
        del _ACTIVE_OTP_STORE[transaction_id]
        return {
            "success": False,
            "status": "CHALLENGE_EXPIRED",
            "message": "El código OTP ha expirado. Debe generar un nuevo desafío de pago."
        }

    input_hash = hashlib.sha256(otp_code.strip().encode("utf-8")).hexdigest()
    if input_hash == session["otp_hash"]:
        del _ACTIVE_OTP_STORE[transaction_id]
        auth_code = f"AUTH-C2P-{int(time.time())}"
        return {
            "success": True,
            "status": "PAYMENT_CONFIRMED",
            "transaction_id": transaction_id,
            "authorization_code": auth_code,
            "message": "Clave dinámica confirmada exitosamente. Fondos debitados y saldo acreditado a la línea."
        }

    session["attempts"] += 1
    remaining = 3 - session["attempts"]
    if session["attempts"] >= 3:
        del _ACTIVE_OTP_STORE[transaction_id]
        return {
            "success": False,
            "status": "CHALLENGE_LOCKED",
            "message": "Límite de intentos superado. Transacción cancelada por seguridad antifraude."
        }

    return {
        "success": False,
        "status": "INVALID_OTP",
        "attempts_remaining": remaining,
        "message": f"Código OTP incorrecto. Le quedan {remaining} intento(s)."
    }


# ============================================================================
# Servidor MCP Despachador (FintechMcpServer)
# ============================================================================

class FintechMcpServer:
    """Servidor MCP JSON-RPC 2.0 para la Suite 2: Pasarela Financiera C2P y BCV."""

    TOOLS = {
        "mcp_bcv_get_official_rate": mcp_bcv_get_official_rate,
        "mcp_bcv_convert_to_bolivares": mcp_bcv_convert_to_bolivares,
        "mcp_bcv_convert_to_usd": mcp_bcv_convert_to_usd,
        "mcp_c2p_validate_transaction": mcp_c2p_validate_transaction,
        "mcp_c2p_generate_otp_challenge": mcp_c2p_generate_otp_challenge,
        "mcp_c2p_confirm_payment": mcp_c2p_confirm_payment,
    }

    @classmethod
    def get_manifest(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "mcp_bcv_get_official_rate",
                "description": "Obtiene la tasa de cambio oficial del BCV.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"currency": {"type": "string", "default": "USD"}}
                }
            },
            {
                "name": "mcp_bcv_convert_to_bolivares",
                "description": "Convierte un monto en USD a Bolívares usando la tasa BCV.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"usd_amount": {"type": "number"}},
                    "required": ["usd_amount"]
                }
            },
            {
                "name": "mcp_bcv_convert_to_usd",
                "description": "Convierte un monto en Bolívares a USD usando la tasa BCV.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"ves_amount": {"type": "number"}},
                    "required": ["ves_amount"]
                }
            },
            {
                "name": "mcp_c2p_validate_transaction",
                "description": "Validador transaccional y antifraude de pagos móviles C2P.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reference_id": {"type": "string"},
                        "bank_code": {"type": "string"},
                        "amount_bs": {"type": "number"},
                        "phone": {"type": "string"},
                        "payer_cid": {"type": "string"}
                    },
                    "required": ["reference_id", "bank_code", "amount_bs", "phone", "payer_cid"]
                }
            },
            {
                "name": "mcp_c2p_generate_otp_challenge",
                "description": "Genera un desafío OTP de 6 dígitos para validar cobros C2P.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string"},
                        "transaction_id": {"type": "string"}
                    },
                    "required": ["phone", "transaction_id"]
                }
            },
            {
                "name": "mcp_c2p_confirm_payment",
                "description": "Confirma la clave OTP y finaliza el cobro C2P.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "transaction_id": {"type": "string"},
                        "otp_code": {"type": "string"}
                    },
                    "required": ["transaction_id", "otp_code"]
                }
            }
        ]

    def handle_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Any = 1) -> Dict[str, Any]:
        params = params or {}
        if method not in self.TOOLS:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method '{method}' not found in FintechMcpServer."},
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
