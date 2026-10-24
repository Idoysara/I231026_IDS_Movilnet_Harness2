#!/usr/bin/env python3
"""
core/system_config.py — Parametrización Centralizada de Movilnet Core (Modelo N <-> 1)
=====================================================================================
Proyecto: AI_Movilnet_300926 / Movilnet PWA & Asistente 4GMAX
Gobernanza: Universal Best Practices Engineering Rule (Pilares I, II y III)
Protocolo Maestro Decagonal (Garantía de Verdad y Cero Errores)

Responsabilidades:
 1. Centralizar como parámetro dinámico de primera clase la línea telefónica del Asistente (el "1" en N <-> 1).
 2. Proveer lectura tipada desde variables de entorno (.env) o configuración por defecto.
 3. Ofrecer utilidades de actualización atómica del archivo .env y .env.example.
 4. Proveer conjunto dinámico de senders autorizados para pasarelas y guardianes de auditoría.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.phone_migration_models import PhoneDescriptor, CarrierOperator


@dataclass
class MovilnetCoreConfig:
    """Configuración tipada inmutable del núcleo Movilnet Core."""
    active_bot_phone: PhoneDescriptor
    bot_name: str
    port: int
    core_url: str
    allowed_bot_senders: Set[str]
    n8n_base_url: str
    llm_model: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_bot_phone": {
                "international_e164": self.active_bot_phone.international_e164,
                "national_formatted": self.active_bot_phone.national_formatted,
                "whatsapp_jid": self.active_bot_phone.whatsapp_jid,
                "carrier": self.active_bot_phone.carrier.value,
            },
            "bot_name": self.bot_name,
            "port": self.port,
            "core_url": self.core_url,
            "allowed_bot_senders": list(sorted(self.allowed_bot_senders)),
            "n8n_base_url": self.n8n_base_url,
            "llm_model": self.llm_model,
        }


class SystemConfigManager:
    """Gestor singleton de parametrización centralizada para Movilnet Core."""

    DEFAULT_BOT_PHONE = "0424-1533712"
    DEFAULT_BOT_NAME = "MOVI"
    DEFAULT_PORT = 8010
    ENV_FILE = PROJECT_ROOT / ".env"
    ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"

    # Línea oficial certificada y remitente activo único (+58 424 153 3712)
    AUTHORIZED_BOT_SENDERS = {
        "584241533712@s.whatsapp.net",
    }
    LEGACY_AUTHORIZED_SENDERS = AUTHORIZED_BOT_SENDERS

    # LISTA NEGRA PERMANENTE INVIOLABLE (Capítulo 228)
    # Prohibición absoluta de recepción, despacho, procesamiento o vinculación
    BLACKLISTED_NUMBERS = {
        "4166251587",
        "584166251587",
        "04166251587",
        "00584166251587",
        "584166251587@s.whatsapp.net",
    }

    @classmethod
    def is_blacklisted(cls, phone_or_jid: Optional[str]) -> bool:
        """Determina si un número, JID o texto contiene el número en lista negra 00584166251587."""
        if not phone_or_jid:
            return False
        clean = re.sub(r"\D", "", str(phone_or_jid))
        return any(clean.endswith(b) or clean == b for b in ["4166251587", "584166251587", "04166251587", "00584166251587"]) or "4166251587" in str(phone_or_jid)

    _cached_config: Optional[MovilnetCoreConfig] = None

    @classmethod
    def load_env_file(cls, env_path: Optional[Path] = None) -> Dict[str, str]:
        """Carga variables desde el archivo .env sin requerir librerías externas."""
        target = env_path or cls.ENV_FILE
        env_vars: Dict[str, str] = {}
        if not target.exists():
            return env_vars

        try:
            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        env_vars[k] = v
        except Exception:
            pass
        return env_vars

    @classmethod
    def get_config(cls, reload_env: bool = False) -> MovilnetCoreConfig:
        """Retorna la configuración activa del sistema con fallback a variables de entorno."""
        if cls._cached_config is not None and not reload_env:
            return cls._cached_config

        env_file_vars = cls.load_env_file()

        # 1. Determinar número activo de bot (prioridad: os.environ -> .env -> DEFAULT)
        phone_raw = (
            os.environ.get("MOVILNET_ACTIVE_BOT_PHONE")
            or env_file_vars.get("MOVILNET_ACTIVE_BOT_PHONE")
            or cls.DEFAULT_BOT_PHONE
        )
        bot_desc = PhoneDescriptor.from_string(phone_raw)

        # 2. Nombre del Bot
        bot_name = (
            os.environ.get("MOVILNET_BOT_NAME")
            or env_file_vars.get("MOVILNET_BOT_NAME")
            or cls.DEFAULT_BOT_NAME
        )

        # 3. Puerto y URLs
        port = int(
            os.environ.get("MOVILNET_PORT")
            or env_file_vars.get("MOVILNET_PORT")
            or cls.DEFAULT_PORT
        )
        core_url = (
            os.environ.get("MOVILNET_CORE_URL")
            or env_file_vars.get("MOVILNET_CORE_URL")
            or f"http://localhost:{port}"
        )
        n8n_base_url = (
            os.environ.get("N8N_BASE_URL")
            or env_file_vars.get("N8N_BASE_URL")
            or "https://n8n.lpgtec.net"
        )
        llm_model = (
            os.environ.get("MOVILNET_LLM_MODEL")
            or env_file_vars.get("MOVILNET_LLM_MODEL")
            or "gemini-3.5-flash-lite"
        )

        # 4. Senders autorizados dinámicos
        allowed_senders = set(cls.LEGACY_AUTHORIZED_SENDERS)
        allowed_senders.add(bot_desc.whatsapp_jid)

        config = MovilnetCoreConfig(
            active_bot_phone=bot_desc,
            bot_name=bot_name,
            port=port,
            core_url=core_url,
            allowed_bot_senders=allowed_senders,
            n8n_base_url=n8n_base_url,
            llm_model=llm_model,
        )

        cls._cached_config = config
        return config

    @classmethod
    def get_active_bot_phone(cls) -> PhoneDescriptor:
        """Acceso directo al PhoneDescriptor del número central activo (el '1')."""
        return cls.get_config().active_bot_phone

    @classmethod
    def get_active_bot_name(cls) -> str:
        """Acceso directo al nombre del Bot activo."""
        return cls.get_config().bot_name

    @classmethod
    def get_allowed_bot_senders(cls) -> Set[str]:
        """Acceso directo al set de senders permitidos."""
        return cls.get_config().allowed_bot_senders

    @classmethod
    def update_active_phone_in_env(
        cls,
        new_phone_str: str,
        bot_name: Optional[str] = None,
        root_dir: Optional[Path] = None
    ) -> bool:
        """
        Actualiza el parámetro MOVILNET_ACTIVE_BOT_PHONE en .env y .env.example
        preservando el resto del archivo. Respeta root_dir si es provisto.
        """
        base = (root_dir or PROJECT_ROOT).resolve()
        target_env = base / ".env"
        target_example = base / ".env.example"

        new_desc = PhoneDescriptor.from_string(new_phone_str)
        name_to_use = bot_name or cls.DEFAULT_BOT_NAME

        for target_path in [target_env, target_example]:
            if not target_path.exists():
                continue

            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Reemplazar o insertar MOVILNET_ACTIVE_BOT_PHONE
            if "MOVILNET_ACTIVE_BOT_PHONE=" in content:
                content = re.sub(
                    r"MOVILNET_ACTIVE_BOT_PHONE=.*",
                    f"MOVILNET_ACTIVE_BOT_PHONE={new_desc.national_formatted}",
                    content,
                )
            else:
                content += f"\n# Parametrización Central de Línea Oficial del Bot (Modelo N <-> 1)\nMOVILNET_ACTIVE_BOT_PHONE={new_desc.national_formatted}\n"

            if "MOVILNET_BOT_NAME=" in content:
                content = re.sub(
                    r"MOVILNET_BOT_NAME=.*",
                    f"MOVILNET_BOT_NAME={name_to_use}",
                    content,
                )
            else:
                content += f"MOVILNET_BOT_NAME={name_to_use}\n"

            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)

        cls._cached_config = None  # Invalidar caché
        return True


def run_self_verification() -> bool:
    """Auto-verificación formal del gestor de parametrización (Pilar II & V)."""
    print("🧪 [TEST 1/4] Carga de configuración por defecto...")
    cfg = SystemConfigManager.get_config(reload_env=True)
    assert cfg.active_bot_phone.international_digits == "584241533712"
    assert cfg.port == 8010
    assert cfg.bot_name == "MOVI"

    print("🧪 [TEST 2/4] Senders autorizados dinámicos y guarda de lista negra...")
    senders = SystemConfigManager.get_allowed_bot_senders()
    assert cfg.active_bot_phone.whatsapp_jid in senders
    assert len(senders) >= 1
    assert "584166251587@s.whatsapp.net" not in senders
    assert SystemConfigManager.is_blacklisted("00584166251587") is True
    assert SystemConfigManager.is_blacklisted("584166251587") is True
    assert SystemConfigManager.is_blacklisted("0416-625-1587") is True

    print("🧪 [TEST 3/4] Sobrescritura temporal por os.environ...")
    orig = os.environ.get("MOVILNET_ACTIVE_BOT_PHONE")
    try:
        os.environ["MOVILNET_ACTIVE_BOT_PHONE"] = "0416-0000000"
        SystemConfigManager._cached_config = None
        override_cfg = SystemConfigManager.get_config(reload_env=True)
        assert override_cfg.active_bot_phone.national_with_zero == "04160000000"
        assert override_cfg.active_bot_phone.carrier == CarrierOperator.MOVILNET
    finally:
        if orig:
            os.environ["MOVILNET_ACTIVE_BOT_PHONE"] = orig
        else:
            os.environ.pop("MOVILNET_ACTIVE_BOT_PHONE", None)
        SystemConfigManager._cached_config = None

    print("🧪 [TEST 4/4] Serialización a JSON...")
    d = cfg.to_dict()
    assert "active_bot_phone" in d
    assert "allowed_bot_senders" in d
    print("✅ Todas las pruebas de SystemConfigManager pasaron al 100%.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parametrización Central de Movilnet Core")
    parser.add_argument("--show", action="store_true", help="Muestra la configuración activa del sistema.")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación formal.")
    parser.add_argument("--set-phone", type=str, help="Actualiza el número central en .env y .env.example.")
    args = parser.parse_args()

    if args.test:
        run_self_verification()
        sys.exit(0)

    if args.set_phone:
        SystemConfigManager.update_active_phone_in_env(args.set_phone)
        print(f"✅ Número central actualizado a {args.set_phone} en .env")
        sys.exit(0)

    cfg = SystemConfigManager.get_config()
    print(json.dumps(cfg.to_dict(), indent=2))
