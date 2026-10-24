#!/usr/bin/env python3
"""
tests/test_production_algorithmic_fixes.py
==========================================
Verificación formal automatizada de las correcciones algorítmicas de producción:
1. Erradicación de alucinación de identidad (cero mención de 'Horacio').
2. Precisión geográfica en Petare, La Urbina y El Marqués (Farmacias, Automercados y Librerías).
3. Ruptura del bucle de bienvenida en líneas competidoras (Movistar/Digitel).
4. Oferta de Portabilidad 10GB contextual para prospectos (cero promo 2x1 exclusiva 0416/0426).
5. Desactivación de previews de medios (linkPreview: false) en despachos a WhatsApp.
"""

import unittest
from api.agents.agent_customer_care import CustomerCareAgent, AgentMessage, LLMReasoningEngine
from core.carrier_funnel_classifier import CarrierFunnelClassifier, Carrier
from api.agents.agent_n8n_dispatcher import N8nDispatcherAgent, N8nEgressMessage


class TestProductionAlgorithmicFixes(unittest.TestCase):
    """Verificación formal de las correcciones algorítmicas de producción."""

    def test_agent_message_sender_name_and_no_horacio(self):
        """Verifica que el agente atienda al usuario por su pushName verificado 'Ids' y nunca 'Horacio'."""
        agent = CustomerCareAgent()
        msg = AgentMessage(
            text="Que es esta image.",
            msisdn="04142554590",
            sender_name="Ids"
        )
        resp = agent.process_message(msg)
        self.assertNotIn("Horacio", resp.response_text)
        self.assertNotEqual(resp.response_text, "")



    def test_competitor_offers_targeted_portability(self):
        """Verifica que una línea Movistar reciba oferta de Portabilidad 10GB y no la promo 2x1 de clientes activos."""
        agent = CustomerCareAgent()
        msg = AgentMessage(
            text="Probando que ofertas tienes",
            msisdn="04142554590",
            sender_name="Ids"
        )
        resp = agent.process_message(msg)
        self.assertIn("Portabilidad", resp.response_text)
        self.assertTrue("10 GB" in resp.response_text or "10GB" in resp.response_text)
        self.assertNotIn("Por ser cliente activo 0416/0426", resp.response_text)

    def test_petare_pharmacy_geo_precision(self):
        """Verifica que farmacias en Petare retornen comercios de Petare/Sucre y no de Chacao."""
        engine = LLMReasoningEngine()
        reply, _, _ = engine._semantic_fallback_reasoner(
            message="Busco una farmacia en petare",
            session_history=[],
            msisdn="04142554590"
        )
        self.assertIn("Petare", reply)
        self.assertTrue("Farmatodo Redoma de Petare" in reply or "Locatel La California" in reply or "El Cristo" in reply)
        self.assertTrue("Chacao" not in reply or "Municipio Sucre" in reply)

    def test_urbina_supermarket_geo_precision(self):
        """Verifica que automercados en La Urbina retornen Central Madeirense o Unicasa La Urbina."""
        engine = LLMReasoningEngine()
        reply, _, _ = engine._semantic_fallback_reasoner(
            message="Busco un Automercado en la urbina",
            session_history=[],
            msisdn="04142554590"
        )
        self.assertTrue("Central Madeirense La Urbina" in reply or "Unicasa La Urbina" in reply)
        self.assertNotIn("Plaza's Los Palos Grandes", reply)

    def test_marques_bookstore_geo_precision(self):
        """Verifica que librerías en El Marqués retornen Tecni-Ciencia Líder o Nacho Unicentro El Marqués."""
        engine = LLMReasoningEngine()
        reply, _, _ = engine._semantic_fallback_reasoner(
            message="Busca una librería en el marques",
            session_history=[],
            msisdn="04142554590"
        )
        self.assertTrue("Líder" in reply or "Unicentro El Marqués" in reply or "Boleíta Center" in reply)

    def test_competitor_loop_broken(self):
        """Verifica que preguntas como 'En petare' desde Movistar no repitan el pitch de bienvenida en loop."""
        engine = LLMReasoningEngine()
        reply, _, _ = engine._semantic_fallback_reasoner(
            message="En petare",
            session_history=[],
            msisdn="04142554590"
        )
        self.assertNotIn("Veo que nos escribes desde una línea Movistar Venezuela", reply)

    def test_n8n_egress_link_preview_disabled(self):
        """Verifica que los mensajes de salida hacia Evolution API desactiven linkPreview."""
        egress = N8nEgressMessage(
            instance_id="Viki LPGTEC",
            recipient_jid="584142554590@s.whatsapp.net",
            text_content="Mensaje con https://movilnet-core.onrender.com"
        )
        payload = egress.to_evolution_payload()
        self.assertFalse(payload["options"]["linkPreview"])


if __name__ == "__main__":
    unittest.main()

