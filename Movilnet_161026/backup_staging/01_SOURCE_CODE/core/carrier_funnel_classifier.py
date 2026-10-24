#!/usr/bin/env python3
"""
core/carrier_funnel_classifier.py — Clasificador de Operadoras & Motor de Funnel Marketing
===========================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)

Funcionalidad:
1. Identifica la operadora de telefonía móvil a partir del prefijo nacional venezolano (E.164):
   - Movilnet: 0416, 0426 (Base masiva de 4 millones de abonados)
   - Movistar: 0414, 0424 (Competencia directa)
   - Digitel: 0412 (Competencia directa)
   - Otro / Internacional: Prefijos no catalogados
2. Para abonados Movilnet: Enruta a Fast-Path Telco ODA (Saldo, Megas, Contrato, C2P, EIR).
3. Para usuarios de la Competencia (Movistar/Digitel):
   Activa la Campaña de Funnel Marketing de Portabilidad / Captación hacia Movilnet 4GMAX:
   - Oferta de bienvenida: 10 GB de datos + eSIM gratis + Ahorro del 60% en renta.
"""

from __future__ import annotations

import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, Optional
from enum import Enum

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class Carrier(str, Enum):
    MOVILNET = "MOVILNET"
    MOVISTAR = "MOVISTAR"
    DIGITEL = "DIGITEL"
    CANTV_FIJA = "CANTV_FIJA"
    VOIP_ISP_SPECIAL = "VOIP_ISP_SPECIAL"
    OTHER = "OTRO"


class PipelineRoute(str, Enum):
    FAST_PATH_ODA = "FAST_PATH_TELCO_ODA"
    FUNNEL_PORTABILITY = "FUNNEL_MARKETING_PORTABILIDAD"
    AI_GEMINI_FALLBACK = "AI_AGENT_GEMINI"


@dataclass
class CarrierClassificationResult:
    carrier: Carrier
    carrier_label: str
    is_competitor: bool
    pipeline_route: PipelineRoute
    phone_national: str
    original_raw: str
    funnel_offer_headline: Optional[str] = None
    funnel_reply_text: Optional[str] = None
    funnel_stage: Optional[str] = None

    @property
    def is_movilnet_subscriber(self) -> bool:
        """Compuerta booleana inmutable de abonado Movilnet (0416/0426)."""
        return not self.is_competitor and self.carrier == Carrier.MOVILNET

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["carrier"] = self.carrier.value
        d["pipeline_route"] = self.pipeline_route.value
        d["is_movilnet_subscriber"] = self.is_movilnet_subscriber
        return d


