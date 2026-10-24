"""
Módulo Autónomo de Despacho Multimodal — Suite de Pruebas: Contrato de Webhook n8n Stage (:8025)
Gobernanza: Universal Best Practices Engineering Rule (Pilares I, III, IV, V)
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from service.server import MultimodalRequestHandler
from application.transcription_engine import TranscriptionEngine
from tests.fakes import FakeOcrBackend, FakeSttBackend
from scripts.simulate_n8n_stage_webhook import build_n8n_stage_payload


class MockSocket:
    """Socket en memoria sin dependencias de red física para pruebas de contrato."""

    def __init__(self, request_bytes: bytes):
        self.rfile = io.BytesIO(request_bytes)
        self.wfile = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        if "r" in mode:
            return self.rfile
        return self.wfile

    def sendall(self, data: bytes):
        self.wfile.write(data)


class TestN8NStageContract(unittest.TestCase):
    """Verifica que el endpoint :8025 cumpla el contrato de n8n DEV_STAGE para todos los medios."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmp_dir, "test_contract.db")
        cls._prev_vault_env = os.environ.get("MULTIMODAL_VAULT_ROOT")
        os.environ["MULTIMODAL_VAULT_ROOT"] = os.path.join(cls.tmp_dir, "vaults")

        # Fake OCR que reconoce comprobante C2P con referencia y monto
        cls.ocr = FakeOcrBackend(
            text="Comprobante Pago Movil C2P\nBanco: 0102 Banco de Venezuela\nReferencia: 84729104\nMonto: Bs. 250,00\nFecha: 18/10/2026"
        )
        cls.stt = FakeSttBackend(text="Hola Movilnet, deseo recargar mi saldo")
        cls.engine = TranscriptionEngine(ocr_backend=cls.ocr, stt_backend=cls.stt)
        MultimodalRequestHandler.setup_services(cls.db_path, engine=cls.engine)

    @classmethod
    def tearDownClass(cls):
        if cls._prev_vault_env is None:
            os.environ.pop("MULTIMODAL_VAULT_ROOT", None)
        else:
            os.environ["MULTIMODAL_VAULT_ROOT"] = cls._prev_vault_env
        shutil.rmtree(cls.tmp_dir)

    def _execute_post(self, path: str, payload: dict):
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = [
            f"POST {path} HTTP/1.1",
            "Host: localhost",
            f"Content-Length: {len(body_bytes)}",
            "Content-Type: application/json",
            "X-N8N-Source: DEV_STAGE"
        ]
        raw_req = "\r\n".join(headers).encode("utf-8") + b"\r\n\r\n" + body_bytes
        sock = MockSocket(raw_req)
        MultimodalRequestHandler(sock, ("127.0.0.1", 12345), None)

        raw_resp = sock.wfile.getvalue().decode("utf-8", errors="replace")
        header_part, _, body_part = raw_resp.partition("\r\n\r\n")
        status_line = header_part.splitlines()[0] if header_part else "HTTP/1.1 500 Error"
        status_code = int(status_line.split()[1])
        json_data = json.loads(body_part) if body_part else {}
        return status_code, json_data

    def test_n8n_stage_voucher_processing_contract(self):
        """Verifica que el payload de n8n para comprobantes sea procesado exitosamente."""
        payload = build_n8n_stage_payload("+584166251587", "IMAGE")
        status, body = self._execute_post("/api/v1/multimodal/process", payload)

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "PROCESSED")
        self.assertEqual(body["phone_number"], "+584166251587")
        self.assertIn("84729104", body["transcription"])
        self.assertIn("Banco de Venezuela", body["transcription"])
        self.assertIn("250.00", body["transcription"])
        self.assertIsNotNone(body["output_asset_id"])
        # Debe incluir la URL oficial PWA
        self.assertIn("Portal PWA 4GMAX", body["reply_text"])
        # Debe despachar por el cliente WhatsApp
        self.assertIn("dispatch", body)
        self.assertTrue(body["dispatch"]["success"])

    def test_n8n_stage_voice_note_contract(self):
        """Verifica que el payload de n8n para audios OGG sea procesado exitosamente."""
        payload = build_n8n_stage_payload("+584166251587", "AUDIO")
        status, body = self._execute_post("/api/v1/multimodal/process", payload)

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "PROCESSED")
        self.assertEqual(body["media_type"], "AUDIO")
        self.assertIn("deseo recargar mi saldo", body["transcription"])
        self.assertIn("Portal PWA 4GMAX", body["reply_text"])

    def test_n8n_stage_video_contract(self):
        """Verifica que el payload de n8n para videos MP4 sea procesado y archivado en bóveda."""
        payload = build_n8n_stage_payload("+584166251587", "VIDEO")
        status, body = self._execute_post("/api/v1/multimodal/process", payload)

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "PROCESSED")
        self.assertEqual(body["media_type"], "VIDEO")
        self.assertIn("archivado en tu bóveda privada", body["reply_text"])
        self.assertIn("Portal PWA 4GMAX", body["reply_text"])

    def test_n8n_stage_invalid_payload_rejection(self):
        """Verifica que payloads sin número de teléfono sean rechazados con 400."""
        status, body = self._execute_post("/api/v1/multimodal/process", {"filename": "foto.jpg"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
