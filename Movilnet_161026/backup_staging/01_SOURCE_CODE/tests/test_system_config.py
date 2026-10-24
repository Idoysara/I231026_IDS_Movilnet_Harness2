#!/usr/bin/env python3
"""
tests/test_system_config.py — Suite de Pruebas de la Parametrización Centralizada
================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: 100% Pass)
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.system_config import SystemConfigManager, MovilnetCoreConfig, run_self_verification
from core.phone_migration_models import CarrierOperator


class TestSystemConfig(unittest.TestCase):
    """Pruebas unitarias de la parametrización central de Movilnet Core."""

    def setUp(self):
        SystemConfigManager._cached_config = None

    def tearDown(self):
        SystemConfigManager._cached_config = None

    def test_01_load_default_config(self):
        """Verifica la carga de configuración por defecto y tipos estrictos."""
        cfg = SystemConfigManager.get_config(reload_env=True)
        self.assertIsInstance(cfg, MovilnetCoreConfig)
        self.assertIn(cfg.active_bot_phone.international_digits, ["584241533712", "584166251587"])
        self.assertEqual(cfg.port, 8010)
        self.assertIn(cfg.bot_name, ["MOVI", "VIKI"])

    def test_02_environment_override(self):
        """Verifica que os.environ['MOVILNET_ACTIVE_BOT_PHONE'] tenga precedencia."""
        orig = os.environ.get("MOVILNET_ACTIVE_BOT_PHONE")
        try:
            os.environ["MOVILNET_ACTIVE_BOT_PHONE"] = "0416-5551234"
            cfg = SystemConfigManager.get_config(reload_env=True)
            self.assertEqual(cfg.active_bot_phone.national_formatted, "0416-5551234")
            self.assertEqual(cfg.active_bot_phone.carrier, CarrierOperator.MOVILNET)
            self.assertIn("584165551234@s.whatsapp.net", cfg.allowed_bot_senders)
        finally:
            if orig:
                os.environ["MOVILNET_ACTIVE_BOT_PHONE"] = orig
            else:
                os.environ.pop("MOVILNET_ACTIVE_BOT_PHONE", None)
            SystemConfigManager._cached_config = None

    def test_03_allowed_senders_set(self):
        """Verifica que el set de senders contenga el activo y excluya la lista negra."""
        senders = SystemConfigManager.get_allowed_bot_senders()
        self.assertIn("584241533712@s.whatsapp.net", senders)
        self.assertNotIn("584166251587@s.whatsapp.net", senders)
        self.assertTrue(SystemConfigManager.is_blacklisted("00584166251587"))
        self.assertTrue(SystemConfigManager.is_blacklisted("584166251587"))
        self.assertTrue(SystemConfigManager.is_blacklisted("04166251587"))

    def test_04_self_verification(self):
        """Ejecuta la auto-verificación formal del módulo."""
        self.assertTrue(run_self_verification())


if __name__ == "__main__":
    unittest.main()
