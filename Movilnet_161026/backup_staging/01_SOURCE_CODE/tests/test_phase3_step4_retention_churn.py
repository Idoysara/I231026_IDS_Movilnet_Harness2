#!/usr/bin/env python3
"""
test_phase3_step4_retention_churn.py — Batería de Pruebas Automatizadas: Fase 3, Paso 4
====================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Hito: Fase 3 — Paso 4: Agente Nivel 4 (Retención Proactiva, Fidelización & Churn ML)
Estándares: TM Forum ODA (TMF680 Customer Recommendation / Churn Retention,
            TMF629 Customer Management, TMF677 Customer Bill Management)
"""

import os
import sys
import json
import time
import uuid
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.repository import MovilnetRepository
from api.service import MovilnetAPIService
from api.agents.agent_customer_care import CustomerCareAgent, IntentType
from api.agents.agent_retention_churn import (
    RetentionChurnAgent,
    ChurnRiskSegment,
    RetentionOfferType,
    SubscriberChurnFeatures,
    ChurnPredictionResult,
    RetentionOffer,
    RetentionOfferResponse,
    get_retention_churn_agent
)


class TestPhase3Step4RetentionChurn(unittest.TestCase):
    """Suite de validación formal para el Agente Nivel 4 (RetentionChurnAgent)."""

    @classmethod
    def setUpClass(cls):
        cls.repo = MovilnetRepository()
        cls.service = MovilnetAPIService(repository=cls.repo)
        cls.agent = cls.service.retention_churn_agent

        # Crear número de prueba exclusivo
        cls.test_msisdn = f"0416{uuid.uuid4().int % 10000000:07d}"
        cls.test_cid = f"V-{uuid.uuid4().int % 100000000:08d}"

        cls.repo.create_subscriber_with_line(
            cid=cls.test_cid,
            msisdn=cls.test_msisdn,
            plan_id="PLAN_10GB_4GMAX",
            balance_ves=250.0,
            quota_mb=10240
        )

    def test_01_churn_predictor_low_risk(self):
        """Valida que un abonado con perfil fidelizado y sin quejas obtenga LOW_RISK (< 0.30)."""
        f = SubscriberChurnFeatures(
            antiquity_months=36.0,
            days_without_recharge=2,
            avg_monthly_recharge_ves=850.0,
            data_usage_trend_pct=15.0,
            complaints_count_30d=0,
            has_4gmax_device=1
        )
        res = self.agent.predict_churn(self.test_msisdn, features=f)
        self.assertIsInstance(res, ChurnPredictionResult)
        self.assertEqual(res.risk_segment, ChurnRiskSegment.LOW)
        self.assertLess(res.churn_probability, 0.30)
        self.assertLess(res.churn_score_pct, 30.0)
        self.assertGreater(len(res.top_contributing_factors), 0)

    def test_02_churn_predictor_critical_risk(self):
        """Valida que un abonado con prolongada inactividad, quejas y caída de consumo obtenga CRITICAL_RISK (>= 0.80)."""
        f = SubscriberChurnFeatures(
            antiquity_months=2.0,
            days_without_recharge=60,
            avg_monthly_recharge_ves=100.0,
            data_usage_trend_pct=-80.0,
            complaints_count_30d=4,
            has_4gmax_device=0,
            failed_transactions_count=3
        )
        res = self.agent.predict_churn(self.test_msisdn, features=f)
        self.assertEqual(res.risk_segment, ChurnRiskSegment.CRITICAL)
        self.assertGreaterEqual(res.churn_probability, 0.80)
        self.assertGreaterEqual(res.churn_score_pct, 80.0)

    def test_03_churn_predictor_medium_and_high_risk(self):
        """Valida segmentación precisa en zonas intermedias MEDIUM_RISK y HIGH_RISK."""
        # Medium Risk
        f_med = SubscriberChurnFeatures(
            antiquity_months=12.0,
            days_without_recharge=18,
            avg_monthly_recharge_ves=350.0,
            data_usage_trend_pct=-15.0,
            complaints_count_30d=1,
            has_4gmax_device=1
        )
        res_med = self.agent.predict_churn(self.test_msisdn, features=f_med)
        self.assertIn(res_med.risk_segment, [ChurnRiskSegment.MEDIUM, ChurnRiskSegment.HIGH])

        # High Risk
        f_high = SubscriberChurnFeatures(
            antiquity_months=6.0,
            days_without_recharge=35,
            avg_monthly_recharge_ves=200.0,
            data_usage_trend_pct=-55.0,
            complaints_count_30d=2,
            has_4gmax_device=1
        )
        res_high = self.agent.predict_churn(self.test_msisdn, features=f_high)
        self.assertIn(res_high.risk_segment, [ChurnRiskSegment.HIGH, ChurnRiskSegment.CRITICAL])

    def test_04_churn_explainability_factors(self):
        """Verifica la generación de factores explicativos estructurados para el agente."""
        f = SubscriberChurnFeatures(
            days_without_recharge=45,
            data_usage_trend_pct=-65.0,
            complaints_count_30d=3
        )
        res = self.agent.predict_churn(self.test_msisdn, features=f)
        factors = res.top_contributing_factors
        self.assertGreaterEqual(len(factors), 2)
        factor_names = [fac["factor"] for fac in factors]
        self.assertTrue(any("RECLAMO" in fn or "INACTIVIDAD" in fn or "DATOS" in fn for fn in factor_names))
        for fac in factors:
            self.assertIn("severity", fac)
            self.assertIn("detail", fac)

    def test_05_analytical_fallback_consistency(self):
        """Comprueba que el modelo analítico de contingencia produce predicciones coherentes."""
        predictor = self.agent.predictor
        f = SubscriberChurnFeatures(antiquity_months=24.0, days_without_recharge=3, complaints_count_30d=0)
        prob_fallback = predictor._analytical_predict(f)
        self.assertIsInstance(prob_fallback, float)
        self.assertLess(prob_fallback, 0.50)

    def test_06_nba_offer_selection_critical(self):
        """Verifica que el motor NBA asigne el paquete de Rescate VIP ante riesgo CRITICAL."""
        f = SubscriberChurnFeatures(days_without_recharge=50, complaints_count_30d=3)
        resp = self.agent.generate_retention_offer(self.test_msisdn, features=f)
        self.assertEqual(resp.churn_prediction.risk_segment, ChurnRiskSegment.CRITICAL)
        self.assertEqual(resp.selected_offer.discount_pct, 50.0)
        self.assertGreaterEqual(resp.selected_offer.bonus_data_gb, 15.0)
        self.assertIn("RESCATE", resp.selected_offer.coupon_code)

    def test_07_nba_offer_selection_high_and_medium(self):
        """Verifica la correcta asignación de ofertas para HIGH_RISK y MEDIUM_RISK."""
        # High Risk
        f_high = SubscriberChurnFeatures(days_without_recharge=35, data_usage_trend_pct=-50.0, complaints_count_30d=1)
        resp_high = self.agent.generate_retention_offer(self.test_msisdn, features=f_high)
        self.assertIn(resp_high.churn_prediction.risk_segment, [ChurnRiskSegment.HIGH, ChurnRiskSegment.CRITICAL])
        self.assertGreaterEqual(resp_high.selected_offer.discount_pct, 30.0)

        # Medium Risk
        f_med = SubscriberChurnFeatures(days_without_recharge=16, data_usage_trend_pct=-10.0, complaints_count_30d=1)
        resp_med = self.agent.generate_retention_offer(self.test_msisdn, features=f_med)
        self.assertIn(resp_med.churn_prediction.risk_segment, [ChurnRiskSegment.MEDIUM, ChurnRiskSegment.HIGH])
        self.assertGreaterEqual(resp_med.selected_offer.bonus_data_gb, 5.0)

    def test_08_nba_offer_selection_low_risk(self):
        """Verifica que un abonado de bajo riesgo reciba bono de agradecimiento (+2 GB)."""
        f = SubscriberChurnFeatures(antiquity_months=48.0, days_without_recharge=1, complaints_count_30d=0)
        resp = self.agent.generate_retention_offer(self.test_msisdn, features=f)
        self.assertEqual(resp.churn_prediction.risk_segment, ChurnRiskSegment.LOW)
        self.assertEqual(resp.selected_offer.bonus_data_gb, 2.0)
        self.assertIn("GRACIAS", resp.selected_offer.coupon_code)

    def test_09_omnichannel_message_formatting(self):
        """Valida que el mensaje generado contenga formato Markdown, emojis y botones CTA interactivos."""
        f = SubscriberChurnFeatures(days_without_recharge=40, complaints_count_30d=2)
        resp = self.agent.generate_retention_offer(self.test_msisdn, channel="whatsapp", features=f)
        msg = resp.personalized_message
        self.assertIn(self.test_msisdn, msg)
        self.assertIn("TELECOMUNICACIONES MOVILNET", msg)
        self.assertIn(resp.selected_offer.coupon_code, msg)
        self.assertGreaterEqual(len(resp.interactive_buttons), 2)
        self.assertIn("btn_accept_retention_offer", [b["id"] for b in resp.interactive_buttons])

    def test_10_coupon_generation_and_validation(self):
        """Prueba el ciclo de vida del cupón de retención (creación, validación, rechazo a terceros y canje)."""
        resp = self.agent.generate_retention_offer(self.test_msisdn)
        coupon = resp.selected_offer.coupon_code

        # 1. Validación exitosa para el abonado titular
        val_ok = self.agent.validate_retention_coupon(coupon, self.test_msisdn)
        self.assertTrue(val_ok["valid"])
        self.assertEqual(val_ok["coupon_code"], coupon)

        # 2. Rechazo para otro número no autorizado
        other_phone = "04269990011"
        val_err = self.agent.validate_retention_coupon(coupon, other_phone)
        self.assertFalse(val_err["valid"])
        self.assertEqual(val_err["reason"], "CUPON_NO_CORRESPONDE_A_ESTA_LINEA")

        # 3. Canje del cupón
        redeemed = self.agent.redeem_retention_coupon(coupon, self.test_msisdn)
        self.assertTrue(redeemed)

        # 4. Intento de re-canje (doble gasto)
        val_double = self.agent.validate_retention_coupon(coupon, self.test_msisdn)
        self.assertFalse(val_double["valid"])
        self.assertEqual(val_double["reason"], "CUPON_YA_CANJEADO")

    def test_11_persistence_in_churn_metrics_table(self):
        """Verifica que la evaluación de churn quede persistida de forma inmutable en SQLite WAL."""
        resp = self.agent.generate_retention_offer(self.test_msisdn)
        self.assertIsNotNone(resp.persisted_evaluation_id)

        latest = self.repo.get_latest_churn_metric(self.test_msisdn)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["id"], resp.persisted_evaluation_id)
        self.assertEqual(latest["msisdn"], self.test_msisdn)
        self.assertEqual(latest["coupon_code_offered"], resp.selected_offer.coupon_code)

    def test_12_swarm_handoff_from_customer_care(self):
        """Valida que el Agente Nivel 4 atienda un handoff de insatisfacción desde el Agente N1."""
        payload = {
            "msisdn": self.test_msisdn,
            "intent": "HANDOFF_RETENTION_CHURN",
            "reason": "Abonado manifiesta deseo de portarse a otra operadora",
            "complaints": 3,
            "data_trend": -60.0
        }
        res = self.agent.handle_swarm_handoff("agent_customer_care", payload)
        self.assertIsInstance(res, RetentionOfferResponse)
        self.assertIn(res.churn_prediction.risk_segment, [ChurnRiskSegment.CRITICAL, ChurnRiskSegment.HIGH])
        self.assertIn("RESCATE", res.selected_offer.coupon_code)

    def test_13_swarm_handoff_from_emergency_eir(self):
        """Valida que el Agente Nivel 4 atienda un handoff post-bloqueo desde el Agente N3."""
        payload = {
            "msisdn": self.test_msisdn,
            "reason": "Terminal bloqueado por hurto en EIR",
            "imei": "358240051111110"
        }
        res = self.agent.handle_swarm_handoff("agent_emergency_eir", payload)
        self.assertIsInstance(res, RetentionOfferResponse)
        self.assertGreaterEqual(res.selected_offer.bonus_data_gb, 10.0)

    def test_14_rest_api_predict_and_offer_endpoints(self):
        """Valida despacho HTTP REST API para /predict y /offer."""
        # 1. Endpoint predict
        body_predict = json.dumps({
            "msisdn": self.test_msisdn,
            "complaints_count_30d": 2,
            "days_without_recharge": 30
        }).encode("utf-8")
        st1, _, b1 = self.service.dispatch("POST", "/api/v1/agents/retention-churn/predict", {}, body_predict)
        self.assertEqual(st1, 200)
        data1 = json.loads(b1.decode("utf-8"))
        self.assertEqual(data1["msisdn"], self.test_msisdn)
        self.assertIn("churn_probability", data1)
        self.assertIn("risk_segment", data1)

        # 2. Endpoint offer
        body_offer = json.dumps({
            "msisdn": self.test_msisdn,
            "channel": "telegram"
        }).encode("utf-8")
        st2, _, b2 = self.service.dispatch("POST", "/api/v1/agents/retention-churn/offer", {}, body_offer)
        self.assertEqual(st2, 200)
        data2 = json.loads(b2.decode("utf-8"))
        self.assertEqual(data2["status"], "OFFER_GENERATED")
        self.assertIn("selected_offer", data2)
        self.assertIn("coupon_code", data2["selected_offer"])

    def test_15_rest_api_status_endpoint(self):
        """Valida despacho HTTP REST API para /status (GET)."""
        st, _, b = self.service.dispatch("GET", f"/api/v1/agents/retention-churn/status?msisdn={self.test_msisdn}", {}, b"")
        self.assertEqual(st, 200)
        data = json.loads(b.decode("utf-8"))
        self.assertTrue(data["has_evaluations"])
        self.assertEqual(data["msisdn"], self.test_msisdn)
        self.assertGreaterEqual(data["history_evaluations_count"], 1)

    def test_16_performance_and_latency_sla_benchmarks(self):
        """Valida que la inferencia ML y selección NBA cumplan el SLA Carrier-Grade (< 20 ms)."""
        f = SubscriberChurnFeatures(antiquity_months=14.0, days_without_recharge=10, complaints_count_30d=1)

        # Warmup de 2 iteraciones
        for _ in range(2):
            self.agent.predict_churn(self.test_msisdn, features=f)

        # Benchmark de 20 ejecuciones
        latencies = []
        for _ in range(20):
            t0 = time.time()
            res = self.agent.predict_churn(self.test_msisdn, features=f)
            latencies.append((time.time() - t0) * 1000.0)

        avg_lat = sum(latencies) / len(latencies)
        p95_lat = sorted(latencies)[int(len(latencies) * 0.95)]
        min_lat = min(latencies)

        print(f"\n   ⚡ Latencia Agente N4 (Churn ML): Promedio={avg_lat:.3f}ms | P95={p95_lat:.3f}ms | Min={min_lat:.3f}ms")

        # SLAs Carrier-Grade
        self.assertLess(avg_lat, 20.0, f"SLA de latencia promedio (< 20ms) superado: {avg_lat:.2f}ms")
        self.assertLess(p95_lat, 30.0, f"SLA de latencia P95 (< 30ms) superado: {p95_lat:.2f}ms")


if __name__ == "__main__":
    unittest.main()
