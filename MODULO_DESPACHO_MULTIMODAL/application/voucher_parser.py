"""
Módulo Autónomo de Despacho Multimodal — Capa de Aplicación: Parser de Comprobantes (Pago Móvil C2P)
Gobernanza: Universal Best Practices Engineering Rule (Pilares I, II, III y V)

Función PURA: convierte el texto crudo devuelto por un motor OCR en entidades estructuradas
y validadas. No hace E/S, no depende de ningún motor OCR. Regla de oro: NUNCA inventar datos;
si un campo no está en el texto, no aparece en el resultado.

Ejecución autónoma:
    python3 application/voucher_parser.py --test
    python3 application/voucher_parser.py --text "Banco Banesco Ref: 123456789 Monto Bs. 1.250,50"
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Códigos SUDEBAN oficiales de bancos venezolanos (Superintendencia de las Instituciones del Sector Bancario)
BANK_CODES: Dict[str, str] = {
    "0102": "Banco de Venezuela",
    "0104": "Venezolano de Crédito",
    "0105": "Mercantil",
    "0108": "Provincial",
    "0114": "Bancaribe",
    "0115": "Exterior",
    "0128": "Banco Caroní",
    "0134": "Banesco",
    "0137": "Sofitasa",
    "0138": "Banco Plaza",
    "0146": "Bangente",
    "0151": "BFC Banco Fondo Común",
    "0156": "100% Banco",
    "0157": "DelSur",
    "0163": "Banco del Tesoro",
    "0166": "Banco Agrícola de Venezuela",
    "0168": "Bancrecer",
    "0169": "Mi Banco",
    "0171": "Banco Activo",
    "0172": "Bancamiga",
    "0173": "Banco Internacional de Desarrollo",
    "0174": "Banplus",
    "0175": "Banco Bicentenario",
    "0177": "Banfanb",
    "0191": "BNC Nacional de Crédito",
}

# Palabras clave en el texto -> código bancario SUDEBAN (ordenadas de mayor a menor especificidad)
_BANK_KEYWORDS = [
    # Banco de Venezuela (0102)
    ("banco de venezuela", "0102"), ("bdvenlínea", "0102"), ("bdvenlinea", "0102"),
    ("bdvapp", "0102"), ("bdv en línea", "0102"), ("bdv en linea", "0102"),
    ("pagoclave", "0102"), ("pago clave", "0102"), ("bdv", "0102"),
    # Venezolano de Crédito (0104)
    ("venezolano de crédito", "0104"), ("venezolano de credito", "0104"), ("vencred", "0104"),
    # Mercantil (0105)
    ("mercantil", "0105"), ("tpago", "0105"), ("t-pago", "0105"),
    # BBVA Provincial (0108)
    ("bbva provincial", "0108"), ("provincial", "0108"), ("bbva", "0108"),
    ("provinet", "0108"), ("dinero rápido", "0108"), ("dinero rapido", "0108"),
    # Bancaribe (0114)
    ("bancaribe", "0114"), ("mi pago bancaribe", "0114"),
    # Exterior (0115)
    ("exterior", "0115"),
    # Caroní (0128)
    ("caroní", "0128"), ("caroni", "0128"),
    # Banesco (0134)
    ("banesco", "0134"), ("multipagos banesco", "0134"),
    # Sofitasa (0137)
    ("sofitasa", "0137"),
    # Banco Plaza (0138)
    ("banco plaza", "0138"),
    # Bangente (0146)
    ("bangente", "0146"),
    # Fondo Común (0151)
    ("fondo común", "0151"), ("fondo comun", "0151"), ("bfc", "0151"),
    # 100% Banco (0156)
    ("100% banco", "0156"), ("100%banco", "0156"),
    # DelSur (0157)
    ("delsur", "0157"), ("del sur", "0157"),
    # Banco del Tesoro (0163)
    ("del tesoro", "0163"), ("banco del tesoro", "0163"), ("tesoro", "0163"),
    # Agrícola (0166)
    ("agrícola de venezuela", "0166"), ("agricola de venezuela", "0166"),
    # Bancrecer (0168)
    ("bancrecer", "0168"),
    # Mi Banco (0169)
    ("mi banco", "0169"), ("mibanco", "0169"),
    # Banco Activo (0171)
    ("banco activo", "0171"),
    # Bancamiga (0172)
    ("bancamiga", "0172"),
    # Banco Internacional de Desarrollo (0173)
    ("banco internacional de desarrollo", "0173"),
    # Banplus (0174)
    ("banplus", "0174"),
    # Bicentenario (0175)
    ("bicentenario", "0175"),
    # Banfanb (0177)
    ("banfanb", "0177"),
    # BNC (0191)
    ("bnc", "0191"), ("nacional de crédito", "0191"), ("nacional de credito", "0191"),
]

# Expresiones regulares refinadas para Referencia
_REF_PATTERNS = [
    # 1. Prefijo con identificadores frecuentes (ej: Referencia: 12345678, N° Operación: 123456)
    re.compile(
        r"(?:referencia|ref\.?|n[uú]m(?:ero)?\.?\s*(?:de\s*)?(?:operaci[oó]n|ref(?:erencia)?|comprobante|transacci[oó]n|aprobaci[oó]n|secuencia)|"
        r"n[ro°º]\.?\s*(?:de\s*)?(?:operaci[oó]n|ref(?:erencia)?|comprobante|transacci[oó]n|aprobaci[oó]n|secuencia)|"
        r"operaci[oó]n|comprobante|transacci[oó]n|aprobaci[oó]n|secuencia)\s*[:#.\-ºo°]*\s*([0-9]{6,20})",
        re.IGNORECASE,
    ),
    # 2. Etiqueta de referencia con salto de línea (ej: Referencia \n 12345678)
    re.compile(
        r"(?:referencia|ref\.?|n[uú]mero\s+de\s+operaci[oó]n|nro\.?\s*de\s*operaci[oó]n|operaci[oó]n|aprobaci[oó]n|comprobante)\s*[:#.\-ºo°]*\s*\n\s*([0-9]{6,20})",
        re.IGNORECASE,
    ),
    # 3. Código o secuencia bancaria típica
    re.compile(
        r"(?:c[oó]digo\s+(?:de\s+)?(?:referencia|operaci[oó]n|aprobaci[oó]n))\s*[:#.\-ºo°]*\s*([0-9]{6,20})",
        re.IGNORECASE,
    ),
]

# Expresiones regulares refinadas para Monto
_AMOUNT_PATTERNS = [
    # 1. Prefijo de monto (ej: Monto: Bs. 1.250,50 o Monto pagado: 250,00)
    re.compile(
        r"(?:monto(?:\s+(?:de\s+la\s+operaci[oó]n|pagado|debitado|total))?|importe|total(?:\s+pagado)?|bs\.?|bol[ií]vares|ves)\s*[:.]?\s*(?:bs\.?|ves)?\s*([0-9][0-9.,]*[0-9]|[0-9])",
        re.IGNORECASE,
    ),
    # 2. Salto de línea entre Monto y el valor (ej: Monto:\nBs. 1.500,00)
    re.compile(
        r"(?:monto|importe|total)\s*[:.]?\s*\n\s*(?:bs\.?|ves)?\s*([0-9][0-9.,]*[0-9]|[0-9])",
        re.IGNORECASE,
    ),
    # 3. Valor numérico con decimales seguido de Bs o VES (ej: 1.250,50 Bs o 250,00 VES)
    re.compile(
        r"\b([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+[.,][0-9]{2})\s*(?:bs\.?|bol[ií]vares|ves)\b",
        re.IGNORECASE,
    ),
]

# Expresiones para fechas (estándar venezolano DD/MM/AAAA y formato ISO AAAA-MM-DD)
_DATE_PATTERNS = [
    re.compile(r"\b(0?[1-9]|[12][0-9]|3[01])[/\-.](0?[1-9]|1[0-2])[/\-.](20[0-9]{2}|[0-9]{2})\b"),
    re.compile(r"\b(20[0-9]{2})[/\-.](0?[1-9]|1[0-2])[/\-.](0?[1-9]|[12][0-9]|3[01])\b"),
]

_BANK_CODE_RE = re.compile(r"\b(0[0-9]{3})\b")


@dataclass
class VoucherParseResult:
    """Resultado tipado del análisis de un comprobante a partir de texto OCR."""
    is_valid_voucher: bool
    confidence: float
    bank_code: Optional[str] = None
    bank_name: Optional[str] = None
    reference_number: Optional[str] = None
    amount_ves: Optional[float] = None
    date: Optional[str] = None
    currency: str = "VES"
    missing_fields: List[str] = field(default_factory=list)

    def to_entities(self) -> Dict[str, object]:
        """Solo incluye campos realmente encontrados (cero datos inventados)."""
        out: Dict[str, object] = {"is_valid_voucher": self.is_valid_voucher, "currency": self.currency}
        for key in ("bank_code", "bank_name", "reference_number", "amount_ves", "date"):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        if self.missing_fields:
            out["missing_fields"] = list(self.missing_fields)
        return out


def parse_amount(raw: str) -> Optional[Decimal]:
    """
    Interpreta montos en formato venezolano o anglosajón:
      '1.250,50' -> 1250.50 | '250,00' -> 250.00 | '250.00' -> 250.00 | '1.250' -> 1250 | '1,250.50' -> 1250.50
    Devuelve None si no es un monto válido y positivo.
    """
    s = raw.strip().strip(".,")
    if not s or not re.fullmatch(r"[0-9][0-9.,]*", s):
        return None
    has_dot, has_comma = "." in s, "," in s
    try:
        if has_dot and has_comma:
            decimal_sep = "," if s.rfind(",") > s.rfind(".") else "."
            thousands_sep = "." if decimal_sep == "," else ","
            s = s.replace(thousands_sep, "").replace(decimal_sep, ".")
        elif has_comma:
            head, _, tail = s.rpartition(",")
            s = head.replace(",", "") + "." + tail if len(tail) in (1, 2) else s.replace(",", "")
        elif has_dot:
            head, _, tail = s.rpartition(".")
            s = s.replace(".", "") if (len(tail) == 3 and head) else s
        value = Decimal(s)
    except InvalidOperation:
        return None
    return value if value > 0 else None


def _detect_bank(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Detecta el banco por código SUDEBAN de 4 dígitos o por palabras clave oficiales."""
    lowered = text.lower()
    # 1. Búsqueda por código numérico directo de 4 dígitos
    for code in _BANK_CODE_RE.findall(text):
        if code in BANK_CODES:
            return code, BANK_CODES[code]
    # 2. Búsqueda por palabras clave oficiales
    for keyword, code in _BANK_KEYWORDS:
        if keyword in lowered:
            return code, BANK_CODES[code]
    return None, None


