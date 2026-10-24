"""
core/phone_migration_models.py
==============================================================================
Dominio Puro: Modelos Tipados e Invariantes para Migración Universal de Líneas
Cumple: Pilares I, III y VI de Excelencia Técnica & Protocolo Decagonal.
==============================================================================
"""

from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Any
from enum import Enum


class CarrierOperator(str, Enum):
    """Operadoras según el plan de numeración CONATEL."""
    MOVILNET = "MOVILNET"
    MOVISTAR = "MOVISTAR"
    DIGITEL = "DIGITEL"
    DESCONOCIDA = "DESCONOCIDA"


@dataclass(frozen=True)
class PhoneDescriptor:
    """
    Descriptor inmutable de una línea telefónica con todas sus representaciones
    normalizadas canónicas en la arquitectura Movilnet Core.
    """
    raw_input: str
    clean_digits: str             # Ej: 584241533712 o 04241533712
    national_with_zero: str       # Ej: 04241533712
    national_formatted: str       # Ej: 0424-1533712
    international_e164: str       # Ej: +58 424 153 3712
    international_digits: str     # Ej: 584241533712
    international_0058: str       # Ej: 00584241533712
    whatsapp_jid: str             # Ej: 584241533712@s.whatsapp.net
    prefix_area: str              # Ej: 0424
    carrier: CarrierOperator
    session_token_suffix: str     # Ej: 1533712 (últimos 7-8 dígitos)

    @classmethod
    def from_string(cls, phone_str: str) -> PhoneDescriptor:
        """Fabrica un PhoneDescriptor a partir de cualquier cadena telefónica."""
        digits = re.sub(r"[^\d]", "", str(phone_str or ""))
        
        # Normalizar a internacional 58
        if digits.startswith("0058") and len(digits) == 14:
            clean_int = digits[2:]
        elif digits.startswith("58") and len(digits) == 12:
            clean_int = digits
        elif digits.startswith("0") and len(digits) == 11:
            clean_int = "58" + digits[1:]
        elif len(digits) == 10:
            clean_int = "58" + digits
        else:
            clean_int = digits

        # Formato nacional
        if clean_int.startswith("58") and len(clean_int) == 12:
            nat_zero = "0" + clean_int[2:]
            nat_fmt = f"{nat_zero[:4]}-{nat_zero[4:]}"
            prefix = nat_zero[:4]
            e164 = f"+58 {clean_int[2:5]} {clean_int[5:]}"
        elif digits.startswith("0") and len(digits) == 11:
            nat_zero = digits
            nat_fmt = f"{digits[:4]}-{digits[4:]}"
            prefix = digits[:4]
            e164 = f"+58 {digits[1:4]} {digits[4:]}"
        else:
            nat_zero = digits
            nat_fmt = digits
            prefix = digits[:4] if len(digits) >= 4 else "0000"
            e164 = f"+{digits}"

        # Clasificación CONATEL
        if prefix in ("0416", "0426"):
            carrier = CarrierOperator.MOVILNET
        elif prefix in ("0414", "0424"):
            carrier = CarrierOperator.MOVISTAR
        elif prefix in ("0412",):
            carrier = CarrierOperator.DIGITEL
        else:
            carrier = CarrierOperator.DESCONOCIDA

        session_suffix = clean_int[-7:] if len(clean_int) >= 7 else clean_int

        return cls(
            raw_input=phone_str,
            clean_digits=digits,
            national_with_zero=nat_zero,
            national_formatted=nat_fmt,
            international_e164=e164,
            international_digits=clean_int,
            international_0058=f"00{clean_int}",
            whatsapp_jid=f"{clean_int}@s.whatsapp.net",
            prefix_area=prefix,
            carrier=carrier,
            session_token_suffix=session_suffix,
        )

    @property
    def is_movilnet_subscriber(self) -> bool:
        """Indica si la línea pertenece estrictamente a los prefijos de abonados Movilnet (0416/0426)."""
        return self.prefix_area in ("0416", "0426")

    def get_search_patterns(self) -> List[str]:
        """Retorna lista de expresiones de búsqueda para este número."""
        return [
            re.escape(self.national_formatted),
            re.escape(self.national_with_zero),
            re.escape(self.international_0058),
            re.escape(self.international_digits),
            re.escape(self.whatsapp_jid),
            re.escape(self.international_e164),
        ]


@dataclass
class ComponentImpactDetail:
    """Detalle de impacto en un archivo o nodo específico."""
    target_id: str             # Ruta de archivo o Nombre de Nodo n8n
    layer: str                 # 'CORE_MODULE', 'N8N_WORKFLOW', 'UI_FRONTEND', 'DATABASE', 'DOCKER_ENV', 'SCRIPT'
    matches_found: int
    lines_affected: List[int] = field(default_factory=list)
    replacements_preview: List[str] = field(default_factory=list)
    status: str = "PENDING"    # PENDING, REPLACED, SKIPPED, ERROR
    error_message: Optional[str] = None


@dataclass
class MigrationPlan:
    """Plan de migración atómico pre-calculado con rollback garantizado."""
    plan_id: str
    timestamp_utc: str
    from_phone: PhoneDescriptor
    to_phone: PhoneDescriptor
    bot_name: str
    total_files_analyzed: int
    total_matches_detected: int
    components: List[ComponentImpactDetail] = field(default_factory=list)
    backup_snapshot_dir: Optional[str] = None
    dry_run: bool = True
    executed: bool = False
    success: bool = False
    sha256_seal: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["from_phone"] = asdict(self.from_phone)
        d["to_phone"] = asdict(self.to_phone)
        d["from_phone"]["carrier"] = self.from_phone.carrier.value
        d["to_phone"]["carrier"] = self.to_phone.carrier.value
        return d
