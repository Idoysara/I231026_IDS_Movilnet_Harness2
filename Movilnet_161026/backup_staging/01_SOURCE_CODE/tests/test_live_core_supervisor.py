#!/usr/bin/env python3
"""
tests/test_live_core_supervisor.py — Suite de Pruebas para el Supervisor Online de Core Movilnet
================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal
"""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.live_core_supervisor import LiveCoreSupervisor, SupervisedInteraction, SupervisorDashboardStatus


class TestLiveCoreSupervisor(unittest.TestCase):
    """Pruebas unitarias para evaluación de latencias, coherencia semántica y SLAs."""

    def setUp(self):
        self.supervisor = LiveCoreSupervisor()

    def test_01_evaluate_sla_latency(self):
        """Valida umbrales de latencia Carrier-Grade."""
        self.assertEqual(self.supervisor.evaluate_sla_latency(1.5), "OPTIMO")
        self.assertEqual(self.supervisor.evaluate_sla_latency(3.5), "OPTIMO")
        self.assertEqual(self.supervisor.evaluate_sla_latency(5.2), "ACEPTABLE")
        self.assertEqual(self.supervisor.evaluate_sla_latency(6.0), "ACEPTABLE")
        self.assertEqual(self.supervisor.evaluate_sla_latency(6.1), "DEMORADO")
        self.assertEqual(self.supervisor.evaluate_sla_latency(15.0), "DEMORADO")

    def test_02_evaluate_response_coherence_positive(self):
        """Valida que respuestas válidas y pertinentes sean clasificadas como coherentes."""
        is_coh, score, act = self.supervisor.evaluate_response_coherence(
            "Cuál es la tasa de cambio",
            "La tasa oficial BCV del día es Bs. 48.20 por USD."
        )
        self.assertTrue(is_coh)
        self.assertEqual(score, 1.0)
        self.assertTrue(act)

    def test_03_evaluate_response_coherence_negative(self):
        """Valida que respuestas vacías o con errores técnicos sean rechazadas."""
        is_coh, score, act = self.supervisor.evaluate_response_coherence("Hola", "")
        self.assertFalse(is_coh)
        self.assertEqual(score, 0.0)

        is_coh_err, score_err, _ = self.supervisor.evaluate_response_coherence("Hola", "Error 503 Service Unavailable")
        self.assertFalse(is_coh_err)
        self.assertLess(score_err, 0.5)

    def test_04_audit_trace_item_multicarrier(self):
        """Valida la clasificación de operadoras móviles en la traza."""
        sample_movistar = {
            "execution_id": "9745",
            "user_phone": "0414-2554590",
            "user_message": "Consulta de saldo",
            "bot_reply": "Tu saldo es Bs. 15.00",
            "total_duration_sec": 2.1
        }
        res = self.supervisor.audit_trace_item(sample_movistar)
        self.assertEqual(res.carrier_name, "MOVISTAR")
        self.assertEqual(res.sla_status, "OPTIMO")
        self.assertTrue(res.is_coherent)

        sample_movilnet = {
            "execution_id": "9746",
            "user_phone": "0416-6251587",
            "user_message": "Recarga C2P",
            "bot_reply": "Para recargar ingresa tu cédula",
            "total_duration_sec": 4.2
        }
        res_mov = self.supervisor.audit_trace_item(sample_movilnet)
        self.assertEqual(res_mov.carrier_name, "MOVILNET")
        self.assertEqual(res_mov.sla_status, "ACEPTABLE")

    def test_05_dashboard_status_and_sha256(self):
        """Valida generación de métricas y sellado SHA-256."""
        inter = SupervisedInteraction(
            interaction_id="INT-TEST-001",
            execution_id="9999",
            timestamp_utc="2026-10-09T10:00:00Z",
            sender_phone="0424-1533712",
            sender_name="Ids",
            carrier_name="MOVISTAR",
            message_text="Primero",
            bot_response="Adelante",
            latency_sec=2.35,
            sla_status="OPTIMO",
            is_action_executed=True,
            is_coherent=True,
            quality_score=1.0,
            delivery_status="DELIVERY_ACK"
        )
        self.supervisor.interactions_history.append(inter)
        status = self.supervisor.generate_dashboard_status()

        self.assertEqual(status.total_interactions_audited, 1)
        self.assertEqual(status.sla_compliance_rate, 100.0)
        self.assertEqual(status.avg_latency_sec, 2.35)
        self.assertEqual(status.carrier_distribution.get("MOVISTAR"), 1)
        self.assertEqual(len(status.sha256_seal), 64)


if __name__ == "__main__":
    unittest.main()
