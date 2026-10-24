#!/usr/bin/env python3
"""
scripts/test_pure_greeting_vs_compound_query.py
===============================================
Suite de Verificación Militar y Pruebas Automatizadas (Regla del 100% Pass)
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)

Verifica rigurosamente:
1. Filtro 'Saludo Puro' vs 'Consulta Compuesta'.
2. Erradicación total de falsos positivos (Caso Francisco Landaeta y consultas abiertas).
3. Aislamiento estricto de Menús:
   - Abonados Únicos Movilnet (0416/0426): Menú de Autogestión Oficial.
   - NO Usuarios Movilnet (0414/0424/0412/otros): Módulo NO_USUARIOS_MOVILNET (Portabilidad 4GMAX).
4. Cero Secuestro Comercial Ciego: Consultas compuestas pasan libremente a IA.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.greeting_compound_classifier import (
    GreetingCompoundClassifier,
    MessageCategory,
    RoutingDestination
)
from core.fastpath_intent_interceptor import (
    FastPathIntentInterceptor,
    fastpath_interceptor
)
from core.carrier_funnel_classifier import CarrierFunnelClassifier, Carrier


class TestPureGreetingVsCompoundQuerySuite(unittest.TestCase):
    def setUp(self):
        self.interceptor = FastPathIntentInterceptor()
        self.phone_movilnet = "04161234567"
        self.phone_movilnet_alt = "04269876543"
        self.phone_competitor_movistar = "04142650088"  # Francisco Landaeta
        self.phone_competitor_digitel = "04125556677"
        # Resetear cuota de prueba Freemium para asegurar idempotencia en pruebas unitarias
        self.interceptor.reset_prospect_trial(self.phone_competitor_movistar)
        self.interceptor.reset_prospect_trial(self.phone_competitor_digitel)


    # =========================================================================
    # 1. PRUEBAS DE SALUDO PURO (PURE GREETING)
    # =========================================================================
    def test_pure_greetings_isolated(self):
        pure_cases = [
            "Hola",
            "hola",
            "HOLA",
            "Buenos días",
            "buenos dias",
            "Buenas tardes",
            "buenas noches",
            "buen dia",
            "Epa",
            "Épale",
            "epale",
            "Alo",
            "Saludos",
            "saludos cordiales",
            "Hola buenas tardes",
            "Hola buenos días equipo",
            "Epa qué tal, saludos!! 👋",
            "Hola buenas tardes amigos de Movilnet",
            "Hola, feliz día para todos",
            "Buenas tardes equipo, gracias"
        ]

        for msg in pure_cases:
            with self.subTest(msg=msg):
                res = GreetingCompoundClassifier.analyze(msg)
                self.assertTrue(
                    res.is_pure_greeting,
                    f"Fallo: '{msg}' debió clasificarse como PURE_GREETING, pero fue: {res.category}"
                )
                self.assertFalse(
                    res.is_compound,
                    f"Fallo: '{msg}' no debió marcarse como compound"
                )

    # =========================================================================
    # 2. PRUEBAS DE CONSULTAS COMPUESTAS CON SALUDO (CASO FRANCISCO LANDAETA Y MÁS)
    # =========================================================================
    def test_compound_queries_with_greetings(self):
        compound_cases = [
            ("Hola, quiero comprar una laptop, tienes alguna que me recomiendes comprar?", "Caso Landaeta laptop"),
            ("Buenos días, me ayudan a elegir una computadora para programar?", "Pregunta PC"),
            ("Buenas tardes, ¿dónde queda una oficina en Valencia?", "Pregunta de sede"),
            ("Hola me recomiendas un restaurante en Altamira?", "Recomendación restaurante"),
            ("Hola qué farmacia de turno hay en Maracay?", "Pregunta de farmacia"),
            ("Epa cómo configuro el APN de mi celular?", "Pregunta APN"),
            ("Buenas tardes, se me cayó la señal en Los Teques", "Reporte de falla técnica"),
            ("Hola, tienen dispositivos MiFi para conectar mi laptop?", "Consulta MiFi"),
            ("Buenos días, cuál es el horario de atención?", "Consulta horario"),
            ("Hola, qué precio tiene una eSIM para mi teléfono?", "Consulta precio eSIM"),
            ("Buenas noches, deseo información sobre cómo afiliarme a la banca móvil", "Banca móvil"),
            ("Hola! Tienen cobertura 5G en Barquisimeto?", "Cobertura 5G")
        ]

        for msg, desc in compound_cases:
            with self.subTest(msg=msg, desc=desc):
                res = GreetingCompoundClassifier.analyze(msg)
                self.assertFalse(
                    res.is_pure_greeting,
                    f"Falso Positivo Crítico: '{msg}' ({desc}) se clasificó erróneamente como PURE_GREETING!"
                )
                self.assertTrue(
                    res.is_compound,
                    f"Fallo: '{msg}' ({desc}) debió ser marcado como COMPOUND_QUERY"
                )

    # =========================================================================
    # 3. PRUEBAS DE ENRUTAMIENTO EN FASTPATH (CERO SECUESTRO COMERCIAL)
    # =========================================================================
    def test_no_commercial_hijacking_on_compound_laptop(self):
        msg = "Hola, quiero comprar una laptop, tienes alguna que me recomiendes comprar?"
        # Ejecutar en el interceptor con la línea de Francisco Landaeta (0414)
        fp_res = self.interceptor.intercept(msg, self.phone_competitor_movistar)

        # Invariante 1: NO debe ser interceptado por FastPath determinista
        self.assertFalse(
            fp_res.can_intercept,
            "Fallo Crítico: El mensaje de compra de laptop fue interceptado por FastPath y no llegó a IA!"
        )
        # Invariante 2: Intención clasificada como conversación libre
        self.assertEqual(
            fp_res.intent_detected,
            "CONVERSACION_LIBRE",
            "Fallo: La intención debió ser CONVERSACION_LIBRE para dar pase al agente de IA."
        )

    # =========================================================================
    # 4. AISLAMIENTO DE MENÚ SEGÚN OPERADORA (0416/0426 vs NO USUARIOS)
    # =========================================================================
    def test_menu_segmentation_movilnet_subscriber(self):
        """Abonados 0416/0426 reciben menú de autogestión con Saldo, Planes, C2P."""
        msg = "Hola"
        res_0416 = self.interceptor.intercept(msg, self.phone_movilnet)
        res_0426 = self.interceptor.intercept(msg, self.phone_movilnet_alt)

        for res, phone in [(res_0416, self.phone_movilnet), (res_0426, self.phone_movilnet_alt)]:
            self.assertTrue(res.can_intercept)
            self.assertEqual(res.data_source, "MOVILNET_SUBSCRIBER_MENU")
            self.assertIn("Menú de Autogestión", res.response_text)
            self.assertIn("Escribe **'Saldo'**", res.response_text)
            self.assertIn("carrier=movilnet", res.response_text)

    def test_menu_segmentation_no_usuarios_movilnet(self):
        """NO usuarios (0414/0412) van al módulo NO_USUARIOS_MOVILNET (Portabilidad)."""
        msg = "Hola"
        res_0414 = self.interceptor.intercept(msg, self.phone_competitor_movistar)
        res_0412 = self.interceptor.intercept(msg, self.phone_competitor_digitel)

        for res, phone in [(res_0414, self.phone_competitor_movistar), (res_0412, self.phone_competitor_digitel)]:
            self.assertTrue(res.can_intercept)
            self.assertEqual(res.data_source, "FUNNEL_MARKETING_NO_USUARIOS_MOVILNET")
            self.assertIn("Módulo de Nuevos Usuarios & Portabilidad 4GMAX", res.response_text)
            self.assertIn("Bono de Bienvenida", res.response_text)
            self.assertIn("Portabilidad", res.response_text)
            # PROHIBIDO ofrecer saldo interno de línea personal a no usuarios
            self.assertNotIn("Menú de Autogestión Oficial Movilnet", res.response_text)
            self.assertNotIn("Escribe **'Saldo'** para consultar tu balance disponible y megas", res.response_text)

    # =========================================================================
    # 5. CONSULTAS TELCO COMBINADAS CON SALUDO (DEBEN RESOLVERSE POR FASTPATH)
    # =========================================================================
    def test_greeting_plus_telco_intent(self):
        """Mensajes como 'Hola quiero saber mi saldo' deben resolver Telco FastPath."""
        res_saldo = self.interceptor.intercept("Hola, cuál es mi saldo?", self.phone_movilnet)
        self.assertTrue(res_saldo.can_intercept)
        self.assertEqual(res_saldo.intent_detected, "SALDO_CUPO")

        res_planes = self.interceptor.intercept("Buenos días, qué planes tienen?", self.phone_movilnet)
        self.assertTrue(res_planes.can_intercept)
        self.assertEqual(res_planes.intent_detected, "CATALOGO_PLANES")

        res_c2p = self.interceptor.intercept("Hola cómo recargo con pago móvil?", self.phone_movilnet)
        self.assertTrue(res_c2p.can_intercept)
        self.assertEqual(res_c2p.intent_detected, "GUIA_PAGO_C2P")

        res_eir = self.interceptor.intercept("Hola me robaron el celular bloquear imei", self.phone_movilnet)
        self.assertTrue(res_eir.can_intercept)
        self.assertEqual(res_eir.intent_detected, "EMERGENCIA_EIR")

    # =========================================================================
    # 6. CASOS DE REENCUENTRO ("Nuevamente soy yo", etc.) Y NO-MOVILNET
    # =========================================================================
    def test_reencounter_greetings_and_no_movilnet_guarantee(self):
        """Verifica 'Nuevamente soy yo' (Caso Ids 0414-2554590):
        1. Se clasifica como PURE_GREETING.
        2. Es interceptado por FastPath.
        3. Recibe data_source: FUNNEL_MARKETING_NO_USUARIOS_MOVILNET.
        4. PROHIBIDO TERMINANTEMENTE decir 'tu línea Movilnet'.
        """
        reencounter_cases = [
            "Nuevamente soy yo",
            "nuevamente soy yo",
            "Soy yo de nuevo",
            "de nuevo yo",
            "Aqui de nuevo",
            "aqui estoy",
            "otra vez yo",
            "Volvi",
            "buenas de nuevo"
        ]

        for msg in reencounter_cases:
            with self.subTest(msg=msg):
                res = GreetingCompoundClassifier.analyze(msg)
                self.assertTrue(
                    res.is_pure_greeting,
                    f"Fallo: '{msg}' debió clasificarse como PURE_GREETING, pero fue: {res.category}"
                )

        # Prueba con número real del incidente: 0414-2554590 (Movistar)
        phone_ids = "04142554590"
        res_interceptor = self.interceptor.intercept("Nuevamente soy yo", phone_ids)
        self.assertTrue(res_interceptor.can_intercept, "Fallo: 'Nuevamente soy yo' debió ser interceptado")
        self.assertEqual(res_interceptor.intent_detected, "SALUDO_BIENVENIDA")
        self.assertEqual(res_interceptor.data_source, "FUNNEL_MARKETING_NO_USUARIOS_MOVILNET")
        self.assertIn("Módulo de Nuevos Usuarios & Portabilidad 4GMAX", res_interceptor.response_text)
        self.assertIn("Movistar Venezuela", res_interceptor.response_text)
        # Regla Soberana: Jamás decir 'con tu línea Movilnet'
        self.assertNotIn("tu línea Movilnet", res_interceptor.response_text)
        self.assertNotIn("con tu línea Movilnet", res_interceptor.response_text)



def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPureGreetingVsCompoundQuerySuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        print(f"\n❌ Se detectaron {len(result.failures)} fallas y {len(result.errors)} errores.")
        sys.exit(1)
    else:
        print("\n🏆 ¡Todas las pruebas de la suite (100% Pass) fueron aprobadas exitosamente!")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
