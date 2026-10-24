#!/usr/bin/env python3
"""
tests/test_marketing_funnel.py — Pruebas Unitarias del Motor de Funnel Marketing Digital
========================================================================================
Proyecto: AI_Movilnet_300926 / Subagente MarketingFunnelAgent & CustomerCare Integration
"""

import unittest
from api.agents.agent_marketing_funnel import (
    MarketingFunnelAgent,
    OfferCategory,
    marketing_funnel_agent
)
from api.agents.agent_customer_care import (
    CustomerCareAgent,
    AgentMessage
)


class TestMarketingFunnelAgent(unittest.TestCase):
    """Pruebas del algoritmo Next-Best-Action y cierre de conversión."""

    def setUp(self):
        self.agent = MarketingFunnelAgent()
        self.care_agent = CustomerCareAgent()

    def test_01_nba_critical_data_quota_recommends_extra_data(self):
        """Si los megas son críticos (< 25% y faltan días), debe recomendar bolsa extra de datos."""
        offer = self.agent.evaluate_next_best_action(
            msisdn="04160000001",
            balance_ves=100.0,
            remaining_data_mb=350,   # Menos de 500 MB
            total_quota_mb=10240,
            days_to_cutoff=10,
            user_message="¿cuántos megas me quedan?"
        )
        self.assertEqual(offer.category, OfferCategory.DATA_UPSELL)
        self.assertIn("5GB", offer.headline)
        self.assertEqual(offer.target_action, "BUY_EXTRA_DATA")

    def test_02_nba_critical_balance_recommends_c2p_recharge(self):
        """Si el saldo en bolívares es bajo, debe recomendar Recarga C2P con Bono."""
        offer = self.agent.evaluate_next_best_action(
            msisdn="04160000001",
            balance_ves=12.5,        # Saldo bajo
            remaining_data_mb=8000,
            total_quota_mb=10240,
            days_to_cutoff=5,
            user_message="mi saldo por favor"
        )
        self.assertEqual(offer.category, OfferCategory.C2P_RECHARGE)
        self.assertIn("C2P", offer.headline)
        self.assertGreater(offer.price_ves, 0)

    def test_03_nba_home_router_intent(self):
        """Si el usuario pregunta por internet para el hogar sin cables, recomienda Módem CPE."""
        offer = self.agent.evaluate_next_best_action(
            msisdn="04160000001",
            balance_ves=150.0,
            remaining_data_mb=5000,
            total_quota_mb=10240,
            days_to_cutoff=15,
            user_message="¿cómo hago para tener wifi o internet en mi casa sin cables de cantv?"
        )
        self.assertEqual(offer.category, OfferCategory.HOME_WIRELESS)
        self.assertEqual(offer.offer_id, "OFR-HOME-ROUTER")

    def test_04_nba_plan_upgrade_intent(self):
        """Si el usuario consulta por cambiar o mejorar de plan, ofrece Inteliplan 10GB."""
        offer = self.agent.evaluate_next_best_action(
            msisdn="04160000001",
            balance_ves=200.0,
            remaining_data_mb=6000,
            total_quota_mb=10240,
            days_to_cutoff=15,
            user_message="quiero cambiar de plan por uno mejor"
        )
        self.assertEqual(offer.category, OfferCategory.PLAN_UPGRADE)
        self.assertEqual(offer.offer_id, "OFR-UPGRADE-10GB")

    def test_05_closing_pitch_generation(self):
        """Generación del gancho comercial de cierre persuasivo."""
        offer = self.agent.campaigns[0]
        pitch = self.agent.generate_closing_pitch(offer)
        self.assertIn("Oportunidad Comercial", pitch)
        self.assertIn(offer.cta_text, pitch)

    def test_06_customer_care_integration_metadata(self):
        """Verificar que CustomerCareAgent inyecta el funnel comercial en sus respuestas."""
        msg = AgentMessage(
            msisdn="04160000001",
            text="¿Qué beneficios o promociones tengo con mi línea?",
            channel="web",
            session_id="test-funnel-session-001"
        )
        resp = self.care_agent.process_message(msg)
        self.assertIsNotNone(resp.response_text)
        self.assertIn("marketing_funnel", resp.metadata)
        self.assertIn("offer_id", resp.metadata["marketing_funnel"])
        # Verificar que se proveyeron botones de acción comercial
        button_ids = [b["id"] for b in resp.interactive_options]
        self.assertTrue(any("funnel" in bid or "c2p" in bid for bid in button_ids))

    def test_07_october_campaigns_catalog_integrity(self):
        """Verifica que el catálogo de Octubre contenga exactamente 8 campañas (2 por semana)."""
        oct_camps = self.agent.get_october_campaigns()
        self.assertEqual(len(oct_camps), 8)
        for w in range(1, 5):
            week_camps = self.agent.get_campaigns_by_week(w)
            self.assertEqual(len(week_camps), 2, f"La semana {w} debe tener exactamente 2 campañas")
            scopes = {c.scope for c in week_camps}
            self.assertIn("NACIONAL", scopes)
            self.assertIn("REGIONAL", scopes)

    def test_08_october_halloween_campaign_recommendation(self):
        """Verifica la recomendación estacional de la campaña de Halloween."""
        offer = self.agent.evaluate_next_best_action(
            msisdn="04160000001",
            balance_ves=100.0,
            remaining_data_mb=5000,
            total_quota_mb=10240,
            days_to_cutoff=10,
            user_message="¿Tienen alguna promo para este fin de semana de halloween?"
        )
        self.assertEqual(offer.offer_id, "OCT-S4-NAC-HALLOWEEN-DATOS")
        self.assertIn("Halloween", offer.headline)
        self.assertEqual(offer.price_ves, 70.00)

    def test_09_october_12_octubre_soberania_recommendation(self):
        """Verifica la recomendación de la campaña del 12 de Octubre."""
        offer = self.agent.evaluate_next_best_action(
            msisdn="04160000001",
            balance_ves=100.0,
            remaining_data_mb=5000,
            total_quota_mb=10240,
            days_to_cutoff=10,
            user_message="Quiero saber la promoción de la semana patria del 12 de octubre"
        )
        self.assertEqual(offer.offer_id, "OCT-S2-NAC-12OCT-SOBERANIA")
        self.assertIn("12 de Octubre", offer.headline)
        self.assertEqual(offer.price_ves, 200.00)

    def test_10_october_regional_zulia_recommendation(self):
        """Verifica la recomendación regional de la temporada de béisbol en Zulia."""
        offer = self.agent.evaluate_next_best_action(
            msisdn="04160000001",
            balance_ves=100.0,
            remaining_data_mb=5000,
            total_quota_mb=10240,
            days_to_cutoff=10,
            user_message="Voy a ver a las Águilas del Zulia, ¿tienen promo especial?"
        )
        self.assertEqual(offer.offer_id, "OCT-S3-REG-ZULIA-OCCIDENTE")
        self.assertEqual(offer.scope, "REGIONAL")
        self.assertIn("Occidental", offer.headline)


if __name__ == "__main__":
    unittest.main()
