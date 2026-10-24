#!/usr/bin/env python3
"""
api/agents/agent_marketing_funnel.py — Motor de Funnel Marketing Digital & Next-Best-Action (NBA)
================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Antigravity Nivel 5 Mobile Client & Omnichannel Funnel Engine
Alineado con: Directivas de Mercadeo, Ventas B2B2C, Operaciones Comerciales y TM Forum TMF680.

Implementa:
  1. Algoritmo Next-Best-Action (NBA) contextual según saldo, consumo de megas y fecha de corte.
  2. Catálogo de 8 Campañas Estacionales de Octubre 2026 (2 por semana, regional y nacional).
  3. Motor de selección de ofertas contextuales por región y estacionalidad.
  4. Ganchos de conversión y cierre de ventas (Call-To-Action Hooks).
  5. Generador de payloads One-Click Checkout para recargas inmediatas vía Pago Móvil C2P.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class FunnelStage(str, Enum):
    TOFU_AWARENESS = "TOFU_AWARENESS"        # Descubrimiento / Consulta pasiva
    MOFU_CONSIDERATION = "MOFU_CONSIDERATION"# Interés en planes o consumo
    BOFU_CONVERSION = "BOFU_CONVERSION"      # Decisión de compra / Recarga C2P
    LOYALTY_RETENTION = "LOYALTY_RETENTION"  # Fidelización / Cross-sell aliados


class OfferCategory(str, Enum):
    DATA_UPSELL = "DATA_UPSELL"              # Mega Adicional 4GMAX
    PLAN_UPGRADE = "PLAN_UPGRADE"            # Inteliplan 10GB / Mega Conecta 20GB
    C2P_RECHARGE = "C2P_RECHARGE"            # Recarga rápida de saldo con bonos
    HOME_WIRELESS = "HOME_WIRELESS"          # Módem Inalámbrico 4GMAX Residencial
    PARTNER_REWARD = "PARTNER_REWARD"        # Cupones aliados (Farmatodo, Cines 2x1)
    LOYALTY_RETENTION = "LOYALTY_RETENTION"  # Fidelización / Beneficios territoriales


@dataclass
class MarketingOffer:
    offer_id: str
    campaign_name: str
    category: OfferCategory
    headline: str
    description: str
    benefit_highlight: str
    price_ves: float
    price_usd: float
    cta_text: str
    target_action: str
    prefill_data: Dict[str, Any]
    scope: str = "NACIONAL"
    week: int = 1
    target_regions: Optional[List[str]] = None
    theme: Optional[str] = None
    keywords: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d


class MarketingFunnelAgent:
    """
    Subagente comercial de Funnel Marketing Digital de Telecomunicaciones Movilnet C.A.
    """

    def __init__(self):
        # 1. Catálogo Base Permanente
        self.base_campaigns: List[MarketingOffer] = [
            MarketingOffer(
                offer_id="OFR-EXTRA-2GB",
                campaign_name="Navega Sin Pausas 4GMAX",
                category=OfferCategory.DATA_UPSELL,
                headline="🚀 Bolsa Extra Datos 2GB 4GMAX",
                description="¡Que nada detenga tu navegación! Activa 2 GB adicionales para videos, redes y streaming.",
                benefit_highlight="Vigencia hasta tu fecha de corte. Activación inmediata sin pérdida de señal.",
                price_ves=45.00,
                price_usd=1.22,
                cta_text="⚡ Activar 2GB por Bs. 45,00",
                target_action="BUY_EXTRA_DATA",
                prefill_data={"package_code": "EXTRA_2GB", "amount_ves": 45.00}
            ),
            MarketingOffer(
                offer_id="OFR-EXTRA-5GB",
                campaign_name="Mega Rendimiento 4GMAX",
                category=OfferCategory.DATA_UPSELL,
                headline="🔥 Paquete Especial 5GB Extra",
                description="Duplica tu potencia con 5 GB adicionales para estudio, trabajo y ocio continuo.",
                benefit_highlight="Tarifa especial con 20% de ahorro por GB comparado a la tarifa estándar.",
                price_ves=95.00,
                price_usd=2.58,
                cta_text="⚡ Activar 5GB por Bs. 95,00",
                target_action="BUY_EXTRA_DATA",
                prefill_data={"package_code": "EXTRA_5GB", "amount_ves": 95.00}
            ),
            MarketingOffer(
                offer_id="OFR-UPGRADE-10GB",
                campaign_name="Evoluciona a 10GB 4GMAX",
                category=OfferCategory.PLAN_UPGRADE,
                headline="🌟 Actualización a Inteliplan 10GB",
                description="Sube de nivel con 10 GB de datos, 1.000 minutos libres y 500 SMS a nivel nacional.",
                benefit_highlight="El plan más cotizado de Venezuela con la mayor cobertura territorial.",
                price_ves=185.00,
                price_usd=5.02,
                cta_text="🔄 Cambiar a Inteliplan 10GB",
                target_action="PLAN_UPGRADE",
                prefill_data={"new_plan_id": "PLAN_10GB_4GMAX", "amount_ves": 185.00}
            ),
            MarketingOffer(
                offer_id="OFR-C2P-BONUS",
                campaign_name="Recarga y Gana con Pago Móvil C2P",
                category=OfferCategory.C2P_RECHARGE,
                headline="💳 Recarga C2P con Bono de Megas",
                description="Recarga tu línea hoy con BDV, Banesco o cualquier banco y recibe 1GB de cortesía.",
                benefit_highlight="Bono acreditado automáticamente en menos de 3 minutos tras confirmar el pago.",
                price_ves=150.00,
                price_usd=4.07,
                cta_text="⚡ Recargar Bs. 150 + 1GB Bono",
                target_action="C2P_RECHARGE",
                prefill_data={"amount_ves": 150.00, "bonus_gb": 1.0}
            ),
            MarketingOffer(
                offer_id="OFR-HOME-ROUTER",
                campaign_name="Hogar Conectado 4GMAX",
                category=OfferCategory.HOME_WIRELESS,
                headline="🏠 Módem WiFi 4GMAX Residencial",
                description="Internet inalámbrico para tu casa u oficina conectando hasta 32 equipos sin cables.",
                benefit_highlight="Sin instalaciones complejas de fibra. Enchufa y navega al instante.",
                price_ves=920.00,
                price_usd=24.96,
                cta_text="📦 Solicitar Módem Residencial",
                target_action="INQUIRE_HARDWARE",
                prefill_data={"device_type": "CPE_4GMAX_ROUTER", "amount_ves": 920.00}
            ),
            MarketingOffer(
                offer_id="OFR-PARTNER-CINES",
                campaign_name="Fidelización Movilnet 4GMAX",
                category=OfferCategory.PARTNER_REWARD,
                headline="🎟️ Promo Aliada 2x1 en Cines",
                description="Por ser cliente activo 0416/0426 disfruta entradas al 2x1 en cines aliados a nivel nacional.",
                benefit_highlight="Solo presenta tu número Movilnet en taquilla y disfruta tu función.",
                price_ves=0.00,
                price_usd=0.00,
                cta_text="🎁 Ver Cupón 2x1",
                target_action="SHOW_COUPON",
                prefill_data={"coupon_code": "MOVILNET-2X1-CINE"}
            )
        ]

        # 2. Catálogo Oficial de 8 Campañas de Octubre 2026 (2 por semana: Regional y Nacional)
        self.october_campaigns: List[MarketingOffer] = [
            # SEMANA 1 (01 - 07 OCT): Arranque de Mes & Clases
            MarketingOffer(
                offer_id="OCT-S1-NAC-ESTUDIANTE",
                campaign_name="Estudiante 4GMAX — Conectados al Futuro",
                category=OfferCategory.DATA_UPSELL,
                headline="📚 Bolsa Académica 3GB Extra",
                description="¡Arrancan las clases! Activa 3 GB adicionales dedicados a plataformas educativas, Zoom, Teams y Classroom.",
                benefit_highlight="Tarifa especial estudiantil con 35% de descuento.",
                price_ves=55.00,
                price_usd=1.49,
                cta_text="⚡ Activar Bolsa Estudiante 3GB por Bs. 55,00",
                target_action="BUY_EXTRA_DATA",
                prefill_data={"package_code": "ESTUDIANTE_3GB", "amount_ves": 55.00},
                scope="NACIONAL",
                week=1,
                target_regions=["Todas"],
                theme="Regreso a Clases & Universitario",
                keywords=["estudiante", "clases", "universidad", "colegio", "estudiar", "zoom", "tareas"]
            ),
            MarketingOffer(
                offer_id="OCT-S1-REG-EJECENTRAL",
                campaign_name="Eje Central 4GMAX — Conecta tu Negocio",
                category=OfferCategory.HOME_WIRELESS,
                headline="🏢 Módem WiFi 4GMAX Pyme Central",
                description="Internet inalámbrico para comercios y hogares en Caracas, Valencia y Maracay con 50GB el primer mes.",
                benefit_highlight="Sin costo de instalación física. Conecta hasta 32 terminales de cobro y teléfonos.",
                price_ves=890.00,
                price_usd=24.15,
                cta_text="📦 Solicitar Módem Pyme Central",
                target_action="INQUIRE_HARDWARE",
                prefill_data={"device_type": "CPE_PYME_CENTRAL", "amount_ves": 890.00},
                scope="REGIONAL",
                week=1,
                target_regions=["Caracas", "Distrito Capital", "Miranda", "Carabobo", "Valencia", "Aragua", "Maracay"],
                theme="Emprendedores & Comercio Industrial",
                keywords=["negocio", "comercio", "pyme", "valencia", "maracay", "caracas", "modem pyme"]
            ),

            # SEMANA 2 (08 - 15 OCT): Semana de la Resistencia Indígena (12 de Octubre)
            MarketingOffer(
                offer_id="OCT-S2-NAC-12OCT-SOBERANIA",
                campaign_name="Semana de la Resistencia Indígena — Soberanía 4GMAX",
                category=OfferCategory.C2P_RECHARGE,
                headline="🇻🇪 Recarga Patria 12 de Octubre con 2GB Bono",
                description="Celebramos la resistencia indígena: recarga desde 200 Bs por Pago Móvil C2P y recibe 2 GB de bono soberano.",
                benefit_highlight="Bono de 2 GB acreditado de inmediato en tu línea 0416/0426.",
                price_ves=200.00,
                price_usd=5.42,
                cta_text="🇻🇪 Recargar Bs. 200 + 2GB Bono Patrio",
                target_action="C2P_RECHARGE",
                prefill_data={"amount_ves": 200.00, "bonus_gb": 2.0},
                scope="NACIONAL",
                week=2,
                target_regions=["Todas"],
                theme="Semana Patria del 12 de Octubre",
                keywords=["12 octubre", "patria", "resistencia", "indigena", "soberania", "bono patrio"]
            ),
            MarketingOffer(
                offer_id="OCT-S2-REG-GUAYANA-ANCESTRAL",
                campaign_name="Ruta Ancestral Guayana — Señal en el Sur",
                category=OfferCategory.LOYALTY_RETENTION,
                headline="🌿 Beneficio Ancestral Guayana y Amazonas",
                description="Para nuestros abonados del sur del Orinoco: navegación nocturna 100% libre y minutos comunitarios ilimitados.",
                benefit_highlight="Beneficio exclusivo para líneas registradas en los estados Bolívar, Amazonas y Delta Amacuro.",
                price_ves=0.00,
                price_usd=0.00,
                cta_text="🌿 Activar Beneficio Ancestral Sur",
                target_action="SHOW_COUPON",
                prefill_data={"coupon_code": "MOVILNET-SUR-ANCESTRAL"},
                scope="REGIONAL",
                week=2,
                target_regions=["Bolívar", "Bolivar", "Amazonas", "Delta Amacuro", "Puerto Ordaz", "Ciudad Guayana"],
                theme="Cobertura y Pueblos Originarios del Sur",
                keywords=["guayana", "bolivar", "amazonas", "delta", "puerto ordaz", "sur", "ancestral"]
            ),

            # SEMANA 3 (16 - 23 OCT): Temporada LVBP 2026
            MarketingOffer(
                offer_id="OCT-S3-NAC-LVBP-PLAYBALL",
                campaign_name="¡Play Ball con Movilnet! — Arranque LVBP 2026",
                category=OfferCategory.DATA_UPSELL,
                headline="⚾ Paquete Fanático LVBP 7GB",
                description="Vive la emoción de la pelota criolla con 7 GB adicionales para streaming de audio, noticias y jugadas en vivo.",
                benefit_highlight="Válido por 15 días con navegación libre en portales deportivos oficiales.",
                price_ves=120.00,
                price_usd=3.25,
                cta_text="⚾ Activar Paquete LVBP 7GB por Bs. 120,00",
                target_action="BUY_EXTRA_DATA",
                prefill_data={"package_code": "LVBP_7GB", "amount_ves": 120.00},
                scope="NACIONAL",
                week=3,
                target_regions=["Todas"],
                theme="Apertura Béisbol Profesional Venezolano",
                keywords=["beisbol", "pelota", "lvbp", "leones", "magallanes", "tiburones", "cardenales", "aguilas", "play ball"]
            ),
            MarketingOffer(
                offer_id="OCT-S3-REG-ZULIA-OCCIDENTE",
                campaign_name="Pasión Zuliana y Falconiana — Águilas & Cobertura",
                category=OfferCategory.PLAN_UPGRADE,
                headline="🦅 Upgrade Pasión Occidental 20GB Pro",
                description="En Zulia y Falcón celebramos el inicio del béisbol: actualiza a Inteliplan 20GB Pro con 25% de descuento el primer mes.",
                benefit_highlight="Prioridad de datos en radiobases 4GMAX modernizadas del eje Maracaibo-Punto Fijo.",
                price_ves=517.50,
                price_usd=14.04,
                cta_text="🦅 Mejorar a 20GB con 25% OFF",
                target_action="PLAN_UPGRADE",
                prefill_data={"new_plan_id": "PLAN_20GB_4GMAX", "amount_ves": 517.50, "discount_pct": 25},
                scope="REGIONAL",
                week=3,
                target_regions=["Zulia", "Maracaibo", "San Francisco", "Falcón", "Falcon", "Punto Fijo", "Coro"],
                theme="Apertura Temporada Occidental Luis Aparicio",
                keywords=["zulia", "maracaibo", "falcon", "punto fijo", "aguilas del zulia", "occidente"]
            ),

            # SEMANA 4 (24 - 31 OCT): Halloween & Cierre de Mes
            MarketingOffer(
                offer_id="OCT-S4-NAC-HALLOWEEN-DATOS",
                campaign_name="Halloween 4GMAX — Noches de Terror y Datos Sin Miedo",
                category=OfferCategory.DATA_UPSELL,
                headline="🎃 Halloween Pase Nocturno 'Sin Miedo' 15GB",
                description="Maratones de películas de terror y videojuegos toda la noche (10:00 PM a 6:00 AM) con 15 GB ultrarrápidos.",
                benefit_highlight="Sin consumir tu cupo principal. Solo durante el fin de semana de Halloween.",
                price_ves=70.00,
                price_usd=1.89,
                cta_text="🎃 Activar Pase Nocturno 15GB por Bs. 70,00",
                target_action="BUY_EXTRA_DATA",
                prefill_data={"package_code": "NOCTURNO_HALLOWEEN_15GB", "amount_ves": 70.00},
                scope="NACIONAL",
                week=4,
                target_regions=["Todas"],
                theme="Temporada de Halloween y Fin de Mes",
                keywords=["halloween", "terror", "miedo", "noche", "maraton", "pelicula", "gamer"]
            ),
            MarketingOffer(
                offer_id="OCT-S4-REG-ANDES-PARAMO",
                campaign_name="Ruta de los Páramos — Cierre de Mes en la Cumbre",
                category=OfferCategory.C2P_RECHARGE,
                headline="🏔️ Recarga Andina con 1.5GB Extra de Altura",
                description="En los Andes venezolanos recarga desde 100 Bs por C2P y te regalamos 1.5 GB para compartir fotos y videos desde las alturas.",
                benefit_highlight="Mayor cobertura 4GMAX en la cordillera andina para residentes y turistas.",
                price_ves=100.00,
                price_usd=2.71,
                cta_text="🏔️ Recargar con Bono Andino 1.5GB",
                target_action="C2P_RECHARGE",
                prefill_data={"amount_ves": 100.00, "bonus_gb": 1.5},
                scope="REGIONAL",
                week=4,
                target_regions=["Mérida", "Merida", "Táchira", "Tachira", "San Cristobal", "Trujillo"],
                theme="Turismo Andino y Fin de Mes de Altura",
                keywords=["merida", "tachira", "trujillo", "andes", "paramo", "san cristobal", "montaña"]
            )
        ]

        # Consolidar todas las campañas
        self.campaigns: List[MarketingOffer] = self.base_campaigns + self.october_campaigns

    def get_october_campaigns(self) -> List[MarketingOffer]:
        """Retorna el catálogo completo de las 8 campañas de Octubre 2026."""
        return self.october_campaigns

    def get_campaigns_by_week(self, week: int) -> List[MarketingOffer]:
        """Filtra las campañas correspondientes a una semana específica de Octubre (1 a 4)."""
        return [c for c in self.october_campaigns if c.week == week]

    def evaluate_next_best_action(
        self,
        msisdn: str,
        balance_ves: float,
        remaining_data_mb: int,
        total_quota_mb: int,
        days_to_cutoff: int,
        user_message: str = "",
        state_or_region: str = ""
    ) -> MarketingOffer:
        """
        Calcula la Acción Comercial Óptima (Next-Best-Action - NBA) analizando las
        variables OCS de la línea, la estacionalidad de Octubre y la intencionalidad del mensaje.
        """
        msg = user_message.lower()
        clean_region = state_or_region.strip().lower()

        # 0. Intercepción Estacional Prioritaria (Mes de Octubre 2026)
        # Búsqueda por palabras clave temáticas de las campañas de Octubre
        for camp in self.october_campaigns:
            if camp.keywords:
                for kw in camp.keywords:
                    if kw in msg:
                        return camp

        # 0.1 Búsqueda Regional Específica si se menciona una región asociada
        if clean_region:
            for camp in self.october_campaigns:
                if camp.scope == "REGIONAL" and camp.target_regions:
                    for reg in camp.target_regions:
                        if reg.lower() in clean_region or clean_region in reg.lower():
                            if any(k in msg for k in ["promocion", "promo", "oferta", "beneficio", "plan", "recarga"]):
                                return camp

        # 1. Intención explícita sobre internet de casa / oficina
        if any(k in msg for k in ["internet en casa", "wifi casa", "modem", "sin cables", "residencial", "oficina"]):
            return self._find_offer("OFR-HOME-ROUTER")

        # 2. Intención explícita de cambiar de plan o comprar megas
        if any(k in msg for k in ["cambiar de plan", "mejor plan", "plan mas grande", "upgrade"]):
            return self._find_offer("OFR-UPGRADE-10GB")

        # 3. Saldo Crítico para renovación de plan (Saldo < Bs. 25.0)
        if balance_ves < 25.0:
            return self._find_offer("OFR-C2P-BONUS")

        # 4. Diagnóstico de Megas Críticos (< 25% disponible con > 3 días para corte)
        quota = max(1, total_quota_mb)
        pct_remaining = (remaining_data_mb / quota) * 100.0

        # Si el abonado tiene abundantes megas (> 50% o más de 10 GB acumulados), ofrecer fidelización
        if remaining_data_mb > 10240 or pct_remaining > 50.0:
            return self._find_offer("OFR-PARTNER-CINES")

        if pct_remaining < 25.0 and days_to_cutoff >= 3:
            # Recomendar bolsa de megas según urgencia
            if remaining_data_mb < 500:
                return self._find_offer("OFR-EXTRA-5GB")
            return self._find_offer("OFR-EXTRA-2GB")

        # 5. Si tiene suficiente saldo y megas, incentivar beneficios o fidelización
        if any(k in msg for k in ["cine", "descuento", "beneficio", "promocion", "aliado"]):
            return self._find_offer("OFR-PARTNER-CINES")

        # 6. Default estratégico: Fomentar beneficios de fidelización
        return self._find_offer("OFR-PARTNER-CINES")

    def generate_closing_pitch(self, offer: MarketingOffer) -> str:
        """
        Genera el gancho persuasivo de cierre de embudo (Closing Hook)
        diseñado para anexarse a las respuestas conversacionales.
        """
        scope_badge = f" [{offer.scope}]" if hasattr(offer, "scope") and offer.scope == "REGIONAL" else ""
        return (
            f"\n\n💡 *Oportunidad Comercial para tu Línea — {offer.headline}{scope_badge}*\n"
            f"{offer.description} {offer.benefit_highlight}\n"
            f"👉 _{offer.cta_text}_"
        )

    def _find_offer(self, offer_id: str) -> MarketingOffer:
        for ofr in self.campaigns:
            if ofr.offer_id == offer_id:
                return ofr
        return self.campaigns[0]


# Instancia Singleton del Subagente
marketing_funnel_agent = MarketingFunnelAgent()


if __name__ == "__main__":
    agent = MarketingFunnelAgent()
    print("=" * 75)
    print("🎯 CAMPAÑAS DE FUNNEL MARKETING — OCTUBRE 2026 (2 POR SEMANA)")
    print("=" * 75)
    for w in range(1, 5):
        camps = agent.get_campaigns_by_week(w)
        print(f"\n📅 SEMANA {w} DE OCTUBRE:")
        for c in camps:
            print(f"  • [{c.scope}] {c.headline} ({c.theme})")
            print(f"    Precio: Bs. {c.price_ves:.2f} | CTA: {c.cta_text}")
