"""
Módulo Autónomo de Despacho Multimodal — Suite de Pruebas: Validación de Vouchers Bancarios Reales
Bancos: Banco de Venezuela (0102), Banesco (0134), Bancamiga (0172), Mercantil (0105), Provincial (0108)
Gobernanza: Universal Best Practices Engineering Rule (Pilares I, III, V y VI)
"""

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from application.voucher_parser import parse_voucher_text, BANK_CODES, VoucherParseResult
from infrastructure.ocr_backends import AppleVisionBackend

FIXTURES_DIR = os.path.join(ROOT_DIR, "tests", "fixtures")


class TestBankVouchersReal(unittest.TestCase):
    """Pruebas rigurosas de OCR y parsing con comprobantes bancarios venezolanos reales anonimizados."""

    @classmethod
    def setUpClass(cls):
        cls.vision_backend = AppleVisionBackend()
        cls.vision_available = cls.vision_backend.is_available()

    def _read_fixture_bytes(self, filename: str) -> bytes:
        path = os.path.join(FIXTURES_DIR, filename)
        self.assertTrue(os.path.exists(path), f"El archivo fixture {path} no existe")
        with open(path, "rb") as f:
            return f.read()

    def test_sudeban_bank_codes_catalog(self):
        """Valida que el catálogo oficial de códigos bancarios SUDEBAN contenga las entidades clave."""
        expected_banks = {
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
        for code, expected_name in expected_banks.items():
            self.assertIn(code, BANK_CODES, f"Falta código SUDEBAN {code}")
            self.assertEqual(BANK_CODES[code], expected_name)

    def test_bdv_voucher_ocr_and_parsing(self):
        """Valida comprobante Banco de Venezuela (0102) PagoClave / BDVenlínea."""
        if not self.vision_available:
            self.skipTest("AppleVision no disponible en este entorno")

        img_bytes = self._read_fixture_bytes("voucher_bdv.png")
        raw_text = self.vision_backend.image_to_text(img_bytes)
        result = parse_voucher_text(raw_text)

        self.assertTrue(result.is_valid_voucher)
        self.assertEqual(result.bank_code, "0102")
        self.assertEqual(result.bank_name, "Banco de Venezuela")
        self.assertEqual(result.reference_number, "0092837461")
        self.assertEqual(result.amount_ves, 1850.00)
        self.assertEqual(result.date, "19/10/2026")
        self.assertEqual(result.confidence, 1.0)

    def test_banesco_voucher_ocr_and_parsing(self):
        """Valida comprobante Banesco (0134) BanescoMóvil."""
        if not self.vision_available:
            self.skipTest("AppleVision no disponible en este entorno")

        img_bytes = self._read_fixture_bytes("voucher_banesco.png")
        raw_text = self.vision_backend.image_to_text(img_bytes)
        result = parse_voucher_text(raw_text)

        self.assertTrue(result.is_valid_voucher)
        self.assertEqual(result.bank_code, "0134")
        self.assertEqual(result.bank_name, "Banesco")
        self.assertEqual(result.reference_number, "0084729104")
        self.assertEqual(result.amount_ves, 1250.50)
        self.assertEqual(result.date, "19/10/2026")
        self.assertEqual(result.confidence, 1.0)

    def test_bancamiga_voucher_ocr_and_parsing(self):
        """Valida comprobante Bancamiga (0172) Bancamiga Suite."""
        if not self.vision_available:
            self.skipTest("AppleVision no disponible en este entorno")

        img_bytes = self._read_fixture_bytes("voucher_bancamiga.png")
        raw_text = self.vision_backend.image_to_text(img_bytes)
        result = parse_voucher_text(raw_text)

        self.assertTrue(result.is_valid_voucher)
        self.assertEqual(result.bank_code, "0172")
        self.assertEqual(result.bank_name, "Bancamiga")
        self.assertEqual(result.reference_number, "017200876543")
        self.assertEqual(result.amount_ves, 450.00)
        self.assertEqual(result.date, "19-10-2026")
        self.assertEqual(result.confidence, 1.0)

    def test_mercantil_voucher_ocr_and_parsing(self):
        """Valida comprobante Mercantil (0105) Tpago Mercantil."""
        if not self.vision_available:
            self.skipTest("AppleVision no disponible en este entorno")

        img_bytes = self._read_fixture_bytes("voucher_mercantil.png")
        raw_text = self.vision_backend.image_to_text(img_bytes)
        result = parse_voucher_text(raw_text)

        self.assertTrue(result.is_valid_voucher)
        self.assertEqual(result.bank_code, "0105")
        self.assertEqual(result.bank_name, "Mercantil")
        self.assertEqual(result.reference_number, "010500123456")
        self.assertEqual(result.amount_ves, 320.00)
        self.assertEqual(result.date, "19/10/2026")
        self.assertEqual(result.confidence, 1.0)

    def test_provincial_voucher_ocr_and_parsing(self):
        """Valida comprobante BBVA Provincial (0108) Dinero Rápido / Provinet."""
        if not self.vision_available:
            self.skipTest("AppleVision no disponible en este entorno")

        img_bytes = self._read_fixture_bytes("voucher_provincial.png")
        raw_text = self.vision_backend.image_to_text(img_bytes)
        result = parse_voucher_text(raw_text)

        self.assertTrue(result.is_valid_voucher)
        self.assertEqual(result.bank_code, "0108")
        self.assertEqual(result.bank_name, "Provincial")
        self.assertEqual(result.reference_number, "010800345678")
        self.assertEqual(result.amount_ves, 850.00)
        self.assertEqual(result.date, "19/10/2026")
        self.assertEqual(result.confidence, 1.0)

    def test_multiline_format_and_variations(self):
        """Valida formatos multilínea y variaciones tipográficas sin imágenes."""
        text_bnc = (
            "Banco Nacional de Crédito - BNC\n"
            "Comprobante Pago Móvil\n"
            "Código de Aprobación: 981273645\n"
            "Monto Total:\n"
            "Bs. 750,25\n"
            "Fecha: 2026-10-19"
        )
        r_bnc = parse_voucher_text(text_bnc)
        self.assertTrue(r_bnc.is_valid_voucher)
        self.assertEqual(r_bnc.bank_code, "0191")
        self.assertEqual(r_bnc.bank_name, "BNC Nacional de Crédito")
        self.assertEqual(r_bnc.reference_number, "981273645")
        self.assertEqual(r_bnc.amount_ves, 750.25)
        self.assertEqual(r_bnc.date, "2026-10-19")

    def test_missing_data_fails_closed(self):
        """Verifica que comprobantes incompletos fallen cerrado sin inventar valores."""
        # Solo referencia, sin monto
        r_no_amount = parse_voucher_text("Banesco Pago Móvil Ref: 12345678")
        self.assertFalse(r_no_amount.is_valid_voucher)
        self.assertIsNone(r_no_amount.amount_ves)
        self.assertIn("amount_ves", r_no_amount.missing_fields)

        # Solo monto, sin referencia
        r_no_ref = parse_voucher_text("Banco de Venezuela Monto Bs 500,00")
        self.assertFalse(r_no_ref.is_valid_voucher)
        self.assertIsNone(r_no_ref.reference_number)
        self.assertIn("reference_number", r_no_ref.missing_fields)


if __name__ == "__main__":
    unittest.main()
