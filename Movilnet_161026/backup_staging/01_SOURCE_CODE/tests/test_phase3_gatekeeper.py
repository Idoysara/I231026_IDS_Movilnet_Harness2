#!/usr/bin/env python3
"""
tests/test_phase3_gatekeeper.py — Suite Automatizada de Pruebas Gatekeeper 3
===========================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Hito: Fase 3 — Paso 5: Gatekeeper 3 Final de la Fase 3
Valida la auditoría integral y multidimensional para la certificación formal
de la Fase 3 completa: Enjambre Swarm L5, 4 Agentes, 5 Workflows n8n,
OpenAPI 3.1.0 TM Forum ODA, Seguridad SAST y Rendimiento Carrier-Grade.
"""

import json
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.gatekeeper_phase3 import GatekeeperPhase3Engine, compute_file_sha256
from db.repository import MovilnetRepository


class TestPhase3Gatekeeper(unittest.TestCase):
    """Batería de validación formal para el Gatekeeper 3 de la Fase 3."""

    @classmethod
    def setUpClass(cls):
        cls.engine = GatekeeperPhase3Engine()
        cls.repo = MovilnetRepository()

    def test_01_prior_step_certificates_validity(self):
        """Verifica que los certificados de los Pasos 1, 2, 3 y 4 de la Fase 3 existan y sean válidos."""
        d1 = self.engine.audit_dimension_1_step_certificates()
        self.assertTrue(d1["passed"], f"Fallo en Dimensión 1: {d1.get('checks')}")
        checks = d1["checks"]

        for step in ["paso1", "paso2", "paso3", "paso4"]:
            self.assertIn(step, checks)
            self.assertTrue(checks[step]["exists"])
            self.assertEqual(checks[step]["status"], "CERTIFICADO_Y_APROBADO_100%")
            self.assertEqual(len(checks[step]["sha256_cryptographic_seal"]), 64)
            self.assertGreater(checks[step]["tests_run"], 0)

    def test_02_dimension_2_swarm_l5_orchestration(self):
        """Verifica la coordinación en bucle cerrado del enjambre Swarm L5 entre los 4 agentes."""
        d2 = self.engine.audit_dimension_2_swarm_l5_orchestration()
        self.assertTrue(d2["passed"], f"Fallo en Dimensión 2 (Swarm L5): {d2.get('checks')}")
        checks = d2["checks"]

        # Handoff N1 -> N4
        self.assertTrue(checks["swarm_handoff_n1_to_n4_success"])
        # Handoff N3 -> N4
        self.assertTrue(checks["swarm_handoff_n3_to_n4_success"])
        # Canje y prevención de doble gasto de cupón en N2 / N4
        self.assertTrue(checks["coupon_validation_active"])
        self.assertTrue(checks["coupon_redemption_success"])
        self.assertTrue(checks["coupon_double_spending_prevented"])
        # Handoff N2 -> N3 y bloqueo por fraude
        self.assertTrue(checks["swarm_handoff_n2_to_n3_fraud_lock"])
        # Invalidación de memoria L1 en N1
        self.assertTrue(checks["l1_cache_invalidation_cross_agent"])

    def test_03_dimension_3_n8n_workflows_and_cicd(self):
        """Verifica los 5 workflows omnicanal de n8n y el manifiesto de despliegue CI/CD."""
        d3 = self.engine.audit_dimension_3_n8n_workflows_and_cicd()
        self.assertTrue(d3["passed"], f"Fallo en Dimensión 3 (n8n & CI/CD): {d3.get('checks')}")
        checks = d3["checks"]

        expected_wfs = [
            "movilnet_whatsapp_ai_workflow.json",
            "movilnet_telegram_ai_workflow.json",
            "movilnet_c2p_payment_workflow.json",
            "movilnet_incident_eir_lock_workflow.json",
            "movilnet_retention_churn_workflow.json"
        ]
        for wf in expected_wfs:
            self.assertTrue(checks[f"{wf}_exists"])
            self.assertTrue(checks[f"{wf}_has_min_nodes"])
            self.assertTrue(checks[f"{wf}_has_connections"])
            self.assertTrue(checks[f"{wf}_has_webhook_node"])

        self.assertTrue(checks["deploy_script_exists"])
        self.assertTrue(checks["manifest_file_exists"])
        self.assertEqual(checks["manifest_status"], "SUCCESS")
        self.assertGreaterEqual(checks["manifest_workflows_count"], 5)
        self.assertTrue(checks["all_webhook_endpoints_registered"])

    def test_04_dimension_4_api_and_openapi_contracts(self):
        """Verifica el microservicio REST API y el contrato formal OpenAPI 3.1.0 TM Forum ODA."""
        d4 = self.engine.audit_dimension_4_api_and_openapi()
        self.assertTrue(d4["passed"], f"Fallo en Dimensión 4 (API & OpenAPI): {d4.get('checks')}")
        checks = d4["checks"]

        self.assertTrue(checks["openapi_version_3_1_0"])
        self.assertGreaterEqual(checks["total_paths"], 23)
        self.assertGreaterEqual(checks["total_schemas"], 29)
        self.assertTrue(checks["all_agent_endpoints_registered"])
        self.assertTrue(checks["all_required_agent_schemas_registered"])
        self.assertTrue(checks["endpoint_health_200"])
        self.assertTrue(checks["endpoint_retention_status_200"])
        self.assertTrue(checks["endpoint_eir_status_200"])

    def test_05_dimension_5_security_sast_and_timing_defense(self):
        """Verifica la auditoría SAST contra secretos y el uso de timing attack defense."""
        d5 = self.engine.audit_dimension_5_security_and_sast()
        self.assertTrue(d5["passed"], f"Fallo en Dimensión 5 (Seguridad SAST): {d5.get('checks')}")
        checks = d5["checks"]

        self.assertEqual(checks["hardcoded_secrets_found"], 0)
        self.assertTrue(checks["zero_secrets_exposed"])
        self.assertTrue(checks["hmac_compare_digest_used"])

    def test_06_dimension_6_carrier_grade_latency_benchmarks(self):
        """Verifica el cumplimiento de SLAs de latencia Carrier-Grade en los 4 agentes y el backend."""
        d6 = self.engine.audit_dimension_6_performance_and_latency()
        self.assertTrue(d6["passed"], f"Fallo en Dimensión 6 (Rendimiento): {d6.get('checks')}")
        checks = d6["checks"]

        self.assertTrue(checks["db_sla_passed"])
        self.assertTrue(checks["agent_n1_sla_passed"])
        self.assertTrue(checks["agent_n2_sla_passed"])
        self.assertTrue(checks["agent_n3_sla_passed"])
        self.assertTrue(checks["agent_n4_sla_passed"])
        self.assertTrue(checks["agent_n4_fallback_valid"])
        self.assertLess(checks["agent_n4_ml_avg_ms"], 5.0)

    def test_07_full_audit_execution_and_certification_issuance(self):
        """Ejecuta la auditoría integral y valida la emisión formal del Certificado Gatekeeper 3."""
        report = self.engine.run_full_audit()
        self.assertEqual(report["status"], "CERTIFICADO_Y_APROBADO_100%")
        self.assertIn("Fase 3 de AI_Movilnet_300926 validada", report["verdict"])

        cert_path = PROJECT_ROOT / "reports" / "CERTIFICATION_FASE3_GATEKEEPER.json"
        self.assertTrue(cert_path.exists())

        with open(cert_path, "r", encoding="utf-8") as f:
            cert = json.load(f)

        self.assertEqual(cert["status"], "CERTIFICADO_Y_APROBADO_100%")
        self.assertEqual(cert["phase"], "FASE_3_AI_CORE_AND_MULTI_AGENT_SWARM")
        self.assertEqual(cert["step"], "PASO_5_GATEKEEPER_3_FINAL_FASE_3")
        self.assertEqual(cert["metrics"]["dimensions_evaluated"], 6)
        self.assertEqual(cert["metrics"]["dimensions_passed"], 6)
        self.assertEqual(cert["metrics"]["agents_certified"], 4)
        self.assertEqual(cert["metrics"]["n8n_workflows_deployed"], 5)
        self.assertEqual(len(cert["sha256_cryptographic_seal"]), 64)

    def test_08_cryptographic_integrity_hashes_coverage(self):
        """Verifica que todos los archivos clave de la Fase 3 cuenten con hash SHA-256 en el informe."""
        report = self.engine.run_full_audit()
        hashes = report["integrity_hashes"]
        self.assertGreaterEqual(len(hashes), 15)

        for filename, file_hash in hashes.items():
            self.assertNotEqual(file_hash, "FILE_NOT_FOUND", f"Archivo clave no encontrado: {filename}")
            self.assertEqual(len(file_hash), 64)


if __name__ == "__main__":
    unittest.main()
