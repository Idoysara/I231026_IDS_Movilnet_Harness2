#!/usr/bin/env python3
"""
api/agents/agent_deals_scout.py — Sub-Agente Scout de Ofertas de Proximidad y Cuponería (Club 4GMAX)
=================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Fase 3: Integración Ecosistema Simbiótico / Enjambre L5 (Zero-Token & Carrier Billing)
Gobernanza: Protocolo Decagonal de Calidad & Regla Cero Adivinación (Fase 1 a 10)

Funcionalidades Principales:
1. Exploración y filtrado geoespacial de promociones vía SpatialRadarEngine (:8030).
2. Prevención de alucinaciones: Solo recomienda ofertas verificadas en el catálogo auditado.
3. Validación de Invariantes de Negocio:
   - Invariante II: Margen Bruto >= 35%.
   - Invariante III: Radio máximo de radar <= 3000m.
   - Invariante IV: Cuota anti-acaparamiento <= 3 cupones activos simultáneos.
   - Invariante V: Tokens dinámicos TOTP (60s) con HMAC-SHA256 y bóveda anti-replay.
   - Invariante VI: Conciliación Carrier Billing Split 20% Movilnet / 80% Comercio.
4. Generación de Magic Links 1-Tap con patrocinio de datos (Zero-Rating APN).
"""

from __future__ import annotations

import os
import sys
import time
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CAZADOR_ROOT = PROJECT_ROOT / "services" / "cazador_ofertas"
if str(CAZADOR_ROOT) not in sys.path:
    sys.path.insert(0, str(CAZADOR_ROOT))

from services.cazador_ofertas.src.application.cazador_service import CazadorApplicationService
from services.cazador_ofertas.src.infrastructure.deflector.magic_link_service import MagicLinkService
from services.cazador_ofertas.src.domain.invariants import (
    CazadorInvariants,
    DomainInvariantViolationError
)
from core.carrier_funnel_classifier import CarrierFunnelClassifier, Carrier

