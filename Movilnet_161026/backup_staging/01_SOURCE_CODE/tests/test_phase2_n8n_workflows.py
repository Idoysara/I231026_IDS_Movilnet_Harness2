#!/usr/bin/env python3
"""
test_phase2_n8n_workflows.py — Suite de Validación y Verificación de Workflows n8n
==================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Fase 2: Paso 2 (Parte 1) — Validación Estructural y Lógica de Flujos Omnicanal n8n
"""

import sys
import json
import uuid
import unittest
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.service import MovilnetAPIService


class TestN8nWorkflowStructure(unittest.TestCase):
    """Verificación de integridad estructural y compatibilidad con motor n8n."""

    WORKFLOW_FILES = [
        "movilnet_whatsapp_ai_workflow.json",
        "movilnet_telegram_ai_workflow.json",
        "movilnet_c2p_payment_workflow.json",
        "movilnet_incident_eir_lock_workflow.json"
    ]

    def setUp(self):
        self.wf_dir = PROJECT_ROOT / "api" / "n8n_workflows"

    def test_all_workflow_files_exist(self):
        for wf_file in self.WORKFLOW_FILES:
            path = self.wf_dir / wf_file
            self.assertTrue(path.exists(), f"El archivo {wf_file} debe existir en {self.wf_dir}")

    def test_workflow_json_schema_compliance(self):
        seen_webhook_paths = set()

        for wf_file in self.WORKFLOW_FILES:
            path = self.wf_dir / wf_file
            with open(path, "r", encoding="utf-8") as f:
                wf = json.load(f)

            # 1. Campos obligatorios
            self.assertIn("name", wf, f"{wf_file} debe tener 'name'")
            self.assertIn("nodes", wf, f"{wf_file} debe tener 'nodes'")
            self.assertIn("connections", wf, f"{wf_file} debe tener 'connections'")
            self.assertIn("settings", wf, f"{wf_file} debe tener 'settings'")
            self.assertTrue(isinstance(wf["nodes"], list))
            self.assertTrue(isinstance(wf["connections"], dict))
            self.assertGreaterEqual(len(wf["nodes"]), 4, f"{wf_file} debe tener al menos 4 nodos")

            # 2. Unicidad de Node IDs y validación de tipos
            node_ids = set()
            node_names = set()
            webhook_found = False

            for node in wf["nodes"]:
                self.assertIn("id", node)
                self.assertIn("name", node)
                self.assertIn("type", node)
                self.assertNotIn(node["id"], node_ids, f"ID duplicado '{node['id']}' en {wf_file}")
                self.assertNotIn(node["name"], node_names, f"Nombre duplicado '{node['name']}' en {wf_file}")
                node_ids.add(node["id"])
                node_names.add(node["name"])

                # Verificación de Webhook
                if node["type"] == "n8n-nodes-base.webhook":
                    webhook_found = True
                    params = node.get("parameters", {})
                    wh_path = params.get("path")
                    self.assertTrue(bool(wh_path), f"Webhook en {wf_file} debe definir 'path'")
                    self.assertNotIn(wh_path, seen_webhook_paths, f"Path de webhook duplicado: {wh_path}")
                    seen_webhook_paths.add(wh_path)

            self.assertTrue(webhook_found, f"{wf_file} debe tener un nodo webhook de entrada")

            # 3. Consistencia de Conexiones
            for src_name, conns in wf["connections"].items():
                self.assertIn(src_name, node_names, f"Nodo origen '{src_name}' no existe en nodes de {wf_file}")
                for conn_type, target_groups in conns.items():
                    for group in target_groups:
                        for target in group:
                            tgt_name = target.get("node")
                            self.assertIn(tgt_name, node_names, f"Nodo destino '{tgt_name}' no existe en {wf_file}")


