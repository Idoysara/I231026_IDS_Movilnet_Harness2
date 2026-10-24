"""
Suite de Pruebas Automatizadas para el Motor REA Clean-Room de Reglas Avanzadas y QR Compacto.
Verifica:
1. Reglas condicionales Voucherify/Medusa (Percentage, Buy X Get Y, Happy Hour, Tiered, Min Basket).
2. Cumplimiento de Invariante II (Margen Bruto >= 35%).
3. Codec de QR Compacto de Alta Velocidad (Protocolo Cashea).
4. Centinela Anti-Colusión y Control de Tasa en Terminales POS.
5. Integración directa con CazadorApplicationService.
"""
import sys
from pathlib import Path
import pytest

CLIENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

for p in (str(PROJECT_ROOT), str(CLIENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.domain.rea_clean_room_deals_engine import (
    ReaCleanRoomDealsEngine,
    AdvancedPromotionRule,
    PromotionRuleType,
    CompactQRCodec,
    CashierAntiCollusionSentinel,
    RuleEvaluationResult
)
from src.domain.invariants import DomainInvariantViolationError
from src.application.cazador_service import CazadorApplicationService


def test_rea_rule_percentage_discount_valido():
    """Prueba que un descuento porcentual con margen final >= 35% sea aprobado."""
    rule = AdvancedPromotionRule(
        rule_id="rule-pct-01",
        rule_type=PromotionRuleType.PERCENTAGE_DISCOUNT,
        titulo="20% Descuento Miércoles Plaza's",
        comercio_id="com-plazas-01",
        precio_regular_unitario_ves=200.0,
        costo_directo_unitario_ves=100.0,  # Costo 50%
        descuento_pct=20.0                 # Precio final = 160 VES -> Margen = (160-100)/160 = 37.5% >= 35%
    )
    result = ReaCleanRoomDealsEngine.evaluate_rule(rule, cantidad_solicitada=2)
    assert result.is_applicable is True
    assert result.precio_total_regular_ves == 400.0
    assert result.precio_final_oferta_ves == 320.0
    assert result.ahorro_total_ves == 80.0
    assert result.margen_bruto_final_pct == 37.5


def test_rea_rule_buy_x_get_y_arturos():
    """Prueba la regla Buy 2 Get 1 Free (2x1 de combos en Arturo's)."""
    rule = AdvancedPromotionRule(
        rule_id="rule-bxg-01",
        rule_type=PromotionRuleType.BUY_X_GET_Y,
        titulo="Combo 2x1 Arturo's Express",
        comercio_id="com-arturos-01",
        precio_regular_unitario_ves=150.0,
        costo_directo_unitario_ves=50.0,
        buy_x_units=2,
        get_y_units=1,
        y_discount_pct=100.0
    )
    # Pide 3 unidades: paga 2 (300 VES), 1 bonificada. Costo total: 3 * 50 = 150 VES.
    # Margen = (300 - 150) / 300 = 50.0% >= 35%
    result = ReaCleanRoomDealsEngine.evaluate_rule(rule, cantidad_solicitada=3)
    assert result.is_applicable is True
    assert result.unidades_bonificadas == 1
    assert result.precio_final_oferta_ves == 300.0
    assert result.ahorro_total_ves == 150.0
    assert result.margen_bruto_final_pct == 50.0


def test_rea_rule_happy_hour_window():
    """Prueba la activación y rechazo de promociones en franja horaria (Happy Hour)."""
    rule = AdvancedPromotionRule(
        rule_id="rule-hh-01",
        rule_type=PromotionRuleType.HAPPY_HOUR_WINDOW,
        titulo="Almuerzo Happy Hour Cine Citta",
        comercio_id="com-cinecitta-01",
        precio_regular_unitario_ves=180.0,
        costo_directo_unitario_ves=80.0,
        descuento_pct=25.0,
        happy_hour_start="12:00",
        happy_hour_end="15:00"
    )
    # Dentro de la franja (13:30) -> Aprobado
    res_in = ReaCleanRoomDealsEngine.evaluate_rule(rule, cantidad_solicitada=1, hora_actual_str="13:30")
    assert res_in.is_applicable is True
    assert res_in.precio_final_oferta_ves == 135.0

    # Fuera de la franja (17:00) -> No aplicable
    res_out = ReaCleanRoomDealsEngine.evaluate_rule(rule, cantidad_solicitada=1, hora_actual_str="17:00")
    assert res_out.is_applicable is False
    assert "fuera de la ventana Happy Hour" in res_out.razon_rechazo


def test_rea_rule_tiered_volume():
    """Prueba descuentos escalonados por volumen de compra."""
    rule = AdvancedPromotionRule(
        rule_id="rule-tier-01",
        rule_type=PromotionRuleType.TIERED_VOLUME,
        titulo="Pack 5+ Pinturas EPA",
        comercio_id="com-epa-01",
        precio_regular_unitario_ves=300.0,
        costo_directo_unitario_ves=150.0,
        tiered_min_units=5,
        tiered_discount_pct=15.0
    )
    # Comprando 3 unidades (no califica para descuento)
    res_3 = ReaCleanRoomDealsEngine.evaluate_rule(rule, cantidad_solicitada=3)
    assert res_3.ahorro_total_ves == 0.0
    assert res_3.precio_final_oferta_ves == 900.0

    # Comprando 5 unidades (califica para 15% descuento)
    res_5 = ReaCleanRoomDealsEngine.evaluate_rule(rule, cantidad_solicitada=5)
    assert res_5.ahorro_total_ves == 225.0
    assert res_5.precio_final_oferta_ves == 1275.0
    assert res_5.margen_bruto_final_pct == 41.18


def test_rea_invariable_margin_rejection():
    """Prueba que el motor rechace automáticamente reglas que violen el Invariante II (<35%)."""
    rule_ruinosa = AdvancedPromotionRule(
        rule_id="rule-ruinosa-01",
        rule_type=PromotionRuleType.PERCENTAGE_DISCOUNT,
        titulo="Descuento Agresivo Destructor de Margen",
        comercio_id="com-farmatodo-01",
        precio_regular_unitario_ves=100.0,
        costo_directo_unitario_ves=70.0,  # Costo 70%
        descuento_pct=25.0                 # Precio final = 75 VES -> Margen = (75-70)/75 = 6.67% < 35%
    )
    with pytest.raises(DomainInvariantViolationError) as exc_info:
        ReaCleanRoomDealsEngine.evaluate_rule(rule_ruinosa, cantidad_solicitada=1)
    assert "Violación de Invariante II" in str(exc_info.value)
    assert "cae por debajo del umbral mínimo del 35.0%" in str(exc_info.value)


def test_rea_compact_qr_codec_cashea_format():
    """Prueba el encoder y decoder del formato QR ultracompacto (<45 caracteres) estilo Cashea."""
    secret = "secret-cazador-movilnet-2026"
    deal_id = "deal-plaza-queso-01"
    msisdn = "04161234567"
    totp = "458921"

    compact_qr = CompactQRCodec.encode(deal_id, msisdn, totp, secret)
    assert compact_qr.startswith("SOF-V1:")
    assert len(compact_qr) <= 45

    # Decodificación y validación
    decoded = CompactQRCodec.decode(compact_qr, secret)
    assert decoded["totp_token"] == totp
    assert decoded["is_valid_signature"] is True

    # Intento de falsificación de firma
    tampered_qr = compact_qr[:-2] + "XX"
    with pytest.raises(DomainInvariantViolationError) as exc_info:
        CompactQRCodec.decode(tampered_qr, secret)
    assert "Firma criptográfica del código QR corrupta" in str(exc_info.value)


def test_rea_cashier_anti_collusion():
    """Prueba que el centinela contenga la colusión y sobre-velocidad en terminal de caja."""
    sentinel = CashierAntiCollusionSentinel(max_redemptions_per_minute=3)
    t0 = 1000.0

    assert sentinel.audit_terminal_rate("caja-gama-01", current_timestamp=t0) is True
    assert sentinel.audit_terminal_rate("caja-gama-01", current_timestamp=t0 + 10) is True
    assert sentinel.audit_terminal_rate("caja-gama-01", current_timestamp=t0 + 20) is True

    # 4to canje dentro del mismo minuto -> Bloqueado
    with pytest.raises(DomainInvariantViolationError) as exc_info:
        sentinel.audit_terminal_rate("caja-gama-01", current_timestamp=t0 + 30)
    assert "Alerta Anti-Colusión" in str(exc_info.value)
    assert "excedió el límite de 3 canjes por minuto" in str(exc_info.value)


def test_cazador_service_rea_integration():
    """Prueba la integración completa de los métodos REA en CazadorApplicationService."""
    service = CazadorApplicationService()
    
    # 1. Generar QR Compacto
    compact_qr = service.generar_qr_compacto_cashea("deal-arturos-combo", "04269876543", "778899")
    assert compact_qr.startswith("SOF-V1:")

    # 2. Verificar QR Compacto en caja
    decoded = service.verificar_qr_compacto_cashea(compact_qr, terminal_id="caja-arturos-recreo-01")
    assert decoded["totp_token"] == "778899"
    assert decoded["is_valid_signature"] is True

    # 3. Evaluar regla avanzada mediante el servicio
    rule = AdvancedPromotionRule(
        rule_id="rule-locatel-hipertensos",
        rule_type=PromotionRuleType.PERCENTAGE_DISCOUNT,
        titulo="Lunes Azules Locatel",
        comercio_id="com-locatel-01",
        precio_regular_unitario_ves=120.0,
        costo_directo_unitario_ves=50.0,
        descuento_pct=20.0
    )
    res = service.evaluar_regla_promocion_avanzada(rule, cantidad_solicitada=1)
    assert res.is_applicable is True
    assert res.precio_final_oferta_ves == 96.0
    assert res.margen_bruto_final_pct == 47.92