class CarrierFunnelClassifier:
    """Motor de clasificación de tráfico celular y enrutamiento comercial de Funnel."""

    # Prefijos nacionales venezolanos (CONATEL / UIT-T E.164)
    MOVILNET_PREFIXES = ("0416", "0426", "416", "426")
    MOVISTAR_PREFIXES = ("0414", "0424", "414", "424")
    DIGITEL_PREFIXES = ("0412", "412")
    SPECIAL_VOIP_PREFIXES = ("0500", "0501", "0800", "0900", "500", "501", "800", "900")

    @classmethod
    def clean_msisdn(cls, raw: str) -> str:
        """Limpia sufijos de WhatsApp y retorna el número nacional con 0 adelante."""
        if not raw:
            return ""
        s = raw.split("@")[0].split(":")[0]
        digits = re.sub(r"[^\d]", "", s)
        if digits.startswith("0058") and len(digits) == 14:
            return "0" + digits[4:]
        if digits.startswith("58") and len(digits) == 12:
            return "0" + digits[2:]
        if len(digits) == 10 and not digits.startswith("0"):
            return "0" + digits
        if len(digits) == 11 and digits.startswith("0"):
            return digits
        return digits

    @classmethod
    def normalize_phone(cls, raw: str) -> Tuple[str, str]:
        """Normaliza números de teléfono retornando (formato_nacional, raw_original)."""
        national = cls.clean_msisdn(raw)
        return national, raw

    @classmethod
    def classify(cls, phone_national: str) -> CarrierClassificationResult:
        """Clasifica el número nacional y retorna CarrierClassificationResult."""
        cleaned = cls.clean_msisdn(phone_national)
        carrier, carrier_label, is_comp = cls.identify_carrier(cleaned)
        return CarrierClassificationResult(
            carrier=carrier,
            carrier_label=carrier_label,
            is_competitor=is_comp,
            pipeline_route=PipelineRoute.FUNNEL_PORTABILITY if is_comp else PipelineRoute.FAST_PATH_ODA,
            phone_national=cleaned,
            original_raw=phone_national,
            funnel_stage="RETENTION_MASIVO" if not is_comp else "MOFU_CONSIDERACION_COMPETENCIA"
        )

    @classmethod
    def identify_carrier(cls, phone_national: str) -> Tuple[Carrier, str, bool]:
        """Identifica la operadora a partir de los prefijos según regulación CONATEL."""
        cleaned = cls.clean_msisdn(phone_national)
        if not cleaned:
            return Carrier.OTHER, "No Identificado", False

        prefix4 = cleaned[:4]
        prefix3 = cleaned[:3]
        prefix2 = cleaned[:2]

        if prefix4 in ("0416", "0426"):
            return Carrier.MOVILNET, "Movilnet 4GMAX", False
        elif prefix4 in ("0414", "0424"):
            return Carrier.MOVISTAR, "Movistar Venezuela", True
        elif prefix4 == "0412":
            return Carrier.DIGITEL, "Digitel 4G LTE", True
        elif prefix4 in ("0500", "0501", "0800", "0900"):
            svc_name = "Toll-Free Gratuito" if prefix4 == "0800" else ("Cobro Compartido" if prefix4 == "0500" else "Servicio Especial No Geográfico")
            return Carrier.VOIP_ISP_SPECIAL, f"Servicio No Geográfico / VoIP ISP {prefix4} ({svc_name})", True
        elif prefix2 == "02":
            if prefix3 == "021":
                return Carrier.CANTV_FIJA, "CANTV / Telefonía Fija Gran Caracas (0212)", True
            else:
                return Carrier.CANTV_FIJA, f"CANTV / Telefonía Fija Regional ({prefix4})", True
        else:
            return Carrier.OTHER, "Operadora Externa / Roaming", True

    @classmethod
    def evaluate_inbound_message(cls, phone_raw: str, message_text: str, sender_name: str = "Usuario") -> CarrierClassificationResult:
        """
        Clasifica el mensaje entrante y decide la ruta:
        - Si es Movilnet: Fast-Path Telco ODA
        - Si es Competencia (Movistar/Digitel): Funnel Marketing de Portabilidad a Movilnet 4GMAX
        - Si es Fija CANTV / ISP VoIP: Orientación comercial hacia red móvil celular Movilnet 4GMAX
        """
        national_phone = cls.clean_msisdn(phone_raw)
        carrier, carrier_label, is_competitor = cls.identify_carrier(national_phone)
        lower_msg = (message_text or "").lower().strip()

        # Detección de intenciones Telco comunes
        is_telco_intent = any(kw in lower_msg for kw in [
            "saldo", "mega", "datos", "cupo", "balance", "debo", "corte",
            "contrato", "plan", "titular", "recarga", "c2p", "robo", "bloqueo", "imei", "portabilidad", "cambiar"
        ])

        if carrier == Carrier.MOVILNET:
            # Abonado Movilnet (Base 4 millones) -> Ruta Fast-Path ODA
            pipeline = PipelineRoute.FAST_PATH_ODA if is_telco_intent else PipelineRoute.AI_GEMINI_FALLBACK
            return CarrierClassificationResult(
                carrier=carrier,
                carrier_label=carrier_label,
                is_competitor=False,
                pipeline_route=pipeline,
                phone_national=national_phone,
                original_raw=phone_raw,
                funnel_stage="RETENTION_MASIVO"
            )

        # Tráfico no-Movilnet (Móviles de la Competencia, Fija CANTV o VoIP/Especiales ISP)
        if carrier in (Carrier.MOVISTAR, Carrier.DIGITEL):
            competitor_name = "Movistar" if carrier == Carrier.MOVISTAR else "Digitel"
            if any(w in lower_msg for w in ["cambiar", "portabilidad", "migrar", "esim", "quiero movilnet", "adquirir"]):
                stage = "BOFU_CONVERSION_PORTABILIDAD"
                headline = "🎯 ¡Paso Final a Movilnet 4GMAX!"
                reply = (
                    f"¡Excelente decisión, {sender_name}! Cambiarte de {competitor_name} a Movilnet 4GMAX es 100% gratis. "
                    f"Recibe: ✨ Tu eSIM digital en minutos + 🎁 Bono de 10 GB de navegación gratis + WhatsApp libre. "
                    f"Haz clic aquí para activar tu portabilidad con tu cédula: https://movilnet.com.ve/portabilidad-express"
                )
            else:
                stage = "MOFU_CONSIDERACION_COMPETENCIA"
                headline = f"🚀 ¡Bienvenido a Movilnet desde {competitor_name}!"
                reply = (
                    f"Hola {sender_name}, notamos que nos contactas desde tu línea {competitor_name} ({national_phone}). "
                    f"¿Sabías que con el Plan Básico Conecta 5GB o Inteliplan 10GB de Movilnet ahorras hasta un 60% comparado con tu renta actual? "
                    f"Únete a los más de 4 millones de venezolanos conectados. Escribe 'PORTABILIDAD' para recibir tu eSIM con 10 GB de regalo."
                )
        elif carrier == Carrier.CANTV_FIJA:
            stage = "MOFU_FIJA_A_MOVILNET_4GMAX"
            headline = "📡 ¡Bienvenido a Movilnet 4GMAX!"
            reply = (
                f"Hola {sender_name}, identificamos que nos contactas desde una línea fija ({national_phone}). "
                f"Movilnet 4GMAX es el operador móvil del Estado venezolano. Si deseas adquirir una línea celular "
                f"4GMAX con eSIM o conocer nuestros planes de datos móviles para tu hogar o empresa, escribe 'PLANES'."
            )
        elif carrier == Carrier.VOIP_ISP_SPECIAL:
            stage = "MOFU_VOIP_SPECIAL_SERVICE"
            headline = "🏢 Centro de Atención Movilnet 4GMAX"
            reply = (
                f"Estimado usuario ({national_phone}): Ha contactado al canal oficial de autogestión Movilnet 4GMAX. "
                f"Para información sobre planes corporativos, interconexión o portabilidad numérica, escribe 'PLANES' o 'PORTABILIDAD'."
            )
        else:
            stage = "MOFU_CONSIDERACION_COMPETENCIA"
            headline = "🚀 ¡Bienvenido a Movilnet 4GMAX!"
            reply = (
                f"Hola {sender_name}, gracias por contactar a Movilnet 4GMAX desde {national_phone}. "
                f"Escribe 'PLANES' o 'PORTABILIDAD' para conocer nuestra cobertura nacional y adquirir tu línea 4GMAX."
            )

        return CarrierClassificationResult(
            carrier=carrier,
            carrier_label=carrier_label,
            is_competitor=True,
            pipeline_route=PipelineRoute.FUNNEL_PORTABILITY,
            phone_national=national_phone,
            original_raw=phone_raw,
            funnel_offer_headline=headline,
            funnel_reply_text=reply,
            funnel_stage=stage
        )