# Coordenadas de referencia para las 7 Ciudades Piloto Comerciales de Venezuela
ZONAS_REFERENCIA_VENEZUELA: Dict[str, Tuple[float, float]] = {
    # 1. Gran Caracas (5 Municipios / 27 Urbanizaciones Clave)
    # Municipio Chacao
    "chacao": (10.4925, -66.8550),
    "plaza el indio": (10.4925, -66.8550),
    "san ignacio": (10.4930, -66.8555),
    "sambil": (10.4910, -66.8530),
    "sambil chacao": (10.4910, -66.8530),
    "altamira": (10.4965, -66.8490),
    "plaza francia": (10.4965, -66.8490),
    "los palos grandes": (10.4985, -66.8415),
    "palos grandes": (10.4985, -66.8415),
    "centro plaza": (10.4960, -66.8450),
    "parque cristal": (10.4970, -66.8430),
    "el rosal": (10.4880, -66.8650),
    "bello campo": (10.4850, -66.8520),
    "ccct": (10.4850, -66.8520),
    "chuao": (10.4850, -66.8520),
    
    # Municipio Baruta
    "las mercedes": (10.4794, -66.8569),
    "tolon": (10.4794, -66.8569),
    "tolón": (10.4794, -66.8569),
    "colinas de bello monte": (10.4820, -66.8750),
    "bello monte": (10.4820, -66.8750),
    "la trinidad": (10.4350, -66.8520),
    "trinidad": (10.4350, -66.8520),
    "el cafetal": (10.4710, -66.8390),
    "cafetal": (10.4710, -66.8390),
    "santa sofia": (10.4710, -66.8390),
    "santa sofía": (10.4710, -66.8390),
    "plaza las americas": (10.4710, -66.8390),
    "plaza las américas": (10.4710, -66.8390),
    "prados del este": (10.4480, -66.8680),
    "santa fe": (10.4480, -66.8680),
    "alto prado": (10.4480, -66.8680),

    # Municipio Sucre
    "los dos caminos": (10.4940, -66.8320),
    "dos caminos": (10.4940, -66.8320),
    "millenium": (10.4940, -66.8320),
    "boleita": (10.4960, -66.8220),
    "boleíta": (10.4960, -66.8220),
    "los ruices": (10.4960, -66.8220),
    "la california": (10.4850, -66.8160),
    "california": (10.4850, -66.8160),
    "cc lider": (10.4850, -66.8160),
    "cc líder": (10.4850, -66.8160),
    "lider": (10.4850, -66.8160),
    "líder": (10.4850, -66.8160),
    "sebucan": (10.5010, -66.8280),
    "sebucán": (10.5010, -66.8280),
    "los chorros": (10.5010, -66.8280),
    "terrazas del avila": (10.4890, -66.8050),
    "terrazas del ávila": (10.4890, -66.8050),
    "el marques": (10.4890, -66.8050),
    "el marqués": (10.4890, -66.8050),

    # Municipio El Hatillo
    "el hatillo": (10.4240, -66.8250),
    "hatillo": (10.4240, -66.8250),
    "los naranjos": (10.4380, -66.8180),
    "galerias los naranjos": (10.4380, -66.8180),
    "galerías los naranjos": (10.4380, -66.8180),
    "la lagunita": (10.4190, -66.8120),
    "lagunita": (10.4190, -66.8120),
    "paseo el hatillo": (10.4190, -66.8120),
    "la boyera": (10.4320, -66.8320),
    "boyera": (10.4320, -66.8320),

    # Municipio Libertador
    "sabana grande": (10.4930, -66.8770),
    "city market": (10.4930, -66.8770),
    "el recreo": (10.4930, -66.8770),
    "chacaito": (10.4930, -66.8770),
    "chacaíto": (10.4930, -66.8770),
    "plaza venezuela": (10.4965, -66.8858),
    "la candelaria": (10.5050, -66.9070),
    "candelaria": (10.5050, -66.9070),
    "sambil candelaria": (10.5050, -66.9070),
    "centro": (10.5060, -66.9180),
    "centro historico": (10.5060, -66.9180),
    "el silencio": (10.5060, -66.9180),
    "capitolio": (10.5060, -66.9180),
    "san bernardino": (10.5130, -66.8990),
    "el paraiso": (10.4850, -66.9320),
    "el paraíso": (10.4850, -66.9320),
    "paraiso": (10.4850, -66.9320),
    "paraíso": (10.4850, -66.9320),
    "montalban": (10.4720, -66.9620),
    "montalbán": (10.4720, -66.9620),
    "catia": (10.5210, -66.9380),
    "perez bonalde": (10.5210, -66.9380),
    "pérez bonalde": (10.5210, -66.9380),
    "caracas": (10.4910, -66.8650),
    "ccs": (10.4910, -66.8650),

    # 2. Maracay (Aragua)
    "maracay": (10.2550, -67.5920),
    "las delicias": (10.2650, -67.5900),
    "los aviadores": (10.1980, -67.5750),
    "parque los aviadores": (10.1980, -67.5750),
    "san jacinto": (10.2450, -67.5750),
    "el limon": (10.3050, -67.6320),
    "el limón": (10.3050, -67.6320),

    # 3. Valencia (Carabobo)
    "valencia": (10.2300, -68.0080),
    "el vinedo": (10.2180, -68.0060),
    "el viñedo": (10.2180, -68.0060),
    "sambil valencia": (10.2520, -68.0130),
    "naguanagua": (10.2520, -68.0130),
    "san diego": (10.2550, -67.9550),
    "metropolis valencia": (10.2010, -67.9620),

    # 4. La Guaira (Vargas)
    "la guaira": (10.6050, -66.9500),
    "catia la mar": (10.6030, -67.0320),
    "playa grande": (10.6080, -67.0250),
    "maiquetia": (10.5980, -66.9550),
    "maiquetía": (10.5980, -66.9550),
    "macuto": (10.6120, -66.9050),
    "caribe": (10.6120, -66.8650),
    "caraballeda": (10.6120, -66.8650),

    # 5. Barquisimeto (Lara)
    "barquisimeto": (10.0710, -69.3050),
    "sambil barquisimeto": (10.0730, -69.2940),
    "cabudare": (10.0330, -69.2660),
    "nueva segovia": (10.0650, -69.2980),
    "av lara": (10.0680, -69.2950),
    "catedral barquisimeto": (10.0650, -69.3250),

    # 6. Maracaibo (Zulia)
    "maracaibo": (10.6650, -71.6100),
    "5 de julio": (10.6690, -71.6150),
    "calle 77": (10.6690, -71.6150),
    "bella vista": (10.6650, -71.6100),
    "lago mall": (10.6620, -71.6020),
    "el milagro": (10.6620, -71.6020),
    "sambil maracaibo": (10.7020, -71.6420),
    "delicias norte": (10.6850, -71.6350),

    # 7. Lechería (Anzoátegui)
    "lecheria": (10.1940, -64.6950),
    "lechería": (10.1940, -64.6950),
    "plaza mayor": (10.1920, -64.6930),
    "playa mansa": (10.1990, -64.6980),
    "puerto la cruz": (10.2150, -64.6350),
    "morro": (10.2010, -64.6920),
}
ZONAS_REFERENCIA_CARACAS = ZONAS_REFERENCIA_VENEZUELA