def _extract_reference(text: str) -> Optional[str]:
    """Extrae el número de referencia probando la jerarquía de patrones."""
    for pattern in _REF_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def _extract_amount(text: str) -> Optional[float]:
    """Extrae el monto monetario en Bolívares probando los patrones definidos."""
    for pattern in _AMOUNT_PATTERNS:
        for m in pattern.finditer(text):
            parsed = parse_amount(m.group(1))
            if parsed is not None:
                return float(parsed)
    return None


def _extract_date(text: str) -> Optional[str]:
    """Extrae la fecha de operación en formato venezolano o ISO."""
    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def parse_voucher_text(text: str) -> VoucherParseResult:
    """
    Extrae y valida los campos de un comprobante de Pago Móvil C2P.
    Invariante: Un comprobante solo es válido si contiene Referencia Y Monto positivo.
    """
    if not text or not text.strip():
        return VoucherParseResult(False, 0.0, missing_fields=["reference_number", "amount_ves"])

    reference = _extract_reference(text)
    amount = _extract_amount(text)
    bank_code, bank_name = _detect_bank(text)
    date = _extract_date(text)

    missing = [name for name, val in (("reference_number", reference), ("amount_ves", amount)) if val is None]
    confidence = round(
        (0.40 if reference else 0) + (0.35 if amount is not None else 0)
        + (0.15 if bank_code else 0) + (0.10 if date else 0), 2
    )
    return VoucherParseResult(
        is_valid_voucher=not missing,
        confidence=confidence,
        bank_code=bank_code,
        bank_name=bank_name,
        reference_number=reference,
        amount_ves=amount,
        date=date,
        missing_fields=missing,
    )


