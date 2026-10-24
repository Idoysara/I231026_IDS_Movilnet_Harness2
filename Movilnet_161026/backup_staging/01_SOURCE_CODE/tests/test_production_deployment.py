#!/usr/bin/env python3
"""
tests/test_production_deployment.py — Suite Automatizada de Verificación de Producción
======================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Hito: Certificación de Despliegue de Producción, SRE Watchdog y Alta Disponibilidad Carrier-Grade.
"""

import json
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REPORTS_DIR = PROJECT_ROOT / "reports"
from scripts.deploy_production import ProductionDeploymentPipeline
from scripts.disaster_recovery_watchdog import DisasterRecoveryWatchdog


class TestProductionDeployment(unittest.TestCase):
    """Batería de validación formal del despliegue en producción y recuperación en frío."""

    @classmethod
    def setUpClass(cls):
        cls.pipeline = ProductionDeploymentPipeline()
        cls.watchdog = DisasterRecoveryWatchdog()

    def test_01_all_phase_certificates_integrity(self):
        """Verifica que las Fases 0 a 4 posean certificados válidos y sellos SHA-256."""
        ok = self.pipeline.stage_1_verify_certificates()
        self.assertTrue(ok)
        checks = self.pipeline.results["stages"]["stage_1_certificates"]["checks"]
        self.assertEqual(len(checks), 5)
        for cert_file, detail in checks.items():
            self.assertTrue(detail["exists"], f"Certificado no encontrado: {cert_file}")
            self.assertTrue(detail["valid"], f"Certificado no válido: {cert_file}")

    def test_02_database_wal_preflight_and_catalogs(self):
        """Verifica la persistencia de base de datos WAL, catálogo de 16 planes y 23 bancos."""
        ok = self.pipeline.stage_2_database_preflight()
        self.assertTrue(ok)
        db_stage = self.pipeline.results["stages"]["stage_2_database"]
        self.assertGreaterEqual(db_stage["active_plans"], 4)
        self.assertGreaterEqual(db_stage["sudeban_banks"], 20)
        self.assertTrue(db_stage["sample_subscriber_found"])

    def test_03_openapi_formal_contract_export(self):
        """Verifica la exportación formal y cobertura del contrato OpenAPI 3.1.0."""
        ok = self.pipeline.stage_3_openapi_synchronization()
        self.assertTrue(ok)
        openapi_stage = self.pipeline.results["stages"]["stage_3_openapi"]
        self.assertGreaterEqual(openapi_stage["paths_count"], 25)
        self.assertGreaterEqual(openapi_stage["schemas_count"], 30)

    def test_04_n8n_workflows_and_webhooks_readiness(self):
        """Verifica el estado del manifiesto de despliegue de los 5 flujos omnicanal n8n."""
        ok = self.pipeline.stage_4_n8n_workflows_readiness()
        self.assertTrue(ok)
        n8n_stage = self.pipeline.results["stages"]["stage_4_n8n"]
        self.assertEqual(n8n_stage["status"], "SUCCESS")
        self.assertGreaterEqual(n8n_stage["workflows_count"], 5)

    def test_05_http_dispatch_and_telemetry_health(self):
        """Verifica la respuesta en 200 de /health, /api/v1/metrics/live y /ui/pwa/index.html."""
        ok = self.pipeline.stage_5_healthcheck_and_endpoints()
        self.assertTrue(ok)
        ep_stage = self.pipeline.results["stages"]["stage_5_endpoints"]
        self.assertEqual(ep_stage["status_health"], 200)
        self.assertEqual(ep_stage["status_noc_metrics"], 200)
        self.assertEqual(ep_stage["status_pwa_portal"], 200)

    def test_06_e2e_smoke_traffic_burst(self):
        """Verifica que el smoke test de tráfico concurrente omnicanal supere el 100% de éxito."""
        ok = self.pipeline.stage_6_stress_smoke_test()
        self.assertTrue(ok)
        smoke = self.pipeline.results["stages"]["stage_6_smoke_test"]
        self.assertEqual(smoke["success_rate_pct"], 100.0)
        self.assertGreater(smoke["throughput_tps"], 50.0)
        self.assertLess(smoke["p95_latency_ms"], 250.0)

    def test_07_disaster_recovery_watchdog_audit(self):
        """Verifica que el watchdog de arranque en frío certifique integridad de persistencia y APIs."""
        audit = self.watchdog.execute_cold_start_audit()
        self.assertEqual(audit["system_status"], "HEALTHY")
        self.assertEqual(audit["database_integrity"]["integrity_check"], "ok")
        self.assertEqual(audit["api_health_code"], 200)
        self.assertEqual(audit["noc_metrics_code"], 200)
        self.assertIn("CONFORME", audit["carrier_sla"])

    def test_08_full_deployment_pipeline_execution(self):
        """Verifica que la ejecución del pipeline emita el manifiesto oficial con firma SHA-256."""
        success, manifest_path = self.pipeline.execute_deployment()
        self.assertTrue(success)
        self.assertTrue(manifest_path.exists())

        mani = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(mani["status"], "SUCCESS")
        self.assertEqual(len(mani["sha256_cryptographic_seal"]), 64)


if __name__ == "__main__":
    unittest.main()
