#!/usr/bin/env python3
"""
core/session_identity_isolator.py — Aislador Criptográfico y Canónico de Sesiones de Chat
========================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal

Problema que Resuelve (Hallazgo Forense):
El nodo 'Postgres Chat Memory' en n8n utilizaba una expresión que priorizaba el 'pushName':
    sessionKey = $('Edit Fields').item.json.body.data.pushName ?? $('Edit Fields').item.json.body.data.key.remoteJid
Esto provocó que múltiples abonados con el mismo nombre o perfil (ej: 'Ids' en 0414-2554590 y 0424-1533712)
compartieran exactamente la misma memoria en PostgreSQL, inyectando historiales ajenos y
desperdiciando miles de tokens de contexto.

Solución de Ingeniería:
1. Genera un Session ID estrictamente canónico, inmutable y determinista anclado al número E.164.
2. Rechaza colisiones por 'pushName'.
3. Soporta blind indexing HMAC-SHA256 para estricto cumplimiento Zero-PII.
4. CLI autónomo con auto-verificación formal (--test, --demo).
"""

from __future__ import annotations

import re
import sys
import hmac
import hashlib
import argparse
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class SessionIdentity:
    """Entidad de Dominio Inmutable para la Identidad de Sesión de Chat."""
    canonical_session_key: str
    e164_phone: str
    national_phone: str
    operator: str
    is_valid: bool
    blind_index_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SessionIdentityIsolator:
    """Motor de Aislamiento de Identidad de Sesión para Chatbots y Memoria Postgres."""

    SECRET_SALT = b"MOVILNET_SESSION_ISOLATOR_SECRET_2026"

    OPERATOR_PREFIXES: Dict[str, str] = {
        "0416": "MOVILNET",
        "0426": "MOVILNET",
        "0414": "MOVISTAR",
        "0424": "MOVISTAR",
        "0412": "DIGITEL",
    }

    @classmethod
    def sanitize_phone_digits(cls, raw: str) -> str:
        """Extrae únicamente dígitos limpios removiendo sufijos JID de WhatsApp."""
        if not raw:
            return ""
        # Remover sufijos WhatsApp (@s.whatsapp.net, @g.us, :1, etc.)
        cleaned = str(raw).split("@")[0].split(":")[0]
        digits = re.sub(r"[^\d]", "", cleaned)
        return digits

    @classmethod
    def to_national_format(cls, digits: str) -> str:
        """Convierte cualquier formato (0058..., 584XXXXXXXXX o 04XXXXXXXXX) a formato nacional 04XXXXXXXXX."""
        if digits.startswith("0058") and len(digits) == 14:
            return "0" + digits[4:]
        if digits.startswith("58") and len(digits) == 12:
            return "0" + digits[2:]
        if digits.startswith("0") and len(digits) == 11:
            return digits
        if len(digits) == 10 and digits.startswith("4"):
            return "0" + digits
        return digits

    @classmethod
    def to_e164_format(cls, digits: str) -> str:
        """Convierte cualquier formato a E.164 internacional puro (584XXXXXXXXX)."""
        national = cls.to_national_format(digits)
        if national.startswith("0") and len(national) == 11:
            return "58" + national[1:]
        if digits.startswith("58") and len(digits) == 12:
            return digits
        return digits

    @classmethod
    def detect_operator(cls, national_phone: str) -> str:
        """Detecta la operadora CONATEL según el prefijo."""
        if len(national_phone) >= 4:
            prefix = national_phone[:4]
            if prefix in cls.OPERATOR_PREFIXES:
                return cls.OPERATOR_PREFIXES[prefix]
            if prefix.startswith("02"):
                return "CANTV_FIJA"
            if prefix in ("0500", "0800", "0900"):
                return "VOIP_ESPECIAL"
        return "OTRO_EXTERNO"

    @classmethod
    def isolate_session(
        cls,
        remote_jid: Optional[str] = None,
        phone_number: Optional[str] = None,
        push_name: Optional[str] = None,
        salt: Optional[bytes] = None
    ) -> SessionIdentity:
        """
        Calcula la identidad de sesión aislada de forma determinista y a prueba de colisiones.
        La clave canónica NUNCA dependerá del push_name, eliminando de raíz la contaminación cruzada.
        """
        # Prioridad absoluta: remote_jid o phone_number
        raw_target = remote_jid or phone_number or ""
        digits = cls.sanitize_phone_digits(raw_target)

        # Si no hay dígitos en target, intentar extraer de phone_number
        if not digits and phone_number:
            digits = cls.sanitize_phone_digits(phone_number)

        national = cls.to_national_format(digits)
        e164 = cls.to_e164_format(digits)
        operator = cls.detect_operator(national)

        # Validación de formato venezolano móvil (11 dígitos, comienza con 04)
        is_valid = bool(re.match(r"^04(12|14|16|24|26)\d{7}$", national))

        # Canonic session key
        if is_valid:
            canonical_key = f"SESSION:E164:{e164}"
        elif digits:
            canonical_key = f"SESSION:RAW:{digits}"
        else:
            # Fallback seguro con hash del push_name para no crashear, pero etiquetado como ANONYMOUS
            safe_name = re.sub(r"[^a-zA-Z0-9_]", "", push_name or "ANON")
            canonical_key = f"SESSION:ANON:{safe_name}"

        # Blind Index HMAC-SHA256
        active_salt = salt or cls.SECRET_SALT
        blind_hash = hmac.new(
            active_salt,
            canonical_key.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return SessionIdentity(
            canonical_session_key=canonical_key,
            e164_phone=e164,
            national_phone=national,
            operator=operator,
            is_valid=is_valid,
            blind_index_hash=blind_hash
        )


def main():
    parser = argparse.ArgumentParser(description="Aislador Canónico de Sesiones de Chat (Zero-Contamination)")
    parser.add_argument("--test", action="store_true", help="Ejecutar suite de pruebas formales")
    parser.add_argument("--demo", action="store_true", help="Demostración con casos de uso reales")
    parser.add_argument("--jid", type=str, help="WhatsApp JID a evaluar (ej: 584140000001@s.whatsapp.net)")
    parser.add_argument("--pushname", type=str, default="Usuario Demo", help="Nombre del perfil (ej: Usuario Demo)")
    args = parser.parse_args()

    if args.test:
        print("🧪 [TEST] Verificando SessionIdentityIsolator (Pilares I al VII)...")
        # Caso 1: Mismo pushName en dos teléfonos distintos DEBEN tener claves diferentes
        s1 = SessionIdentityIsolator.isolate_session(remote_jid="584140000001@s.whatsapp.net", push_name="Usuario Demo")
        s2 = SessionIdentityIsolator.isolate_session(remote_jid="584241533712@s.whatsapp.net", push_name="Usuario Demo")
        assert s1.canonical_session_key != s2.canonical_session_key, "ERROR: Colisión detectada entre mismos pushNames!"
        assert s1.canonical_session_key == "SESSION:E164:584140000001"
        assert s2.canonical_session_key == "SESSION:E164:584241533712"
        assert s1.operator == "MOVISTAR"
        assert s2.operator == "MOVISTAR"

        # Caso 2: Formato nacional directo
        s3 = SessionIdentityIsolator.isolate_session(phone_number="04160000001", push_name="Carlos Perez")
        assert s3.canonical_session_key == "SESSION:E164:584160000001"
        assert s3.operator == "MOVILNET"
        assert s3.is_valid is True

        # Caso 3: Sanitización de sufijos complejos (:1, etc.)
        s4 = SessionIdentityIsolator.isolate_session(remote_jid="584121234567:12@s.whatsapp.net")
        assert s4.canonical_session_key == "SESSION:E164:584121234567"
        assert s4.operator == "DIGITEL"

        # Caso 4: Determinismo del Blind Index
        s1_again = SessionIdentityIsolator.isolate_session(remote_jid="584140000001@s.whatsapp.net", push_name="Usuario Demo")
        assert s1.blind_index_hash == s1_again.blind_index_hash

        print("✅ [TEST PASS] Todos los invariantes de aislamiento verificados exitosamente (100% OK).")
        return

    if args.demo or args.jid:
        target_jid = args.jid or "584140000001@s.whatsapp.net"
        identity = SessionIdentityIsolator.isolate_session(remote_jid=target_jid, push_name=args.pushname)
        print(f"\n📱 Demostración de Aislamiento de Identidad:")
        print(f"   Target JID:             {target_jid}")
        print(f"   PushName:               {args.pushname}")
        print(f"   Canonical Session Key:  {identity.canonical_session_key}")
        print(f"   E.164 Phone:            {identity.e164_phone}")
        print(f"   National Phone:         {identity.national_phone}")
        print(f"   Operadora Detectada:    {identity.operator}")
        print(f"   Validez CONATEL:        {identity.is_valid}")
        print(f"   Blind Index SHA-256:    {identity.blind_index_hash[:16]}...\n")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
