#!/usr/bin/env python3
"""
scripts/test_edge_carrier_firewall.py
======================================
Suite de Certificación Militar del Firewall Perimetral Booleano (0416/0426)
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)

Verifica rigurosamente:
1. Compuerta Booleana Inmutable IS_MOVILNET_SUBSCRIBER (True solo para 0416 y 0426).
2. Segmentación determinista hacia CORE_MOVILNET_AUTOGESTION vs NO_USUARIOS_MOVILNET.
3. Clasificación de todas las operadoras (Movilnet, Movistar, Digitel, CANTV, VoIP, Roaming Internacional).
4. Integridad del modelo de dominio en PhoneDescriptor, CarrierClassificationResult y FastPathResolution.
5. Verificación topológica en el workflow de n8n (Edit Fields -> Edge Carrier Firewall -> Switch).
"""

import sys
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.n8n_webhook_payload_extractor import (
    N8nWebhookPayloadExtractor,
    NormalizedInboundMessage
)
from core.phone_migration_models import PhoneDescriptor, CarrierOperator
from core.carrier_funnel_classifier import CarrierFunnelClassifier, Carrier
from core.fastpath_intent_interceptor import FastPathIntentInterceptor


class TestEdgeCarrierFirewallSuite(unittest.TestCase):
    def setUp(self):
        self.extractor = N8nWebhookPayloadExtractor()
        self.fastpath = FastPathIntentInterceptor()
        self.workflow_path = PROJECT_ROOT / "api" / "n8n_workflows" / "viki_lpgtec_v2_ids_instant_dispatch.json"

    # =========================================================================
    # 1. EVALUACIÓN DIRECTA DE COMPUERTA BOOLEANA (0416 / 0426)
    # =========================================================================
    def test_carrier_firewall_boolean_movilnet_subscribers(self):
        """0416 y 0426 deben ser estrictamente IS_MOVILNET_SUBSCRIBER = True."""
        cases = [
            ("04161234567", "0416"),
            ("04269876543", "0426"),
            ("04160000001", "0416"),
            ("04261112233", "0426")
        ]
        for phone, expected_prefix in cases:
            with self.subTest(phone=phone):
                is_mov, prefix, pipeline, carrier, label = self.extractor.evaluate_carrier_firewall(phone)
                self.assertTrue(is_mov, f"Fallo: {phone} debió ser IS_MOVILNET_SUBSCRIBER = True")
                self.assertEqual(prefix, expected_prefix)
                self.assertEqual(pipeline, "CORE_MOVILNET_AUTOGESTION")
                self.assertEqual(carrier, "MOVILNET")
                self.assertEqual(label, "Movilnet 4GMAX")

    def test_carrier_firewall_boolean_non_movilnet_numbers(self):
        """Cualquier otro prefijo debe ser estrictamente IS_MOVILNET_SUBSCRIBER = False."""
        cases = [
            ("04142554590", "0414", "NO_USUARIOS_MOVILNET", "MOVISTAR", "Movistar Venezuela"),
            ("04241234567", "0424", "NO_USUARIOS_MOVILNET", "MOVISTAR", "Movistar Venezuela"),
            ("04129998877", "0412", "NO_USUARIOS_MOVILNET", "DIGITEL", "Digitel 4G"),
            ("02125551234", "0212", "NO_USUARIOS_MOVILNET", "CANTV_FIJO", "Telefonía Fija CANTV"),
            ("05001234567", "0500", "NO_USUARIOS_MOVILNET", "VOIP_SPECIAL", "Servicio Especial No Geográfico"),
            ("08006684563", "0800", "NO_USUARIOS_MOVILNET", "VOIP_SPECIAL", "Servicio Especial No Geográfico"),
            ("+13051234567", "+130", "NO_USUARIOS_MOVILNET", "INTERNACIONAL_ROAMING", "Línea Internacional / Externa"),
        ]
        for phone, expected_prefix, exp_pipeline, exp_carrier, exp_label in cases:
            with self.subTest(phone=phone):
                is_mov, prefix, pipeline, carrier, label = self.extractor.evaluate_carrier_firewall(phone)
                self.assertFalse(is_mov, f"Fallo: {phone} NO debió ser marcado como Movilnet")
                self.assertEqual(pipeline, exp_pipeline)
                self.assertEqual(carrier, exp_carrier)
                self.assertEqual(label, exp_label)

    # =========================================================================
    # 2. DOMINIO PURO: PhoneDescriptor & CarrierClassificationResult
    # =========================================================================
    def test_phone_descriptor_is_movilnet_subscriber_property(self):
        pd_movilnet = PhoneDescriptor.from_string("04161234567")
        self.assertTrue(pd_movilnet.is_movilnet_subscriber)
        self.assertEqual(pd_movilnet.carrier, CarrierOperator.MOVILNET)

        pd_movistar = PhoneDescriptor.from_string("04142554590")
        self.assertFalse(pd_movistar.is_movilnet_subscriber)
        self.assertEqual(pd_movistar.carrier, CarrierOperator.MOVISTAR)

        pd_digitel = PhoneDescriptor.from_string("04125556677")
        self.assertFalse(pd_digitel.is_movilnet_subscriber)
        self.assertEqual(pd_digitel.carrier, CarrierOperator.DIGITEL)

    def test_carrier_classification_result_property(self):
        res_mov = CarrierFunnelClassifier.classify("04160000001")
        self.assertTrue(res_mov.is_movilnet_subscriber)
        self.assertFalse(res_mov.is_competitor)

        res_comp = CarrierFunnelClassifier.classify("04142554590")
        self.assertFalse(res_comp.is_movilnet_subscriber)
        self.assertTrue(res_comp.is_competitor)
        self.assertIn("is_movilnet_subscriber", res_comp.to_dict())
        self.assertFalse(res_comp.to_dict()["is_movilnet_subscriber"])

    # =========================================================================
    # 3. INTERCEPTOR FASTPATH INTEGRATION CON EL FIREWALL
    # =========================================================================
    def test_fastpath_resolution_includes_firewall_metadata(self):
        # 1. Movilnet saldo
        res_saldo = self.fastpath.intercept("cuanto debo", "04161234567")
        self.assertTrue(res_saldo.is_movilnet_subscriber)
        self.assertEqual(res_saldo.authorized_pipeline, "CORE_MOVILNET_AUTOGESTION")

        # 2. Competencia saldo (debe ofrecer portabilidad sin tocar OCS)
        res_saldo_ext = self.fastpath.intercept("cuanto debo", "04142554590")
        self.assertFalse(res_saldo_ext.is_movilnet_subscriber)
        self.assertEqual(res_saldo_ext.authorized_pipeline, "NO_USUARIOS_MOVILNET")
        self.assertIn("Movistar", res_saldo_ext.response_text)
        self.assertIn("exclusivamente para líneas **Movilnet 4GMAX", res_saldo_ext.response_text)

    # =========================================================================
    # 4. VERIFICACIÓN TOPOLÓGICA DEL WORKFLOW N8N
    # =========================================================================
    def test_n8n_workflow_contains_edge_carrier_firewall_node(self):
        """Verifica que el JSON local contenga el nodo y sus conexiones requeridas."""
        self.assertTrue(self.workflow_path.exists(), f"No se encontró {self.workflow_path}")
        with open(self.workflow_path, "r", encoding="utf-8") as f:
            wf = json.load(f)

        node_names = [n.get("name") for n in wf.get("nodes", [])]
        self.assertIn(
            "Edge Carrier Firewall (0416/0426)",
            node_names,
            "Fallo: El nodo 'Edge Carrier Firewall (0416/0426)' no está presente en el workflow"
        )

        conns = wf.get("connections", {})
        # Edit Fields debe conectar a Edge Carrier Firewall
        edit_fields_targets = [t.get("node") for t in conns.get("Edit Fields", {}).get("main", [[]])[0]]
        self.assertIn(
            "Edge Carrier Firewall (0416/0426)",
            edit_fields_targets,
            "Fallo: 'Edit Fields' no conecta a 'Edge Carrier Firewall (0416/0426)'"
        )

        # Edge Carrier Firewall debe conectar a Switch
        firewall_targets = [t.get("node") for t in conns.get("Edge Carrier Firewall (0416/0426)", {}).get("main", [[]])[0]]
        self.assertIn(
            "Switch",
            firewall_targets,
            "Fallo: 'Edge Carrier Firewall (0416/0426)' no conecta a 'Switch'"
        )


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEdgeCarrierFirewallSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        print(f"\n❌ Se detectaron {len(result.failures)} fallas y {len(result.errors)} errores.")
        sys.exit(1)
    else:
        print("\n🏆 ¡Todas las pruebas del Firewall Perimetral Booleano (100% Pass) fueron aprobadas exitosamente!")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