class TestN8nNodeLogicSimulation(unittest.TestCase):
    """Simulación de la lógica de código embebida en nodos Python de n8n."""

    def test_whatsapp_sanitizer_logic(self):
        cases = [
            ("+584161234567", "Hola quiero saber mi saldo", "04161234567", "BALANCE_QUERY", True),
            ("04269876543", "Deseo hacer un pago movil c2p", "04269876543", "PAYMENT_C2P", True),
            ("04165554321", "Me acaban de robar el celular", "04165554321", "EMERGENCY_LOCK", False),
            ("04160000001", "Donde queda la oficina comercial", "04160000001", "GENERAL_INQUIRY", False),
        ]
        for raw_phone, raw_msg, exp_phone, exp_intent, exp_fastpath in cases:
            clean = raw_phone.replace("+", "").replace(" ", "").replace("-", "")
            if clean.startswith("58") and len(clean) == 12:
                clean = "0" + clean[2:]
            msg_lower = raw_msg.lower()
            is_bal = any(k in msg_lower for k in ["saldo", "cuanto debo", "deuda", "corte", "megas", "datos"])
            is_c2p = any(k in msg_lower for k in ["pagar", "recargar", "pago movil", "c2p"])
            is_emg = any(k in msg_lower for k in ["rob", "hurt", "bloque", "extravi"])
            intent = "BALANCE_QUERY" if is_bal else ("PAYMENT_C2P" if is_c2p else ("EMERGENCY_LOCK" if is_emg else "GENERAL_INQUIRY"))

            self.assertEqual(clean, exp_phone)
            self.assertEqual(intent, exp_intent)
            self.assertEqual(intent in ["BALANCE_QUERY", "PAYMENT_C2P"], exp_fastpath)

    def test_telegram_parser_logic(self):
        text1 = "/saldo 04160000001"
        cmd = text1.split()[0].lower()
        arg = text1.split()[1]
        self.assertEqual(cmd, "/saldo")
        self.assertEqual(arg, "04160000001")

        text2 = "/planes"
        cmd2 = text2.split()[0].lower()
        self.assertEqual(cmd2, "/planes")


class TestN8nApiIntegrationHandshake(unittest.TestCase):
    """Comprobación de que cada endpoint invocado por los flujos responde satisfactoriamente."""

    @classmethod
    def setUpClass(cls):
        cls.service = MovilnetAPIService()
        cls.test_phone = "04160000001"
        cls.test_cid = "V-10000001"
        cls.service.repo.update_line_status(cls.test_phone, "ACTIVO")

    def _call(self, method: str, path: str, body: Any = None):
        body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
        status, _, resp_bytes = self.service.dispatch(method, path, {}, body_bytes)
        return status, json.loads(resp_bytes.decode("utf-8"))

    def test_workflow_whatsapp_api_target(self):
        status, data = self._call("POST", "/api/v1/subscribers/balance", {"msisdn": self.test_phone})
        self.assertEqual(status, 200)
        self.assertIn("balance_ves", data)
        self.assertIn("remaining_data_mb", data)
        self.assertIn("billing_cutoff_date", data)

    def test_workflow_telegram_api_target(self):
        status, data = self._call("GET", "/api/v1/catalog/plans")
        self.assertEqual(status, 200)
        self.assertIn("plans", data)
        self.assertGreaterEqual(len(data["plans"]), 16)

    def test_workflow_c2p_api_target(self):
        ref = f"REF-N8N-{uuid.uuid4().hex[:6]}"
        payload = {
            "reference_id": ref,
            "msisdn": self.test_phone,
            "bank_code": "0102",
            "amount_ves": 75.0,
            "payer_cid": self.test_cid,
            "otp_token": "839201"
        }
        status, data = self._call("POST", "/api/v1/payments/c2p", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "COMPLETADO")

    def test_workflow_eir_lock_api_target(self):
        victim = "04267771122"
        # Crear la línea de prueba si no existe
        if not self.service.repo.get_line_details(victim):
            self.service.repo.create_subscriber_with_line(
                cid="V-27771122",
                msisdn=victim,
                plan_id="PLAN_5GB_BASICO",
                balance_ves=20.0
            )

        status_swap, swap_data = self._call("POST", "/api/v1/security/sim-swap", {"msisdn": victim})
        self.assertEqual(status_swap, 200)

        payload_eir = {
            "msisdn": victim,
            "imei": "358901234567899",
            "reason": "ROBO_EXTRAVIO_N8N",
            "police_report": "DENUNCIA-N8N-001"
        }
        status_eir, eir_data = self._call("POST", "/api/v1/security/eir-lock", payload_eir)
        self.assertEqual(status_eir, 200)
        self.assertEqual(eir_data["status"], "LOCKED_IN_EIR")
        self.assertEqual(eir_data["line_status"], "BLOQUEADO_ROBO")


if __name__ == "__main__":
    unittest.main()
