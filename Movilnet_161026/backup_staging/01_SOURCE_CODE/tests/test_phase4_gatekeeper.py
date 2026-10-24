#!/usr/bin/env python3
"""
tests/test_phase4_gatekeeper.py — Suite Automatizada de Pruebas Gatekeeper 4
===========================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Hito: Fase 4 — Paso 5: Gatekeeper 4 Final de la Fase 4
Valida la auditoría integral y multidimensional para la certificación formal
de la Fase 4 completa: Design System WCAG AAA, Dashboard NOC/CCO, Portal PWA,
Seguridad SAST y Rendimiento E2E Omnicanal Carrier-Grade.
"""

import json
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.gatekeeper_phase4 import GatekeeperPhase4Engine, compute_file_sha256
from api.service import MovilnetAPIService


class TestPhase4Gatekeeper(unittest.TestCase):
    """Batería de validación formal para el Gatekeeper 4 de la Fase 4."""

    @classmethod
    def setUpClass(cls):
        cls.service = MovilnetAPIService()
        cls.engine = GatekeeperPhase4Engine(service=cls.service)

    def test_01_dimension_1_prior_step_certificates_validity(self):
        """Verifica que los certificados de los Pasos 1, 2, 3 y 4 de la Fase 4 existan y sean válidos."""
        d1 = self.engine.audit_dimension_1_step_certificates()
        self.assertTrue(d1["passed"], f"Fallo en Dimensión 1: {d1.get('checks')}")
        checks = d1["checks"]

        for step in ["paso1", "paso2", "paso3", "paso4"]:
            self.assertIn(step, checks)
            self.assertTrue(checks[step]["exists"])
            self.assertEqual(checks[step]["status"], "CERTIFICADO_Y_APROBADO_100%")
            self.assertEqual(len(checks[step]["sha256_cryptographic_seal"]), 64)
            self.assertGreater(checks[step]["tests_run"], 0)

    def test_02_dimension_2_design_system_and_wcag_aaa(self):
        """Verifica design tokens, CSS modular, accesibilidad WCAG 2.1 AAA y tap targets."""
        d2 = self.engine.audit_dimension_2_design_system_and_wcag()
        self.assertTrue(d2["passed"], f"Fallo en Dimensión 2 (Design System): {d2.get('checks')}")
        checks = d2["checks"]

        self.assertTrue(checks["wcag_aaa_contrast_pass"])
        self.assertGreaterEqual(checks["contrast_night_white"], 7.0)
        self.assertGreaterEqual(checks["contrast_card_white"], 7.0)
        self.assertGreaterEqual(checks["contrast_pwa_white"], 7.0)
        self.assertGreaterEqual(checks["contrast_orange_dark"], 4.5)
        self.assertTrue(checks["tap_targets_accessible"])

    def test_03_dimension_3_noc_dashboard_telemetry(self):
        """Verifica la sala de control NOC/CCO, endpoints de telemetría y monitoreo de 4M abonados."""
        d3 = self.engine.audit_dimension_3_noc_dashboard_telemetry()
        self.assertTrue(d3["passed"], f"Fallo en Dimensión 3 (NOC Dashboard): {d3.get('checks')}")
        checks = d3["checks"]

        self.assertEqual(checks["telemetry_endpoint_status"], 200)
        self.assertEqual(checks["subscribers_total"], 4000000)
        self.assertTrue(checks["swarm_monitored"])
        self.assertTrue(checks["c2p_monitored"])
        self.assertTrue(checks["network_monitored"])
        self.assertTrue(checks["telemetry_data_valid"])

    def test_04_dimension_4_pwa_mobile_portal(self):
        """Verifica la especificación W3C PWA, Service Worker, manifest y lógica OCS/C2P."""
        d4 = self.engine.audit_dimension_4_pwa_mobile_portal()
        self.assertTrue(d4["passed"], f"Fallo en Dimensión 4 (PWA Móvil): {d4.get('checks')}")
        checks = d4["checks"]

        self.assertTrue(checks["manifest_w3c_compliant"])
        self.assertTrue(checks["service_worker_offline_ready"])

    def test_05_dimension_5_sast_security_and_secrets(self):
        """Verifica ausencia de secretos en duro y seguridad estricta HMAC-SHA256 en webhooks."""
        d5 = self.engine.audit_dimension_5_sast_security_and_secrets()
        self.assertTrue(d5["passed"], f"Fallo en Dimensión 5 (Seguridad SAST): {d5.get('checks')}")
        checks = d5["checks"]

        self.assertEqual(checks["hardcoded_secrets_detected"], 0)
        self.assertTrue(checks["zero_secrets_leaked"])
        self.assertTrue(checks["hmac_anti_replay_enforced"])

    def test_06_dimension_6_e2e_stress_performance_sla(self):
        """Verifica el cumplimiento de SLAs carrier-grade en ráfagas concurrentes masivas."""
        d6 = self.engine.audit_dimension_6_e2e_stress_performance()
        self.assertTrue(d6["passed"], f"Fallo en Dimensión 6 (Rendimiento E2E): {d6.get('checks')}")
        checks = d6["checks"]

        self.assertEqual(checks["total_requests"], 100)
        self.assertTrue(checks["success_rate_ge_99"])
        self.assertTrue(checks["throughput_ge_50"])
        self.assertTrue(checks["p95_latency_le_250"])

    def test_07_full_gatekeeper_execution_and_reports(self):
        """Verifica que la ejecución completa de Gatekeeper 4 emita los reportes y certificados oficiales."""
        passed, report_p, cert_p = self.engine.run_full_audit()
        self.assertTrue(passed)
        self.assertTrue(report_p.exists())
        self.assertTrue(cert_p.exists())

        cert_data = json.loads(cert_p.read_text(encoding="utf-8"))
        self.assertEqual(cert_data["status"], "CERTIFICADO_Y_APROBADO_100%")
        self.assertEqual(cert_data["dimensions_evaluated"], 6)
        self.assertEqual(cert_data["dimensions_passed"], 6)
        self.assertEqual(len(cert_data["sha256_cryptographic_seal"]), 64)


if __name__ == "__main__":
    unittest.main()
