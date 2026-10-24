"""
Módulo Autónomo de Despacho Multimodal — Suite de Pruebas: Endpoints del Servidor Autónomo
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: 100% PASS)
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


class MockSocket:
    """Socket en memoria sin dependencias de red física para pruebas herméticas ultra-rápidas."""

    def __init__(self, request_bytes: bytes):
        self.rfile = io.BytesIO(request_bytes)
        self.wfile = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        if "r" in mode:
            return self.rfile
        return self.wfile

    def sendall(self, data: bytes):
        self.wfile.write(data)


class TestAutonomousService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmp_dir, "test_server.db")
        cls._prev_vault_env = os.environ.get("MULTIMODAL_VAULT_ROOT")
        os.environ["MULTIMODAL_VAULT_ROOT"] = os.path.join(cls.tmp_dir, "vaults")
        cls.stt = FakeSttBackend(text="Quiero consultar mi saldo disponible")
        cls.ocr = FakeOcrBackend()
        cls.engine = TranscriptionEngine(ocr_backend=cls.ocr, stt_backend=cls.stt)
        MultimodalRequestHandler.setup_services(cls.db_path, engine=cls.engine)

    @classmethod
    def tearDownClass(cls):
        if cls._prev_vault_env is None:
            os.environ.pop("MULTIMODAL_VAULT_ROOT", None)
        else:
            os.environ["MULTIMODAL_VAULT_ROOT"] = cls._prev_vault_env
        shutil.rmtree(cls.tmp_dir)

    def _execute_request(self, method: str, path: str, payload: dict = None):
        """Ejecuta una petición HTTP en memoria simulando el pipeline de red completo."""
        body_bytes = json.dumps(payload).encode("utf-8") if payload else b""
        headers = [
            f"{method} {path} HTTP/1.1",
            "Host: localhost",
            f"Content-Length: {len(body_bytes)}",
            "Content-Type: application/json"
        ]
        raw_req = "\r\n".join(headers).encode("utf-8") + b"\r\n\r\n" + body_bytes

        sock = MockSocket(raw_req)
        # Invocar el Handler
        MultimodalRequestHandler(sock, ("127.0.0.1", 12345), None)
        
        raw_resp = sock.wfile.getvalue().decode("utf-8", errors="replace")
        header_part, _, body_part = raw_resp.partition("\r\n\r\n")
        status_line = header_part.splitlines()[0] if header_part else "HTTP/1.1 500 Error"
        status_code = int(status_line.split()[1])
        json_data = json.loads(body_part) if body_part else {}
        return status_code, json_data

    def test_health_check_endpoint(self):
        status, body = self._execute_request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["database"], "CONNECTED_WAL")

    def test_init_vault_endpoint(self):
        status, body = self._execute_request("POST", "/api/v1/vault/init", {"phone_number": "+584166251587"})
        self.assertEqual(status, 200)
        self.assertIn("vault_id", body)
        self.assertEqual(body["status"], "ACTIVE")

    def test_get_quota_endpoint(self):
        status, body = self._execute_request("GET", "/api/v1/vault/quota?phone=%2B584166251587")
        self.assertEqual(status, 200)
        self.assertIn("quota_limit_bytes", body)
        self.assertTrue(body["can_upload"])

    def test_multimodal_process_endpoint(self):
        payload = {
            "phone_number": "+584166251587",
            "filename": "audio_test.ogg",
            "text_simulation": "Quiero consultar mi saldo disponible"
        }
        status, body = self._execute_request("POST", "/api/v1/multimodal/process", payload)
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "PROCESSED")
        self.assertIn("reply_text", body)
        # Verificar la Regla Inviolable de Enlace PWA
        self.assertIn("Portal PWA 4GMAX", body["reply_text"])


if __name__ == "__main__":
    unittest.main()