@dataclass
class ScoutDealItem:
    oferta_id: str
    titulo: str
    precio_oferta_ves: float
    precio_regular_ves: float
    descuento_pct: float
    comercio_id: str
    comercio_nombre: str
    categoria: str
    distancia_m: float
    anillo: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScoutDealsResult:
    success: bool
    msisdn: str
    lat: Optional[float]
    lon: Optional[float]
    total_ofertas: int
    ofertas: List[ScoutDealItem]
    magic_link: str
    mensaje_formateado: str
    requiere_ubicacion: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["ofertas"] = [o.to_dict() for o in self.ofertas]
        return data


class AgentDealsScout:
    """Sub-Agente Autónomo Scout de Ofertas (Club 4GMAX - Cazador de Ofertas)."""

    def __init__(
        self,
        cazador_service: Optional[CazadorApplicationService] = None,
        magic_service: Optional[MagicLinkService] = None
    ):
        self.cazador_service = cazador_service or CazadorApplicationService()
        self.magic_service = magic_service or MagicLinkService(service=self.cazador_service)
        self.agent_name = "AgentDealsScout"
        self.role = "Scout de Proximidad y Cuponería Soberana Club 4GMAX"

    @classmethod
    def inferir_coordenadas_de_texto(cls, texto: str) -> Optional[Tuple[float, float]]:
        """Busca menciones explícitas de zonas comerciales en el texto para resolver coordenadas WGS84."""
        t_low = texto.lower()
        for zona_key in sorted(ZONAS_REFERENCIA_CARACAS.keys(), key=len, reverse=True):
            if zona_key in t_low:
                return ZONAS_REFERENCIA_CARACAS[zona_key]
        return None

    @classmethod
    def inferir_categoria_de_texto(cls, texto: str) -> Optional[str]:
        """Infiere la categoría comercial del catálogo a partir de términos en lenguaje natural."""
        t_low = texto.lower()
        mapa = [
            (["desayuno", "desayunos", "desayunar", "cafe", "café", "panaderia", "panadería", "croissant", "cachito", "merienda", "torta", "dulce", "dulces", "reina pepiada"], "Café y Panadería"),
            (["almuerzo", "almuerzos", "almorzar", "cena", "cenas", "cenar", "restaurante", "restaurantes", "parrilla", "pasta", "criollo", "pabellon", "pabellón", "carne", "hambre", "comer", "comida", "antojo", "plato", "menú", "menu", "gastronomia", "gastronomía"], "Restaurantes"),
            (["hamburguesa", "hamburguesas", "pizza", "pizzas", "pollo", "broaster", "sushi", "perro caliente", "perros calientes", "churros", "comida rapida", "comida rápida", "franquicia", "pepito", "pepitos", "shawarma"], "Comida Rápida y Franquicias"),
            (["farmacia", "farmacias", "salud", "medicina", "medicinas", "vitamina", "vitaminas", "primeros auxilios", "pediatrico", "pediátrico"], "Farmacias y Salud"),
            (["supermercado", "supermercados", "mercado", "viveres", "víveres", "despensa", "charcuteria", "charcutería", "lacteos", "lácteos", "proteina", "proteínas", "proteinas", "carniceria", "carnicería"], "Supermercados"),
            (["peluqueria", "peluquería", "corte", "manicura", "spa", "facial", "optica", "óptica", "belleza"], "Belleza y Cuidado Personal"),
            (["autolavado", "lavado", "aceite", "alineacion", "alineación", "taller", "ferreteria", "ferretería", "celular", "repuesto"], "Servicios y Hogar")
        ]
        for keywords, cat in mapa:
            if any(k in t_low for k in keywords):
                return cat
        return None

    def scout_deals(
        self,
        phone: str,
        message: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        max_distancia_m: float = 3000.0,
        categoria: Optional[str] = None
    ) -> ScoutDealsResult:
        """
        Explora ofertas en radar geodésico y retorna las promociones verificadas más cercanas.
        Aplica estrictamente la regla de Cero Adivinación: si falta ubicación, la solicita amablemente.
        """
        clean_phone = CarrierFunnelClassifier.clean_msisdn(phone) or phone
        carrier_enum, _, is_comp = CarrierFunnelClassifier.identify_carrier(clean_phone)
        is_movilnet = (not is_comp) and (carrier_enum == Carrier.MOVILNET)

        # 1. Inferir categoría si no viene explícita
        if not categoria:
            categoria = self.inferir_categoria_de_texto(message)

        # 2. Resolver coordenadas si no vienen dadas
        if lat is None or lon is None:
            inferred = self.inferir_coordenadas_de_texto(message)
            if inferred:
                lat, lon = inferred

        # 3. Si todavía no hay coordenadas, aplicar Regla Cero Adivinación
        if lat is None or lon is None:
            magic_link = self.magic_service.generar_magic_link(
                msisdn=clean_phone if is_movilnet else "04160000001"
            )
            cat_aviso = f" de *{categoria}*" if categoria else ""
            msg_solicitud = (
                f"¡Con gusto te ayudo a cazar las mejores ofertas{cat_aviso} del Club 4GMAX! 🏷️🍔\n\n"
                "Para recomendarte los descuentos más cercanos y exactos a tu alrededor, "
                "¿me indicas en qué ciudad o zona te encuentras (ej. Chacao, Los Palos Grandes, El Cafetal), "
                "o compártenos tu ubicación GPS?"
            )
            return ScoutDealsResult(
                success=True,
                msisdn=clean_phone,
                lat=None,
                lon=None,
                total_ofertas=0,
                ofertas=[],
                magic_link=magic_link,
                mensaje_formateado=msg_solicitud,
                requiere_ubicacion=True
            )

        # 4. Búsqueda radar geoespacial
        radar_res = self.cazador_service.buscar_ofertas_radar(
            user_lat=lat,
            user_lon=lon,
            max_distancia_m=max_distancia_m,
            categoria=categoria
        )

        anillos = radar_res.get("anillos", {})
        scout_items: List[ScoutDealItem] = []

        for ring_name, label_anillo in [
            ("zona_1_inmediata", "Inmediata (0-500m)"),
            ("zona_2_vecindario", "Vecindario (500-1000m)"),
            ("zona_3_urbana", "Urbana (1000-3000m)")
        ]:
            for entry in anillos.get(ring_name, []):
                comercio_info = entry.get("comercio", {})
                dist_m = float(comercio_info.get("distance_meters", comercio_info.get("distance_m", 0.0)))
                comercio_obj = self.cazador_service.comercios.get(comercio_info.get("id"))
                nombre_c = comercio_obj.nombre if comercio_obj else comercio_info.get("nombre", "Comercio Aliado")

                for ofe in entry.get("ofertas", []):
                    scout_items.append(ScoutDealItem(
                        oferta_id=ofe.get("id"),
                        titulo=ofe.get("titulo"),
                        precio_oferta_ves=float(ofe.get("precio_oferta_ves", 0.0)),
                        precio_regular_ves=float(ofe.get("precio_regular_ves", 0.0)),
                        descuento_pct=float(ofe.get("descuento_pct", 0.0)),
                        comercio_id=comercio_info.get("id"),
                        comercio_nombre=nombre_c,
                        categoria=comercio_obj.categoria if comercio_obj else "General",
                        distancia_m=round(dist_m, 1),
                        anillo=label_anillo
                    ))

        # Si se filtró por categoría y no hubo resultados, intentar fallback sin filtro de categoría
        if not scout_items and categoria:
            radar_res_fallback = self.cazador_service.buscar_ofertas_radar(
                user_lat=lat,
                user_lon=lon,
                max_distancia_m=max_distancia_m,
                categoria=None
            )
            anillos_fb = radar_res_fallback.get("anillos", {})
            for ring_name, label_anillo in [
                ("zona_1_inmediata", "Inmediata (0-500m)"),
                ("zona_2_vecindario", "Vecindario (500-1000m)"),
                ("zona_3_urbana", "Urbana (1000-3000m)")
            ]:
                for entry in anillos_fb.get(ring_name, []):
                    comercio_info = entry.get("comercio", {})
                    dist_m = float(comercio_info.get("distance_meters", comercio_info.get("distance_m", 0.0)))
                    comercio_obj = self.cazador_service.comercios.get(comercio_info.get("id"))
                    nombre_c = comercio_obj.nombre if comercio_obj else comercio_info.get("nombre", "Comercio Aliado")
                    for ofe in entry.get("ofertas", []):
                        scout_items.append(ScoutDealItem(
                            oferta_id=ofe.get("id"),
                            titulo=ofe.get("titulo"),
                            precio_oferta_ves=float(ofe.get("precio_oferta_ves", 0.0)),
                            precio_regular_ves=float(ofe.get("precio_regular_ves", 0.0)),
                            descuento_pct=float(ofe.get("descuento_pct", 0.0)),
                            comercio_id=comercio_info.get("id"),
                            comercio_nombre=nombre_c,
                            categoria=comercio_obj.categoria if comercio_obj else "General",
                            distancia_m=round(dist_m, 1),
                            anillo=label_anillo
                        ))

        # Generar Magic Link con 1-Tap Zero-Rating en puerto 8010
        first_offer_id = scout_items[0].oferta_id if scout_items else None
        magic_link = self.magic_service.generar_magic_link(
            msisdn=clean_phone if is_movilnet else "04160000001",
            oferta_id=first_offer_id
        )

        # 5. Formatear respuesta conversacional
        if not scout_items:
            mensaje = (
                f"👋 ¡Hola! En el Club 4GMAX no encontramos promociones activas en un radio de {int(max_distancia_m)}m "
                f"de tu ubicación actual.\n\n"
                f"📱 Abre nuestro Radar Soberano en vivo en la PWA:\n"
                f"{magic_link}\n\n"
                f"✨ Navegación 100% patrocinada con Zero-Rating para líneas Movilnet."
            )
        else:
            items_txt = []
            for item in scout_items[:3]:
                items_txt.append(
                    f"🏷️ *{item.titulo}* ({item.distancia_m:.0f}m)\n"
                    f"   💰 *Bs {item.precio_oferta_ves:,.2f}* (-{item.descuento_pct:.0f}%) en *{item.comercio_nombre}*"
                )
            cuerpo = "\n\n".join(items_txt)
            titulo_cat = f" de *{categoria}*" if categoria else ""
            mensaje = (
                f"🎯 **¡Club 4GMAX Activado!** Encontramos {len(scout_items)} ofertas exclusivas{titulo_cat} cerca de ti:\n\n"
                f"{cuerpo}\n\n"
                f"⚡ **Reclama tu cupón sin gastar megas (1-Tap Zero-Rating):**\n"
                f"{magic_link}\n\n"
                f"🔒 Cupón dinámico TOTP de 60s con liquidación directa por saldo Movilnet."
            )

        return ScoutDealsResult(
            success=True,
            msisdn=clean_phone,
            lat=lat,
            lon=lon,
            total_ofertas=len(scout_items),
            ofertas=scout_items,
            magic_link=magic_link,
            mensaje_formateado=mensaje,
            requiere_ubicacion=False
        )

    def claim_deal_coupon(self, phone: str, offer_id: str) -> Dict[str, Any]:
        """Reclama un cupón dinámico para el abonado validando cuota <= 3 y stock atómico."""
        clean_phone = CazadorInvariants.validar_msisdn_movilnet(phone)
        return self.cazador_service.reclamar_cupon(oferta_id=offer_id, msisdn=clean_phone)

    def redeem_deal_coupon(
        self,
        coupon_id: str,
        phone: str,
        merchant_id: str,
        hmac_signature: str
    ) -> Dict[str, Any]:
        """Canjea un cupón en la caja POS validando FSM y Bóveda Anti-Replay."""
        clean_phone = CazadorInvariants.validar_msisdn_movilnet(phone)
        return self.cazador_service.canjear_cupon(
            cupon_id=coupon_id,
            msisdn=clean_phone,
            comercio_id=merchant_id,
            firma_hmac=hmac_signature
        )

    def list_user_coupons(self, phone: str) -> List[Dict[str, Any]]:
        """Obtiene la lista de cupones vigentes e históricos del usuario."""
        clean_phone = CazadorInvariants.validar_msisdn_movilnet(phone)
        return self.cazador_service.obtener_cupones_usuario(clean_phone)


