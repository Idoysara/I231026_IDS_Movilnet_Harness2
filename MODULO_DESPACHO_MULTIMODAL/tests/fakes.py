"""Dobles de prueba compartidos por la suite. NUNCA se usan en código de producción."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from infrastructure.ocr_backends import OcrUnavailableError  # noqa: E402
from infrastructure.stt_backends import SttUnavailableError, SttResult  # noqa: E402

VALID_VOUCHER_TEXT = (
    "Pago Móvil Banesco\nReferencia: 0084729104\nMonto: Bs. 250,00\nFecha: 18/10/2026"
)
VALID_AUDIO_TEXT = "Hola Movilnet, deseo recargar mi saldo de la línea con pago móvil."


class FakeOcrBackend:
    """Backend OCR determinista: devuelve un texto fijo o simula caída del motor."""

    name = "fake-test"

    def __init__(self, text: str = VALID_VOUCHER_TEXT, unavailable: bool = False):
        self.text = text
        self.unavailable = unavailable
        self.received: list = []

    def is_available(self) -> bool:
        return not self.unavailable

    def image_to_text(self, image_bytes: bytes) -> str:
        self.received.append(image_bytes)
        if self.unavailable:
            raise OcrUnavailableError("simulado: motor caído")
        return self.text


class FakeSttBackend:
    """Backend STT determinista para pruebas: transcribe audio o simula caída del motor."""

    name = "fake-stt"

    def __init__(self, text: str = VALID_AUDIO_TEXT, unavailable: bool = False):
        self.text = text
        self.unavailable = unavailable
        self.received: list = []

    def is_available(self) -> bool:
        return not self.unavailable

    def audio_to_text(self, audio_bytes: bytes, filename: str = "", mime_type: str = "audio/ogg") -> SttResult:
        self.received.append((audio_bytes, filename, mime_type))
        if self.unavailable:
            raise SttUnavailableError("simulado: motor STT caído")
        return SttResult(
            text=self.text,
            confidence=0.98 if self.text else 0.0,
            language="es",
            duration_seconds=2.5,
            engine=self.name
        )