def run_self_test() -> bool:
    """Auto-verificación matemática formal del clasificador."""
    # 1. Caso Movilnet 0416
    res1 = CarrierFunnelClassifier.evaluate_inbound_message("584160000001@s.whatsapp.net", "saldo disponible")
    assert res1.carrier == Carrier.MOVILNET
    assert res1.is_competitor is False
    assert res1.pipeline_route == PipelineRoute.FAST_PATH_ODA

    # 2. Caso Movistar 0414 (Competencia)
    res2 = CarrierFunnelClassifier.evaluate_inbound_message("584142554590@s.whatsapp.net", "Podemos probar si estas funcionando")
    assert res2.carrier == Carrier.MOVISTAR
    assert res2.is_competitor is True
    assert res2.pipeline_route == PipelineRoute.FUNNEL_PORTABILITY
    assert "Movistar" in res2.funnel_reply_text

    # 3. Caso Digitel 0412 (Competencia - Intención de portabilidad)
    res3 = CarrierFunnelClassifier.evaluate_inbound_message("04129998877", "quiero cambiarme a movilnet con esim")
    assert res3.carrier == Carrier.DIGITEL
    assert res3.is_competitor is True
    assert res3.funnel_stage == "BOFU_CONVERSION_PORTABILIDAD"
    assert "portabilidad-express" in res3.funnel_reply_text

    # 4. Caso CANTV Fija (0212 Caracas)
    res4 = CarrierFunnelClassifier.evaluate_inbound_message("02125551234", "hola deseo informacion de planes")
    assert res4.carrier == Carrier.CANTV_FIJA
    assert res4.is_competitor is True
    assert "fija" in res4.funnel_reply_text

    # 5. Caso VoIP ISP / Servicio No Geográfico (0500 Cobro Compartido)
    res5 = CarrierFunnelClassifier.evaluate_inbound_message("05001234567", "informacion corporativa")
    assert res5.carrier == Carrier.VOIP_ISP_SPECIAL
    assert res5.is_competitor is True

    # 6. Caso Toll-Free Gratuito (0800)
    res6 = CarrierFunnelClassifier.evaluate_inbound_message("08006684563", "soporte tecnico")
    assert res6.carrier == Carrier.VOIP_ISP_SPECIAL
    assert res6.is_competitor is True

    # 7. Caso prefijo internacional 0058 (14 dígitos)
    cleaned_0058 = CarrierFunnelClassifier.clean_msisdn("00584241533712")
    assert cleaned_0058 == "04241533712"
    cleaned_0058_movilnet = CarrierFunnelClassifier.clean_msisdn("00584160000001")
    assert cleaned_0058_movilnet == "04160000001"

    print("✅ [CARRIER FUNNEL CLASSIFIER]: Auto-verificación formal matemática superada (7/7 tests PASS).")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clasificador de Operadoras & Funnel Marketing")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación formal")
    parser.add_argument("--phone", type=str, help="Teléfono a clasificar")
    parser.add_argument("--msg", type=str, default="saldo", help="Mensaje entrante")
    args = parser.parse_args()

    if args.test:
        run_self_test()
    elif args.phone:
        res = CarrierFunnelClassifier.evaluate_inbound_message(args.phone, args.msg)
        import json
        print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
    else:
        parser.print_help()
