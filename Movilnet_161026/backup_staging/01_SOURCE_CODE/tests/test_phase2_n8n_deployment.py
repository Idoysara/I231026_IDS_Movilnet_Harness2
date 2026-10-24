#!/usr/bin/env python3
"""
test_phase2_n8n_deployment.py — Pruebas de Despliegue, Activación y Verificación de n8n
========================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Fase 2: Paso 2 (Parte 2) — Certificación de Despliegue de Workflows en n8n
"""

import sys
import json
import unittest
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.deploy_n8n_workflows import N8nDeploymentOrchestrator, MANIFEST_PATH


class TestN8nDeploymentPipeline(unittest.TestCase):
    """Pruebas del pipeline de despliegue, manifiestos y gobernanza de n8n."""

    def setUp(self):
        self.orchestrator = N8nDeploymentOrchestrator()

    def test_compute_sha256(self):
        sample_file = PROJECT_ROOT / "requirements.txt"
        sha = self.orchestrator.compute_sha256(sample_file)
        self.assertEqual(len(sha), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in sha))

    def test_validate_workflow_data_valid(self):
        valid_wf = {
            "name": "Test Workflow",
            "nodes": [{"id": "n1", "name": "Node 1"}],
            "connections": {}
        }
        ok, reason = self.orchestrator.validate_workflow_data(valid_wf, "test.json")
        self.assertTrue(ok)
        self.assertEqual(reason, "VALID_WORKFLOW")

    def test_validate_workflow_data_missing_name(self):
        invalid_wf = {
            "nodes": [{"id": "n1", "name": "Node 1"}],
            "connections": {}
        }
        ok, reason = self.orchestrator.validate_workflow_data(invalid_wf, "test.json")
        self.assertFalse(ok)
        self.assertIn("no tiene 'name'", reason)

    def test_validate_workflow_data_duplicate_node_ids(self):
        invalid_wf = {
            "name": "Duplicated IDs",
            "nodes": [
                {"id": "node_dup", "name": "Node A"},
                {"id": "node_dup", "name": "Node B"}
            ],
            "connections": {}
        }
        ok, reason = self.orchestrator.validate_workflow_data(invalid_wf, "test.json")
        self.assertFalse(ok)
        self.assertIn("ID duplicado", reason)

    def test_execute_deployment_dry_run(self):
        manifest = self.orchestrator.execute_deployment(dry_run=True)
        self.assertEqual(manifest["overall_status"], "SUCCESS")
        self.assertGreaterEqual(manifest["total_deployed_successfully"], 4)
        self.assertEqual(manifest["validation_errors"], 0)
        self.assertTrue(MANIFEST_PATH.exists())

        # Verificar contenido del manifiesto
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)

        self.assertEqual(saved["overall_status"], "SUCCESS")
        self.assertGreaterEqual(len(saved["workflows"]), 4)

        paths = {w["webhook_path"] for w in saved["workflows"]}
        expected_paths = {
            "movilnet-whatsapp-webhook",
            "movilnet-telegram-webhook",
            "movilnet-c2p-webhook",
            "movilnet-eir-lock-webhook"
        }
        self.assertTrue(expected_paths.issubset(paths))


if __name__ == "__main__":
    unittest.main()
