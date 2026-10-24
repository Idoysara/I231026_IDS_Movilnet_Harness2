#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validators.py — Validador Defensivo de Entradas Telco y FinTech
=============================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
Reglas de validación y sanitización para números telefónicos venezolanos (0416/0426),
identificaciones de identidad (Cédula/RIF V/E/J/G) y montos de Pago Móvil C2P.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any, Optional


class InputValidator:
    """Validador defensivo de entradas según regulaciones CONATEL y SUDEBAN."""

    RE_MSISDN = re.compile(r"^(?:(?:\+?58)|0)?(416|426)(\d{7})$")
    RE_CID = re.compile(r"^([VEJG])?-?(\d{6,9})$", re.IGNORECASE)
    RE_BANK_CODE = re.compile(r"^\d{4}$")
    RE_OTP = re.compile(r"^\d{6,8}$")

    @classmethod
    def normalize_msisdn(cls, phone: Optional[str]) -> Optional[str]:
        """Normaliza teléfono venezolano a formato estándar '0416xxxxxxx' o '0426xxxxxxx'."""
        if not phone:
            return None
        clean = re.sub(r"[\s\-\(\)]", "", str(phone).strip())
        m = cls.RE_MSISDN.match(clean)
        if m:
            prefix, rest = m.group(1), m.group(2)
            return f"0{prefix}{rest}"
        return None

    @classmethod
    def normalize_cid(cls, cid: Optional[str]) -> Optional[str]:
        """Normaliza cédula venezolana al estándar 'V-xxxxxxxx'."""
        if not cid:
            return None
        clean = re.sub(r"[\s\.]", "", str(cid).strip().upper())
        m = cls.RE_CID.match(clean)
        if m:
            letter = m.group(1) or "V"
            num = m.group(2)
            return f"{letter}-{num}"
        return None

    @classmethod
    def validate_amount(cls, amount: Any) -> Optional[float]:
        """Valida que el monto sea un número estrictamente positivo (> 0)."""
        try:
            val = float(amount)
            if val > 0.0:
                return round(val, 2)
        except (ValueError, TypeError):
            pass
        return None


# ============================================================================
# CLI DE AUTO-VERIFICACIÓN
# ============================================================================

def run_self_tests() -> int:
    """Ejecuta suite de pruebas unitarias para InputValidator."""
    print("🧪 Verificando validators.py...")

    # MSISDN válido
    assert InputValidator.normalize_msisdn("04161234567") == "04161234567"
    assert InputValidator.normalize_msisdn("+584261234567") == "04261234567"
    assert InputValidator.normalize_msisdn("584161234567") == "04161234567"
    assert InputValidator.normalize_msisdn("0416-123-4567") == "04161234567"

    # MSISDN inválido
    assert InputValidator.normalize_msisdn("04141234567") is None  # Movistar
    assert InputValidator.normalize_msisdn("04121234567") is None  # Digitel
    assert InputValidator.normalize_msisdn("abc") is None
    assert InputValidator.normalize_msisdn(None) is None

    # CID válido
    assert InputValidator.normalize_cid("V-12345678") == "V-12345678"
    assert InputValidator.normalize_cid("12345678") == "V-12345678"
    assert InputValidator.normalize_cid("E-87654321") == "E-87654321"

    # Monto válido
    assert InputValidator.validate_amount("150.50") == 150.50
    assert InputValidator.validate_amount(100) == 100.00
    assert InputValidator.validate_amount("-10") is None
    assert InputValidator.validate_amount("abc") is None

    print("✅ [TEST PASS] validators: 4/4 suites aprobadas (100%).")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validador de Entradas Telco/Fintech")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación")
    args = parser.parse_args()

    if args.test:
        sys.exit(run_self_tests())
    else:
        print("Uso: python3 -m api.validators --test")


if __name__ == "__main__":
    main()
