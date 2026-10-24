#!/usr/bin/env python3
"""
IDS_CORE — Cliente 28: Cazador de Ofertas Movilnet
Módulo Clean-Room de Reglas de Descuento Avanzadas y Protocolo QR Rápido en Caja
================================================================================
Reconstrucción Soberana (Clean-Room Software Engineering) a partir de la Evidencia REA:
- Target 1: Protocolo de Canje Rápido en Caja Estilo Cashea Venezuela (`CAS-QRO`).
- Target 2: Motor de Reglas Condicionales de Descuento Voucherify / MedusaJS.
- Target 3: Centinela Anti-Colusión Cajero-Usuario y Límites de Velocidad en Terminal.

Cumple con la Directiva Invariante de Viabilidad Financiera (Margen Bruto >= 35%)
y la Directiva de Arquitectura Limpia Hexagonal (Dominio Puro sin frameworks web).
"""

import time
import hmac
import hashlib
import sys
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# Garantizar resolución de paquetes tanto standalone como paquete
_cazador_root = Path(__file__).resolve().parent.parent.parent
if str(_cazador_root) not in sys.path:
    sys.path.insert(0, str(_cazador_root))

try:
    from src.domain.invariants import CazadorInvariants, DomainInvariantViolationError
except (ImportError, ModuleNotFoundError):
    try:
        from invariants import CazadorInvariants, DomainInvariantViolationError
    except ImportError:
        from .invariants import CazadorInvariants, DomainInvariantViolationError


class PromotionRuleType(str, Enum):
    PERCENTAGE_DISCOUNT = "PERCENTAGE_DISCOUNT"
    BUY_X_GET_Y = "BUY_X_GET_Y"
    HAPPY_HOUR_WINDOW = "HAPPY_HOUR_WINDOW"
    TIERED_VOLUME = "TIERED_VOLUME"
    MIN_BASKET_VES = "MIN_BASKET_VES"


@dataclass(frozen=True)
class AdvancedPromotionRule:
    rule_id: str
    rule_type: PromotionRuleType
    titulo: str
    comercio_id: str
    precio_regular_unitario_ves: float
    costo_directo_unitario_ves: float
    # Parámetros condicionales
    descuento_pct: float = 0.0
    buy_x_units: int = 1
    get_y_units: int = 0
    y_discount_pct: float = 100.0  # 100% = gratis, 50% = a mitad de precio
    happy_hour_start: str = "00:00"  # Formato HH:MM
    happy_hour_end: str = "23:59"    # Formato HH:MM
    tiered_min_units: int = 1
    tiered_discount_pct: float = 0.0
    min_basket_ves: float = 0.0

    def __post_init__(self):
        if self.precio_regular_unitario_ves <= 0:
            raise DomainInvariantViolationError(
                f"Precio regular ({self.precio_regular_unitario_ves} VES) debe ser estrictamente positivo."
            )
        if self.costo_directo_unitario_ves < 0:
            raise DomainInvariantViolationError(
                f"Costo directo ({self.costo_directo_unitario_ves} VES) no puede ser negativo."
            )
        if self.costo_directo_unitario_ves >= self.precio_regular_unitario_ves:
            raise DomainInvariantViolationError(
                "El costo directo debe ser inferior al precio regular de venta."
            )


@dataclass
class RuleEvaluationResult:
    is_applicable: bool
    unidades_compradas: int
    unidades_bonificadas: int
    precio_total_regular_ves: float
    precio_final_oferta_ves: float
    costo_total_directo_ves: float
    ahorro_total_ves: float
    margen_bruto_final_pct: float
    razon_rechazo: Optional[str] = None


