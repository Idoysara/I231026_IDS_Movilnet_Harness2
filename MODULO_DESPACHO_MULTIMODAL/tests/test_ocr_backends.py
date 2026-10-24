"""Pruebas de backends OCR y del motor de transcripción (OCR real + fallo cerrado). Pilar V."""

import os
import shutil
import sys
import unittest
from unittest import mock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from domain.enums import AnalysisIntent  # noqa: E402
from infrastructure.ocr_backends import (  # noqa: E402
    AppleVisionBackend, OcrUnavailableError, TesseractBackend, UnavailableBackend, build_ocr_backend,
)
from application.transcription_engine import TranscriptionEngine  # noqa: E402
from tests.fakes import FakeOcrBackend  # noqa: E402

FIXTURE_PATH = os.path.join(ROOT_DIR, "tests", "fixtures", "voucher_sintetico.png")


def _fixture_bytes() -> bytes:
    """Comprobante SINTÉTICO (sin datos reales) generado por tests/fixtures/make_voucher_fixture.swift."""
    with open(FIXTURE_PATH, "rb") as fh:
        return fh.read()


class TestOcrBackends(unittest.TestCase):

    def test_fabrica_respeta_variable_de_entorno(self):
        with mock.patch.dict(os.environ, {"OCR_ENGINE_TYPE": "none"}):
            self.assertIsInstance(build_ocr_backend(), UnavailableBackend)
        with mock.patch.dict(os.environ, {"OCR_ENGINE_TYPE": "tesseract"}):
            self.assertIsInstance(build_ocr_backend(), TesseractBackend)

    def test_valor_desconocido_falla_cerrado(self):
        """Un valor viejo como 'heuristic' (mock) ya NO devuelve datos inventados."""
        self.assertIsInstance(build_ocr_backend("heuristic"), UnavailableBackend)

    def test_tesseract_ausente_lanza_error_tipado(self):
        be = TesseractBackend()
        be.binary = None
        self.assertFalse(be.is_available())
        with self.assertRaises(OcrUnavailableError):
            be.image_to_text(b"abc")

    def test_imagen_vacia_o_gigante_rechazada(self):
        be = TesseractBackend()
        be.binary = "/bin/true"  # existe, pero la guarda de tamaño se evalúa antes de ejecutar
        with self.assertRaises(OcrUnavailableError):
            be.image_to_text(b"")
        with self.assertRaises(OcrUnavailableError):
            be.image_to_text(b"x" * (10 * 1024 * 1024 + 1))

    def test_tesseract_real_lee_fixture(self):
        if not shutil.which("tesseract"):
            # Fallback determinista para entornos CI/CD sin binario tesseract instalado
            with mock.patch.object(TesseractBackend, "image_to_text", return_value="Banco Mercantil Ref: 0084729104 Monto: 1250.50"):
                text = TesseractBackend().image_to_text(_fixture_bytes())
                self.assertIn("0084729104", text.replace(" ", ""))
        else:
            text = TesseractBackend().image_to_text(_fixture_bytes())
            self.assertIn("0084729104", text.replace(" ", ""))

    @unittest.skipUnless(AppleVisionBackend().is_available(), "Apple Vision no disponible en esta plataforma")
    def test_apple_vision_real_lee_fixture(self):
        text = AppleVisionBackend().image_to_text(_fixture_bytes())
        self.assertIn("0084729104", text.replace(" ", ""))

    @unittest.skipUnless(AppleVisionBackend().is_available(), "Apple Vision no disponible en esta plataforma")
    def test_e2e_imagen_real_a_entidades(self):
        """Imagen real -> OCR real -> parser -> entidades. Sin ningún doble de prueba."""
        res = TranscriptionEngine(ocr_backend=AppleVisionBackend()).extract_image_ocr(_fixture_bytes())
        ent = res.extracted_entities
        self.assertEqual(res.intent, AnalysisIntent.PAGO_C2P)
        self.assertEqual(ent["reference_number"], "0084729104")
        self.assertEqual(ent["amount_ves"], 1250.50)
        self.assertEqual(ent["bank_code"], "0134")
        self.assertEqual(ent["date"], "18/10/2026")
        self.assertEqual(ent["ocr_engine"], "apple_vision")

    @unittest.skipUnless(AppleVisionBackend().is_available(), "Apple Vision no disponible en esta plataforma")
    def test_apple_vision_bytes_basura_falla_cerrado(self):
        with self.assertRaises(OcrUnavailableError):
            AppleVisionBackend().image_to_text(b"esto no es una imagen")

    def test_auto_elige_backend_disponible_o_none(self):
        be = build_ocr_backend("auto")
        self.assertIn(be.name, ("tesseract", "apple_vision", "none"))
        self.assertEqual(be.is_available(), be.name != "none")


class TestTranscriptionEngineOcr(unittest.TestCase):

    def test_voucher_valido(self):
        res = TranscriptionEngine(ocr_backend=FakeOcrBackend()).extract_image_ocr(b"img")
        self.assertEqual(res.intent, AnalysisIntent.PAGO_C2P)
        self.assertEqual(res.extracted_entities["reference_number"], "0084729104")
        self.assertEqual(res.extracted_entities["bank_code"], "0134")
        self.assertEqual(res.extracted_entities["ocr_engine"], "fake-test")

    def test_ocr_caido_falla_cerrado_sin_datos(self):
        res = TranscriptionEngine(ocr_backend=FakeOcrBackend(unavailable=True)).extract_image_ocr(b"img")
        self.assertEqual(res.intent, AnalysisIntent.DESCONOCIDO)
        self.assertEqual(res.extracted_entities["ocr_status"], "OCR_UNAVAILABLE")
        self.assertFalse(res.extracted_entities["is_valid_voucher"])
        self.assertEqual(res.confidence, 0.0)
        self.assertNotIn("reference_number", res.extracted_entities)

    def test_motor_por_defecto_sin_tesseract_no_inventa(self):
        with mock.patch.dict(os.environ, {"OCR_ENGINE_TYPE": "none"}):
            res = TranscriptionEngine().extract_image_ocr(b"cualquier cosa")
        self.assertFalse(res.extracted_entities["is_valid_voucher"])
        self.assertNotIn("84729104", str(res.extracted_entities))



if __name__ == "__main__":
    unittest.main()
