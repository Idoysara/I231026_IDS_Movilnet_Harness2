"""Pruebas unitarias y de resiliencia para backends de STT (Pilar IV y V)."""

import io
import json
import os
import sys
import unittest
import urllib.error
from unittest import mock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from infrastructure.stt_backends import (  # noqa: E402
    GeminiAudioBackend,
    LocalWhisperCliBackend,
    SttUnavailableError,
    UnavailableSttBackend,
    build_stt_backend,
)
from application.transcription_engine import TranscriptionEngine  # noqa: E402
from tests.fakes import FakeSttBackend  # noqa: E402


class TestSttBackends(unittest.TestCase):

    def test_fabrica_respeta_variables_de_entorno(self):
        with mock.patch.dict(os.environ, {"WHISPER_ENGINE_TYPE": "none"}):
            self.assertIsInstance(build_stt_backend(), UnavailableSttBackend)
        with mock.patch.dict(os.environ, {"WHISPER_ENGINE_TYPE": "gemini"}):
            self.assertIsInstance(build_stt_backend(), GeminiAudioBackend)
        with mock.patch.dict(os.environ, {"WHISPER_ENGINE_TYPE": "local"}):
            self.assertIsInstance(build_stt_backend(), LocalWhisperCliBackend)

    def test_valor_desconocido_falla_cerrado(self):
        """Valores inventados o no soportados caen en UnavailableSttBackend (falla cerrado)."""
        self.assertIsInstance(build_stt_backend("motor_fantasma_123"), UnavailableSttBackend)

    def test_unavailable_backend_lanza_error_tipado(self):
        be = UnavailableSttBackend()
        self.assertFalse(be.is_available())
        with self.assertRaises(SttUnavailableError):
            be.audio_to_text(b"audio_bytes")

    def test_audio_vacio_o_gigante_rechazado(self):
        be = GeminiAudioBackend(api_key="mock_key")
        with self.assertRaises(SttUnavailableError):
            be.audio_to_text(b"")
        with self.assertRaises(SttUnavailableError):
            be.audio_to_text(b"x" * (16 * 1024 * 1024 + 1))

    def test_gemini_audio_sin_key_no_disponible(self):
        be = GeminiAudioBackend(api_key="")
        self.assertFalse(be.is_available())
        with self.assertRaises(SttUnavailableError):
            be.audio_to_text(b"dummy")

    @mock.patch("urllib.request.urlopen")
    def test_gemini_audio_transcripcion_exitosa(self, mock_urlopen):
        resp_payload = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Deseo consultar mi saldo 4GMAX"}]
                }
            }]
        }
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = json.dumps(resp_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        be = GeminiAudioBackend(api_key="test_key")
        res = be.audio_to_text(b"OggS_fake_audio", filename="nota.ogg")
        self.assertEqual(res.text, "Deseo consultar mi saldo 4GMAX")
        self.assertGreater(res.confidence, 0.9)
        self.assertEqual(res.engine, "gemini_audio")

    @mock.patch("urllib.request.urlopen")
    def test_gemini_audio_silencio_devuelve_texto_vacio(self, mock_urlopen):
        resp_payload = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "[SILENCIO]"}]
                }
            }]
        }
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = json.dumps(resp_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        be = GeminiAudioBackend(api_key="test_key")
        res = be.audio_to_text(b"OggS_silencio", filename="silencio.ogg")
        self.assertEqual(res.text, "")
        self.assertEqual(res.confidence, 0.1)

    @mock.patch("urllib.request.urlopen")
    def test_gemini_audio_error_http_lanza_error_tipado(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://mock", code=403, msg="Forbidden", hdrs={}, fp=io.BytesIO(b"Clave invalida")
        )
        be = GeminiAudioBackend(api_key="bad_key")
        with self.assertRaises(SttUnavailableError):
            be.audio_to_text(b"OggS_audio")


class TestTranscriptionEngineStt(unittest.TestCase):

    def test_transcribe_audio_exitoso(self):
        fake = FakeSttBackend(text="Quiero pagar mi factura")
        engine = TranscriptionEngine(stt_backend=fake)
        res = engine.transcribe_audio(b"audio_bytes", filename="pago.ogg")
        self.assertEqual(res.text, "Quiero pagar mi factura")
        self.assertEqual(res.confidence, 0.98)
        self.assertEqual(res.engine, "fake-stt")

    def test_transcribe_audio_motor_caido_falla_cerrado(self):
        fake = FakeSttBackend(unavailable=True)
        engine = TranscriptionEngine(stt_backend=fake)
        res = engine.transcribe_audio(b"audio_bytes", filename="pago.ogg")
        self.assertEqual(res.text, "")
        self.assertEqual(res.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
