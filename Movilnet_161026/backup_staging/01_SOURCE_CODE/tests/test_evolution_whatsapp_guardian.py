#!/usr/bin/env python3
"""
tests/test_evolution_whatsapp_guardian.py — Pruebas Automatizadas para el Guardián de WhatsApp
=============================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
"""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evolution_whatsapp_guardian import EvolutionWhatsAppGuardian, WhatsAppHealthStatus


class TestEvolutionWhatsAppGuardian(unittest.TestCase):
    """Suite de verificación para sanitización, detección de PENDING y salud de Evolution API."""

    def setUp(self):
        self.guardian = EvolutionWhatsAppGuardian()

    def test_01_sanitize_jid_with_domain(self):
        """Verifica que @s.whatsapp.net sea limpiado dejando solo dígitos."""
        clean = self.guardian.sanitize_recipient_number("584143189769@s.whatsapp.net")
        self.assertEqual(clean, "584143189769")

    def test_02_sanitize_lid_privacy_id(self):
        """Verifica que identificadores @lid de WhatsApp sean limpiados."""
        clean = self.guardian.sanitize_recipient_number("96559488323823@lid")
        self.assertEqual(clean, "96559488323823")

    def test_03_sanitize_venezuelan_national_format(self):
        """Verifica conversión de 0414... a 58414..."""
        clean = self.guardian.sanitize_recipient_number("0414-3189769")
        self.assertEqual(clean, "584143189769")

    def test_04_audit_outgoing_payload_interception(self):
        """Detecta payload malformado con sufijo y lo corrige automáticamente."""
        raw_payload = {
            "instanceId": "Viki LPGTEC",
            "number": "584143189769@s.whatsapp.net",
            "text": "Prueba de comida china"
        }
        res = self.guardian.audit_outgoing_message_payload(raw_payload)
        self.assertTrue(res["is_compliant"])
        self.assertEqual(res["corrected_payload"]["number"], "584143189769")
        self.assertIn("Contiene sufijo JID '@s.whatsapp.net'", res["detected_issues"][0])

    def test_05_detect_pending_status_and_remediation(self):
        """Detecta mensaje estancado en PENDING y emite pasos de remediación."""
        log_sample = {
            "key": {"remoteJid": "584143189769@s.whatsapp.net", "id": "3EB0BDE48D5588422EA5F4C451DA539DE62BCDFA"},
            "status": "PENDING"
        }
        res = self.guardian.inspect_execution_log(log_sample)
        self.assertTrue(res["is_stuck_pending"])
        self.assertGreaterEqual(len(res["remediation_steps"]), 4)
        self.assertIn("+58 416 625 1587", res["remediation_steps"][0])

    def test_06_health_check_status(self):
        """Comprueba que el chequeo de salud retorne objeto tipado y estructurado."""
        status = self.guardian.run_health_check()
        self.assertIsInstance(status, WhatsAppHealthStatus)
        self.assertEqual(status.overall_health, "HEALTHY_CONNECTED")
        self.assertTrue(status.sanitized_routing_active)

    def test_07_human_typing_cadence(self):
        """Valida que la cadencia humana adapte el retardo según longitud con límites seguros."""
        short_delay = self.guardian.calculate_human_typing_cadence("Hola", jitter_ms=0)
        med_delay = self.guardian.calculate_human_typing_cadence("A" * 100, jitter_ms=0)
        long_delay = self.guardian.calculate_human_typing_cadence("A" * 350, jitter_ms=0)

        self.assertGreaterEqual(short_delay, 650)
        self.assertLessEqual(short_delay, 1000)
        self.assertGreater(med_delay, short_delay)
        self.assertGreater(long_delay, med_delay)
        self.assertLessEqual(long_delay, 2200)

    def test_08_audit_outgoing_payload_injects_human_presence(self):
        """Valida que los paquetes salientes inyecten presence composing y delay adaptativo."""
        payload = {"number": "04143189769", "text": "Mensaje de prueba"}
        res = self.guardian.audit_outgoing_message_payload(payload)
        corrected = res["corrected_payload"]
        self.assertIn("options", corrected)
        self.assertEqual(corrected["options"]["presence"], "composing")
        self.assertGreaterEqual(corrected["options"]["delay"], 650)
        self.assertLessEqual(corrected["options"]["delay"], 2200)


if __name__ == "__main__":
    unittest.main()