def _self_test() -> None:
    """Auto-verificación formal con aserciones rigurosas."""
    # 1. Parsing de montos
    assert parse_amount("1.250,50") == Decimal("1250.50")
    assert parse_amount("250,00") == Decimal("250.00")
    assert parse_amount("250.00") == Decimal("250.00")
    assert parse_amount("1.250") == Decimal("1250")
    assert parse_amount("1,250.50") == Decimal("1250.50")
    assert parse_amount("0") is None and parse_amount("abc") is None and parse_amount("") is None

    # 2. Banco de Venezuela (BDV)
    bdv_text = (
        "BDVenlínea\n"
        "Comprobante de Pago Móvil BDV\n"
        "Operación: 0092837461\n"
        "Monto: Bs. 1.850,00\n"
        "Fecha: 19/10/2026\n"
        "Banco Emisor: 0102 Banco de Venezuela"
    )
    r_bdv = parse_voucher_text(bdv_text)
    assert r_bdv.is_valid_voucher is True
    assert r_bdv.bank_code == "0102"
    assert r_bdv.reference_number == "0092837461"
    assert r_bdv.amount_ves == 1850.00
    assert r_bdv.confidence == 1.0

    # 3. Banesco
    banesco_text = (
        "BanescoMóvil - Recibo de Pago Móvil\n"
        "Número de Referencia: 0084729104\n"
        "Monto: Bs. 1.250,50\n"
        "Fecha: 19/10/2026"
    )
    r_banesco = parse_voucher_text(banesco_text)
    assert r_banesco.is_valid_voucher is True
    assert r_banesco.bank_code == "0134"
    assert r_banesco.reference_number == "0084729104"
    assert r_banesco.amount_ves == 1250.50

    # 4. Bancamiga
    bancamiga_text = (
        "Bancamiga Suite\n"
        "Nro. Referencia: 017200876543\n"
        "Monto de la Operación: Bs. 450,00\n"
        "Fecha: 19-10-2026"
    )
    r_bancamiga = parse_voucher_text(bancamiga_text)
    assert r_bancamiga.is_valid_voucher is True
    assert r_bancamiga.bank_code == "0172"
    assert r_bancamiga.reference_number == "017200876543"
    assert r_bancamiga.amount_ves == 450.00

    # 5. Mercantil
    mercantil_text = (
        "Tpago Mercantil\n"
        "Número de Referencia: 010500123456\n"
        "Total pagado: 320,00 Bs.\n"
        "Fecha: 19/10/2026"
    )
    r_mercantil = parse_voucher_text(mercantil_text)
    assert r_mercantil.is_valid_voucher is True
    assert r_mercantil.bank_code == "0105"
    assert r_mercantil.reference_number == "010500123456"
    assert r_mercantil.amount_ves == 320.00

    # 6. BBVA Provincial
    provincial_text = (
        "BBVA Provincial - Dinero Rápido\n"
        "N° Operación: 010800345678\n"
        "Importe: 850,00 VES\n"
        "Fecha: 19/10/2026"
    )
    r_provincial = parse_voucher_text(provincial_text)
    assert r_provincial.is_valid_voucher is True
    assert r_provincial.bank_code == "0108"
    assert r_provincial.reference_number == "010800345678"
    assert r_provincial.amount_ves == 850.00

    # 7. Formato multilínea con salto de línea
    multiline_text = (
        "Comprobante Banesco\n"
        "Referencia:\n"
        "9988776655\n"
        "Monto:\n"
        "Bs. 500,00\n"
        "Fecha: 19/10/2026"
    )
    r_ml = parse_voucher_text(multiline_text)
    assert r_ml.is_valid_voucher is True
    assert r_ml.reference_number == "9988776655"
    assert r_ml.amount_ves == 500.00

    # 8. Negativo: sin referencia o sin monto (nunca inventar)
    r_invalid = parse_voucher_text("Pago Móvil BDV Monto Bs. 100,00")
    assert not r_invalid.is_valid_voucher
    assert r_invalid.reference_number is None

    print("voucher_parser: auto-verificación ampliada con 5 bancos reales OK")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description="Parser autónomo de comprobantes Pago Móvil C2P")
    cli.add_argument("--test", action="store_true", help="Ejecuta la auto-verificación")
    cli.add_argument("--text", type=str, help="Texto OCR a analizar")
    args = cli.parse_args()
    if args.test:
        _self_test()
    elif args.text:
        print(json.dumps(parse_voucher_text(args.text).to_entities(), ensure_ascii=False, indent=2))
    else:
        cli.print_help()