class CompactQRCodec:
    """
    Codec de Códigos QR Compactos de Alta Velocidad (Inspirado en el estándar Cashea).
    Genera un string alfanumérico compacto (<45 caracteres) optimizado para escaneo instantáneo
    en cajas con pistolas lectoras 2D o cámaras de baja resolución bajo poca iluminación.
    Formato: SOF-V1:{deal_id_tail}:{msisdn_tail}:{totp_token}:{sig8}
    """
    PREFIX = "SOF-V1"

    @classmethod
    def encode(cls, deal_id: str, msisdn: str, totp_token: str, secret_key: str) -> str:
        deal_tail = deal_id.replace("-", "")[-6:].upper()
        clean_msisdn = msisdn.replace("+", "").replace(" ", "")
        msisdn_tail = clean_msisdn[-6:]
        raw_payload = f"{deal_tail}:{msisdn_tail}:{totp_token}"
        sig = hmac.new(
            secret_key.encode("utf-8"),
            raw_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:8].upper()
        return f"{cls.PREFIX}:{deal_tail}:{msisdn_tail}:{totp_token}:{sig}"

    @classmethod
    def decode(cls, compact_qr: str, secret_key: str) -> Dict[str, Any]:
        parts = compact_qr.strip().split(":")
        if len(parts) != 5 or parts[0] != cls.PREFIX:
            raise DomainInvariantViolationError(
                f"Formato de QR compacto inválido. Se esperaba '{cls.PREFIX}:...'"
            )
        deal_tail, msisdn_tail, totp_token, sig = parts[1], parts[2], parts[3], parts[4]
        raw_payload = f"{deal_tail}:{msisdn_tail}:{totp_token}"
        expected_sig = hmac.new(
            secret_key.encode("utf-8"),
            raw_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:8].upper()

        if not hmac.compare_digest(sig, expected_sig):
            raise DomainInvariantViolationError("Firma criptográfica del código QR corrupta o alterada.")

        return {
            "version": parts[0],
            "deal_tail": deal_tail,
            "msisdn_tail": msisdn_tail,
            "totp_token": totp_token,
            "is_valid_signature": True
        }


class CashierAntiCollusionSentinel:
    """
    Centinela Anti-Colusión Cajero-Usuario.
    Previene re-canjes fraudulentos y saturación masiva en terminales de caja física.
    """
    def __init__(self, max_redemptions_per_minute: int = 6):
        self.max_rate = max_redemptions_per_minute
        # Mapeo: terminal_id -> lista de timestamps recientes
        self._terminal_history: Dict[str, List[float]] = {}

    def audit_terminal_rate(self, terminal_id: str, current_timestamp: Optional[float] = None) -> bool:
        now = current_timestamp if current_timestamp is not None else time.time()
        if terminal_id not in self._terminal_history:
            self._terminal_history[terminal_id] = []

        # Purgar eventos mayores a 60 segundos
        cutoff = now - 60.0
        self._terminal_history[terminal_id] = [
            ts for ts in self._terminal_history[terminal_id] if ts >= cutoff
        ]

        if len(self._terminal_history[terminal_id]) >= self.max_rate:
            raise DomainInvariantViolationError(
                f"Alerta Anti-Colusión: Terminal {terminal_id} excedió el límite de {self.max_rate} canjes por minuto."
            )

        self._terminal_history[terminal_id].append(now)
        return True


