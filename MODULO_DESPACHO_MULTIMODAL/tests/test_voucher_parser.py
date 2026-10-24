"""Pruebas unitarias del parser de comprobantes (función pura). Pilar V."""

import os
import sys
import unittest
from decimal import Decimal

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from application.voucher_parser import parse_amount, parse_voucher_text  # noqa: E402


class TestParseAmount(unittest.TestCase):

    def test_formatos_validos(self):
        casos = {
            "1.250,50": "1250.50", "250,00": "250.00", "250.00": "250.00",
            "1.250": "1250", "1,250.50": "1250.50", "12.345.678,90": "12345678.90", "7": "7",
        }
        for raw, esperado in casos.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_amount(raw), Decimal(esperado))

    def test_formatos_invalidos(self):
        for raw in ["", "abc", "0", "0,00", "-5", "1.2.x"]:
            with self.subTest(raw=raw):
                self.assertIsNone(parse_amount(raw))


class TestParseVoucher(unittest.TestCase):

    def test_comprobante_completo(self):
        r = parse_voucher_text("Pago Móvil Banesco\nReferencia: 0084729104\nMonto: Bs. 1.250,50\nFecha: 18/10/2026")
        self.assertTrue(r.is_valid_voucher)
        self.assertEqual(r.reference_number, "0084729104")
        self.assertEqual(r.amount_ves, 1250.50)
        self.assertEqual(r.bank_code, "0134")
        self.assertEqual(r.date, "18/10/2026")
        self.assertEqual(r.confidence, 1.0)

    def test_sin_referencia_no_inventa(self):
        r = parse_voucher_text("Banesco Monto Bs. 100,00")
        self.assertFalse(r.is_valid_voucher)
        self.assertIsNone(r.reference_number)
        self.assertNotIn("reference_number", r.to_entities())
        self.assertIn("reference_number", r.missing_fields)

    def test_sin_monto_no_inventa(self):
        r = parse_voucher_text("Referencia: 123456789 Banco Mercantil")
        self.assertFalse(r.is_valid_voucher)
        self.assertIsNone(r.amount_ves)

    def test_texto_vacio_o_basura(self):
        for texto in ["", "   ", "foto de un gato", "12345"]:
            with self.subTest(texto=texto):
                r = parse_voucher_text(texto)
                self.assertFalse(r.is_valid_voucher)

    def test_ningun_valor_fijo_historico(self):
        """Regresión H-03: los valores del mock antiguo jamás deben aparecer si no están en el texto."""
        r = parse_voucher_text("texto cualquiera sin datos")
        self.assertNotIn("84729104", str(r.to_entities()))
        self.assertNotIn("250.0", str(r.to_entities()))


if __name__ == "__main__":
    unittest.main()
