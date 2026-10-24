#!/usr/bin/env python3
"""
tests/test_phase2_gatekeeper.py — Suite Automatizada de Pruebas Gatekeeper 2
===========================================================================
Valida la suite de pruebas unitarias y de integración del Gatekeeper 2 para
la certificación formal de la Fase 2 completa de AI_Movilnet_300926.
"""

import json
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.gatekeeper_phase2 import GatekeeperPhase2Engine, compute_file_sha256
from db.repository import MovilnetRepository


class TestPhase2Gatekeeper(unittest.TestCase):
    """Batería de pruebas automatizadas para el Gatekeeper 2 de la Fase 2."""

    @classmethod
    def setUpClass(cls):
        cls.engine = GatekeeperPhase2Engine()
        cls.repo = MovilnetRepository()
        # Asegurar línea de prueba activa
        cls.repo.update_line_status("04160000001", "ACTIVO")

    @classmethod
    def tearDownClass(cls):
        # Restaurar línea en estado activo
        cls.repo.update_line_status("04160000001", "ACTIVO")

    def test_gatekeeper_prior_step_certificates_validity(self):
        """Verifica que los certificados de los Pasos 1, 2 y 3 existan y sean válidos."""
        audit_res = self.engine.audit_step_certificates()
        self.assertTrue(audit_res["step_certificates_valid"])
        details = audit_res["details"]
        
        self.assertIn("paso1", details)
        self.assertIn("paso2", details)
        self.assertIn("paso3", details)

        for step in ["paso1", "paso2", "paso3"]:
            self.assertTrue(details[step]["exists"])
            self.assertEqual(details[step]["status"], "CERTIFICADO_Y_APROBADO_100%")
            self.assertTrue(len(details[step]["sha256_cryptographic_seal"]) == 64)

    def test_gatekeeper_dimension_1_api_and_openapi(self):
        """Verifica el cumplimiento estricto de la Dimensión 1: REST API & OpenAPI 3.1.0."""
        d1 = self.engine.audit_dimension_1_api_and_openapi()
        self.assertTrue(d1["passed"], f"Fallo en Dimensión 1: {d1.get('checks')}")
        checks = d1["checks"]
        self.assertTrue(checks["openapi_version_3_1_0"])
        self.assertGreaterEqual(checks["total_paths"], 16)
        self.assertGreaterEqual(checks["total_schemas"], 17)
        self.assertTrue(checks["all_required_endpoints_present"])
        self.assertTrue(checks["all_required_schemas_present"])
        self.assertTrue(checks["api_health_dispatch_success"])
        self.assertTrue(checks["api_swagger_ui_available"])

    def test_gatekeeper_dimension_2_n8n_workflows(self):
        """Verifica el cumplimiento estricto de la Dimensión 2: Workflows n8n."""
        d2 = self.engine.audit_dimension_2_n8n_workflows()
        self.assertTrue(d2["passed"], f"Fallo en Dimensión 2: {d2.get('checks')}")
        checks = d2["checks"]
        for wf in [
            "movilnet_whatsapp_ai_workflow.json",
            "movilnet_telegram_ai_workflow.json",
            "movilnet_c2p_payment_workflow.json",
            "movilnet_incident_eir_lock_workflow.json"
        ]:
            self.assertTrue(checks[f"{wf}_exists"])
            self.assertTrue(checks[f"{wf}_has_min_nodes"])
            self.assertTrue(checks[f"{wf}_has_connections"])
            self.assertTrue(checks[f"{wf}_has_webhook_node"])

    def test_gatekeeper_dimension_3_cicd_deployment_manifest(self):
        """Verifica el cumplimiento estricto de la Dimensión 3: Pipeline CI/CD & Manifiesto."""
        d3 = self.engine.audit_dimension_3_cicd_deployment()
        self.assertTrue(d3["passed"], f"Fallo en Dimensión 3: {d3.get('checks')}")
        checks = d3["checks"]
        self.assertTrue(checks["deploy_script_exists"])
        self.assertTrue(checks["manifest_file_exists"])
        self.assertEqual(checks["overall_status"], "SUCCESS")
        self.assertGreaterEqual(checks["workflows_deployed_count"], 4)
        self.assertTrue(checks["workflows_metadata_complete"])

    def test_gatekeeper_dimension_4_webhook_and_mcp(self):
        """Verifica el cumplimiento estricto de la Dimensión 4: Webhooks & Suites MCP."""
        d4 = self.engine.audit_dimension_4_webhook_and_mcp()
        self.assertTrue(d4["passed"], f"Fallo en Dimensión 4: {d4.get('checks')}")
        checks = d4["checks"]
        self.assertTrue(checks["hmac_verification_nominal"])
        self.assertTrue(checks["anti_replay_expired_rejected"])
        self.assertTrue(checks["idempotency_deduplication_works"])
        self.assertTrue(checks["mcp_suite_1_telco_operational"])
        self.assertTrue(checks["mcp_suite_2_fintech_operational"])
        self.assertTrue(checks["mcp_suite_3_crm_operational"])
        self.assertTrue(checks["mcp_suite_4_privacy_operational"])
        self.assertTrue(checks["mcp_suite_5_whatsapp_operational"])
        self.assertTrue(checks["all_5_mcp_suites_operational"])

    def test_gatekeeper_dimension_5_security_and_sast(self):
        """Verifica el cumplimiento estricto de la Dimensión 5: Seguridad SAST y Prevención de Timing Attacks."""
        d5 = self.engine.audit_dimension_5_security_and_sast()
        self.assertTrue(d5["passed"], f"Fallo en Dimensión 5: {d5.get('checks')}")
        checks = d5["checks"]
        self.assertEqual(checks["hardcoded_secrets_detected"], 0)
        self.assertTrue(checks["zero_hardcoded_secrets_passed"])
        self.assertTrue(checks["timing_attack_resistant_compare_digest"])

    def test_gatekeeper_dimension_6_carrier_grade_latency(self):
        """Verifica el cumplimiento de SLAs de latencia Carrier-Grade en DB, API y Webhooks."""
        d6 = self.engine.audit_dimension_6_performance_and_latency()
        self.assertTrue(d6["passed"], f"Fallo en Dimensión 6: {d6.get('checks')}")
        checks = d6["checks"]
        self.assertTrue(checks["db_p95_sub_2ms"])
        self.assertTrue(checks["api_p95_sub_5ms"])
        self.assertTrue(checks["webhook_p95_sub_10ms"])

    def test_gatekeeper_end_to_end_audit_and_certification(self):
        """Ejecuta la auditoría integral completa y verifica la emisión del certificado oficial."""
        engine = GatekeeperPhase2Engine()
        cert = engine.run_full_audit()

        self.assertEqual(cert.get("status"), "CERTIFICADO_Y_APROBADO_100%")
        self.assertTrue(engine.all_passed)
        self.assertIn("Fase 2 de AI_Movilnet_300926 validada", cert.get("verdict", ""))
        self.assertTrue(len(cert.get("sha256_cryptographic_seal", "")) == 64)

        report_file = PROJECT_ROOT / "reports" / "gatekeeper_phase2_report.json"
        cert_file = PROJECT_ROOT / "reports" / "CERTIFICATION_FASE2_GATEKEEPER.json"
        self.assertTrue(report_file.exists())
        self.assertTrue(cert_file.exists())


if __name__ == "__main__":
    unittest.main()