class ReaCleanRoomDealsEngine:
    """
    Motor Soberano de Reglas de Descuento Avanzadas Clean-Room.
    Evalúa condiciones complejas garantizando en todo momento que el margen de la PyME >= 35%.
    """

    @classmethod
    def evaluate_rule(
        cls,
        rule: AdvancedPromotionRule,
        cantidad_solicitada: int = 1,
        monto_cesta_ves: float = 0.0,
        hora_actual_str: Optional[str] = None
    ) -> RuleEvaluationResult:
        if cantidad_solicitada <= 0:
            raise DomainInvariantViolationError("La cantidad solicitada debe ser al menos 1 unidad.")

        # 1. Regla: MIN_BASKET_VES
        if rule.rule_type == PromotionRuleType.MIN_BASKET_VES:
            if monto_cesta_ves < rule.min_basket_ves:
                return RuleEvaluationResult(
                    is_applicable=False,
                    unidades_compradas=cantidad_solicitada,
                    unidades_bonificadas=0,
                    precio_total_regular_ves=cantidad_solicitada * rule.precio_regular_unitario_ves,
                    precio_final_oferta_ves=cantidad_solicitada * rule.precio_regular_unitario_ves,
                    costo_total_directo_ves=cantidad_solicitada * rule.costo_directo_unitario_ves,
                    ahorro_total_ves=0.0,
                    margen_bruto_final_pct=0.0,
                    razon_rechazo=f"Monto de cesta ({monto_cesta_ves} VES) no alcanza el mínimo de {rule.min_basket_ves} VES"
                )

        # 2. Regla: HAPPY_HOUR_WINDOW
        if rule.rule_type == PromotionRuleType.HAPPY_HOUR_WINDOW:
            current_time = hora_actual_str or time.strftime("%H:%M")
            if not (rule.happy_hour_start <= current_time <= rule.happy_hour_end):
                return RuleEvaluationResult(
                    is_applicable=False,
                    unidades_compradas=cantidad_solicitada,
                    unidades_bonificadas=0,
                    precio_total_regular_ves=cantidad_solicitada * rule.precio_regular_unitario_ves,
                    precio_final_oferta_ves=cantidad_solicitada * rule.precio_regular_unitario_ves,
                    costo_total_directo_ves=cantidad_solicitada * rule.costo_directo_unitario_ves,
                    ahorro_total_ves=0.0,
                    margen_bruto_final_pct=0.0,
                    razon_rechazo=f"Horario actual ({current_time}) fuera de la ventana Happy Hour ({rule.happy_hour_start} a {rule.happy_hour_end})"
                )

        # 3. Cálculo de Unidades e Ingreso
        unidades_bonificadas = 0
        precio_regular_total = cantidad_solicitada * rule.precio_regular_unitario_ves
        costo_directo_total = cantidad_solicitada * rule.costo_directo_unitario_ves

        if rule.rule_type == PromotionRuleType.PERCENTAGE_DISCOUNT:
            descuento = precio_regular_total * (rule.descuento_pct / 100.0)
            precio_final = precio_regular_total - descuento

        elif rule.rule_type == PromotionRuleType.HAPPY_HOUR_WINDOW:
            descuento = precio_regular_total * (rule.descuento_pct / 100.0)
            precio_final = precio_regular_total - descuento

        elif rule.rule_type == PromotionRuleType.BUY_X_GET_Y:
            # Ejemplo: Buy 2 get 1 (X=2, Y=1) -> por cada grupo de (X+Y) se descuenta el Y según y_discount_pct
            grupo = rule.buy_x_units + rule.get_y_units
            grupos_completos = cantidad_solicitada // grupo
            unidades_bonificadas = grupos_completos * rule.get_y_units
            
            descuento_unidad = rule.precio_regular_unitario_ves * (rule.y_discount_pct / 100.0)
            descuento = unidades_bonificadas * descuento_unidad
            precio_final = precio_regular_total - descuento

        elif rule.rule_type == PromotionRuleType.TIERED_VOLUME:
            if cantidad_solicitada >= rule.tiered_min_units:
                descuento = precio_regular_total * (rule.tiered_discount_pct / 100.0)
                precio_final = precio_regular_total - descuento
            else:
                descuento = 0.0
                precio_final = precio_regular_total

        else:
            descuento = 0.0
            precio_final = precio_regular_total

        ahorro = round(descuento, 2)
        precio_final = round(precio_final, 2)

        # 4. Verificación Estricta del Invariante II (Margen Bruto >= 35%)
        # Margen = (Precio_Final - Costo_Directo_Total) / Precio_Final >= 35%
        if precio_final <= 0:
            raise DomainInvariantViolationError("El precio final de la oferta no puede ser cero o negativo.")

        margen = ((precio_final - costo_directo_total) / precio_final) * 100.0
        margen = round(margen, 2)

        if margen < CazadorInvariants.MIN_GROSS_MARGIN_PCT:
            raise DomainInvariantViolationError(
                f"Violación de Invariante II en Regla {rule.rule_type}: Margen resultante ({margen}%) "
                f"cae por debajo del umbral mínimo del {CazadorInvariants.MIN_GROSS_MARGIN_PCT}%. "
                f"Oferta denegada para proteger la rentabilidad del comercio."
            )

        return RuleEvaluationResult(
            is_applicable=True,
            unidades_compradas=cantidad_solicitada,
            unidades_bonificadas=unidades_bonificadas,
            precio_total_regular_ves=round(precio_regular_total, 2),
            precio_final_oferta_ves=precio_final,
            costo_total_directo_ves=round(costo_directo_total, 2),
            ahorro_total_ves=ahorro,
            margen_bruto_final_pct=margen
        )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CLI de Verificación Soberana REA Clean-Room Deals Engine")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación matemática formal")
    args = parser.parse_args()

    if args.test:
        print("🏛️ Ejecutando auto-verificación del motor REA Clean-Room...")
        
        # Test 1: Regla BUY_X_GET_Y válida (Buy 2 Get 1 Free en Almuerzos Arturo's)
        # Costo unitario = 50 VES, Precio unitario = 150 VES (Margen regular = 66.6%)
        # Lleva 3 unidades: paga 2 * 150 = 300 VES. Costo total = 3 * 50 = 150 VES.
        # Margen final = (300 - 150) / 300 = 50% >= 35% -> VÁLIDO
        regla_arturos = AdvancedPromotionRule(
            rule_id="regla-arturos-2x1",
            rule_type=PromotionRuleType.BUY_X_GET_Y,
            titulo="Combo 2x1 Almuerzo Express",
            comercio_id="com-arturos-01",
            precio_regular_unitario_ves=150.0,
            costo_directo_unitario_ves=50.0,
            buy_x_units=2,
            get_y_units=1,
            y_discount_pct=100.0
        )
        res = ReaCleanRoomDealsEngine.evaluate_rule(regla_arturos, cantidad_solicitada=3)
        assert res.is_applicable is True
        assert res.precio_final_oferta_ves == 300.0
        assert res.ahorro_total_ves == 150.0
        assert res.margen_bruto_final_pct == 50.0
        print("  ✓ Test 1: Regla BUY_X_GET_Y aprobada con margen del 50.0%.")

        # Test 2: Regla rechazada por violar Invariante II (Descuento excesivo)
        # Costo = 80 VES, Precio = 100 VES. Descuento 30% -> Precio = 70 VES < Costo -> Margen negativo
        regla_ruinosa = AdvancedPromotionRule(
            rule_id="regla-ruina-01",
            rule_type=PromotionRuleType.PERCENTAGE_DISCOUNT,
            titulo="Descuento Suicida",
            comercio_id="com-farmatodo-01",
            precio_regular_unitario_ves=100.0,
            costo_directo_unitario_ves=80.0,
            descuento_pct=30.0
        )
        try:
            ReaCleanRoomDealsEngine.evaluate_rule(regla_ruinosa, cantidad_solicitada=1)
            assert False, "Debió rechazar por margen insuficiente"
        except DomainInvariantViolationError as e:
            print("  ✓ Test 2: Invariante II protegió exitosamente el margen de la PyME.")

        # Test 3: Codec de QR Compacto estilo Cashea
        secret = "secret-test-clave-2026"
        qr_str = CompactQRCodec.encode("deal-123456", "04161234567", "987654", secret)
        assert qr_str.startswith("SOF-V1:")
        decoded = CompactQRCodec.decode(qr_str, secret)
        assert decoded["totp_token"] == "987654"
        assert decoded["is_valid_signature"] is True
        print(f"  ✓ Test 3: Codec QR Compacto validado ({qr_str}, {len(qr_str)} caracteres).")

        # Test 4: Centinela Anti-Colusión
        sentinel = CashierAntiCollusionSentinel(max_redemptions_per_minute=2)
        sentinel.audit_terminal_rate("caja-01", current_timestamp=100.0)
        sentinel.audit_terminal_rate("caja-01", current_timestamp=110.0)
        try:
            sentinel.audit_terminal_rate("caja-01", current_timestamp=120.0)
            assert False, "Debió bloquear por exceso de velocidad en caja"
        except DomainInvariantViolationError:
            print("  ✓ Test 4: Centinela Anti-Colusión contuvo el exceso de velocidad en terminal.")

        print("🟢 Todas las auto-verificaciones de REA Clean-Room superadas al 100% (0 errores).")
