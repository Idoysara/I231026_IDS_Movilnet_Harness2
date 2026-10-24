"""
Invariantes Matemáticas y Guardas de Dominio para Cazador de Ofertas Movilnet.
Alineadas con la Directiva Invariante de Viabilidad Financiera (Díaz Robisco)
y la Regla Polimórfica de Activos (Pentarquía IDS_CORE).
"""
import re
from typing import Tuple

class DomainInvariantViolationError(Exception):
    """Lanzada cuando una operación viola una regla o guarda matemática del dominio."""
    pass

class CazadorInvariants:
    MIN_GROSS_MARGIN_PCT = 35.0  # Invariante II: Margen Bruto >= 35%
    MAX_RADAR_DISTANCE_METERS = 3000.0  # Invariante III: Anillo 3 Máximo 3km
    VALID_CARRIER_PREFIXES = ("0416", "0426", "58416", "58426", "+58416", "+58426")
    TELCO_SPLIT_PCT = 20.0  # 20% Movilnet
    MERCHANT_SPLIT_PCT = 80.0  # 80% Comercio / Plataforma

    # Invariante VII: Cero Fricción Espacial para Anunciantes / Comercios
    DEFAULT_SMART_RADIUS_METERS = 500.0  # 500m estándar cinemático / peatonal
    MIN_MANUAL_RADIUS_METERS = 50.0  # Previene radios <50m que a 40km/h duran <1.8s
    MAX_METROPOLITAN_RADIUS_METERS = 50000.0  # Cobertura metropolitana Run-of-Network


    @classmethod
    def validar_margen_bruto(cls, precio_oferta: float, costo_directo: float) -> Tuple[bool, float]:
        """
        Invariante II: Margen Bruto = ((Precio_Oferta - Costo_Directo) / Precio_Oferta) >= 35%
        Evita que los comercios vendan a pérdida o erosionen la viabilidad operativa.
        """
        if precio_oferta <= 0:
            raise DomainInvariantViolationError(
                f"Precio de oferta inválido ({precio_oferta} VES). Debe ser estrictamente positivo."
            )
        if costo_directo < 0:
            raise DomainInvariantViolationError(
                f"Costo directo inválido ({costo_directo} VES). No puede ser negativo."
            )
        
        margen = ((precio_oferta - costo_directo) / precio_oferta) * 100.0
        if margen < cls.MIN_GROSS_MARGIN_PCT:
            raise DomainInvariantViolationError(
                f"Violación de Invariante II: Margen bruto de {margen:.2f}% es inferior al umbral mínimo del {cls.MIN_GROSS_MARGIN_PCT}% requerido."
            )
        return True, round(margen, 2)

    @classmethod
    def validar_distancia_radar(cls, distancia_m: float) -> bool:
        """
        Invariante III: El radar geoespacial clasifica ofertas dentro de un radio máximo de 3000m (3km).
        """
        if distancia_m < 0:
            raise DomainInvariantViolationError(
                f"Distancia geodésica no puede ser negativa ({distancia_m}m)."
            )
        if distancia_m > cls.MAX_RADAR_DISTANCE_METERS:
            raise DomainInvariantViolationError(
                f"Distancia de {distancia_m:.1f}m excede el radio urbano máximo de {cls.MAX_RADAR_DISTANCE_METERS}m (Zona 3)."
            )
        return True

    @classmethod
    def validar_msisdn_movilnet(cls, msisdn: str) -> str:
        """
        Guarda de Carrier Billing: Valida que el número pertenezca a la red Movilnet (0416 o 0426).
        """
        clean_num = re.sub(r"[\s\-\(\)\+]", "", msisdn.strip())
        es_valido = any(clean_num.startswith(p.replace("+", "")) for p in cls.VALID_CARRIER_PREFIXES)
        if not es_valido:
            raise DomainInvariantViolationError(
                f"Número MSISDN '{msisdn}' no pertenece a la operadora Movilnet (prefijos válidos: 0416, 0426)."
            )
        return clean_num

    @classmethod
    def validar_idempotencia_key(cls, idempotency_key: str) -> str:
        """
        Guarda de Idempotencia: Obliga a que toda transacción de cobro o reserva posea una clave no vacía.
        """
        if not idempotency_key or len(idempotency_key.strip()) < 8:
            raise DomainInvariantViolationError(
                "La clave de idempotencia (idempotency_key) es obligatoria y debe tener al menos 8 caracteres."
            )
        return idempotency_key.strip()

    @classmethod
    def calcular_split_transaccional(cls, monto_total_ves: float) -> Tuple[float, float]:
        """
        Pilar 6: Split transaccional (20% Telco Movilnet / 80% Comercio & Plataforma).
        """
        if monto_total_ves <= 0:
            raise DomainInvariantViolationError(
                f"Monto total para split debe ser mayor a 0 ({monto_total_ves} VES)."
            )
        comision_telco = round(monto_total_ves * (cls.TELCO_SPLIT_PCT / 100.0), 2)
        neto_comercio = round(monto_total_ves - comision_telco, 2)
        return comision_telco, neto_comercio

    @classmethod
    def validar_grounding_oferta_b2c(cls, oferta_id: str, ids_verificados: set) -> bool:
        """
        Invariante de Cero Alucinación B2C:
        Queda terminantemente prohibido a cualquier LLM, motor o API inventar o proponer
        ofertas, precios o comercios sintéticos que no residan físicamente en el catálogo auditado.
        Si la oferta no está en la base de datos real, se rechaza de inmediato (Fallo Limpio).
        """
        if not oferta_id or oferta_id.strip() not in ids_verificados:
            raise DomainInvariantViolationError(
                f"Violación de Invariante de Grounding B2C: La oferta '{oferta_id}' no existe en el catálogo real verificado. "
                f"Prohibida la alucinación o invención de ofertas sin respaldo físico en base de datos."
            )
        return True

    @classmethod
    def validar_radio_comercio(cls, radio_m: float) -> float:
        """
        Valida que un radio manual no sea peligrosamente pequeño (< 50m).
        Un vehículo a 40 km/h recorre 20 metros en 1.8 segundos, haciendo inútil el anuncio.
        """
        if radio_m < cls.MIN_MANUAL_RADIUS_METERS:
            raise DomainInvariantViolationError(
                f"Radio espacial inválido ({radio_m:.1f}m). Para evitar spots inaudibles (<1.8s a 40km/h), el radio mínimo debe ser >= {cls.MIN_MANUAL_RADIUS_METERS}m."
            )
        return float(radio_m)