# ============================================================================
# CLI DE AUTO-VERIFICACIÓN FORMAL (Pilar II & V)
# ============================================================================

def run_self_verification() -> bool:
    """Verifica el correcto funcionamiento del AgentDealsScout."""
    print("🧪 Verificando AgentDealsScout...")
    agent = AgentDealsScout()

    # 1. Consulta sin ubicación -> Regla Cero Adivinación
    res_no_loc = agent.scout_deals(phone="04169991122", message="Quiero ver ofertas")
    assert res_no_loc.requiere_ubicacion is True
    assert "indicas en qué ciudad o zona" in res_no_loc.mensaje_formateado
    print("  ✅ Cero adivinación validado: exige zona al usuario.")

    # 2. Consulta con inferencia de zona ("Chacao")
    res_chacao = agent.scout_deals(phone="04169991122", message="ofertas en Chacao")
    assert res_chacao.requiere_ubicacion is False
    assert res_chacao.total_ofertas > 0
    assert len(res_chacao.ofertas) > 0
    assert "Club 4GMAX" in res_chacao.mensaje_formateado
    print(f"  ✅ Búsqueda por zona Chacao exitosa: {res_chacao.total_ofertas} ofertas.")

    # 3. Consulta con coordenadas explícitas (Las Mercedes: 10.4810, -66.8610)
    res_gps = agent.scout_deals(phone="04169991122", message="ofertas", lat=10.4810, lon=-66.8610)
    assert res_gps.total_ofertas > 0
    assert res_gps.magic_link.startswith("http")
    print(f"  ✅ Búsqueda por GPS exitosa: {res_gps.total_ofertas} ofertas con Magic Link.")

    print("🎉 AgentDealsScout verificado al 100% con CERO errores.")
    return True


if __name__ == "__main__":
    run_self_verification()
