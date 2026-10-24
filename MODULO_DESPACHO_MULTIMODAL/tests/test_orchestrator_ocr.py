"""Pruebas del orquestador con OCR real: sin respuestas ni recibos con datos inventados (H-05). Pilar V."""

import os
import shutil
import sys
import tempfile
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from infrastructure.database import get_multimodal_connection, init_multimodal_tables  # noqa: E402
from infrastructure.repository import MultimodalRepository  # noqa: E402
from infrastructure.storage_engine import StorageEngine  # noqa: E402
from infrastructure.whatsapp_client import WhatsAppMultimodalClient  # noqa: E402
from application.vault_service import VaultService  # noqa: E402
from application.media_processor import MediaProcessor  # noqa: E402
from application.rich_response_builder import RichResponseBuilder  # noqa: E402
from application.transcription_engine import TranscriptionEngine  # noqa: E402
from application.multimodal_orchestrator import MultimodalOrchestrator  # noqa: E402
from tests.fakes import FakeOcrBackend, FakeSttBackend  # noqa: E402

JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"IMG"
PHONE = "+584161112233"


class TestOrchestratorOcr(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.conn = get_multimodal_connection(os.path.join(self.tmp_dir, "orq.db"))
        init_multimodal_tables(self.conn)
        repo = MultimodalRepository(self.conn)
        storage = StorageEngine(os.path.join(self.tmp_dir, "vaults"))
        vault = VaultService(repo, storage)
        self.ocr = FakeOcrBackend()
        self.stt = FakeSttBackend()
        processor = MediaProcessor(vault, repo, TranscriptionEngine(ocr_backend=self.ocr, stt_backend=self.stt))
        self.builder_calls = []
        self.builder = RichResponseBuilder()
        original = self.builder.generate_pdf_receipt_bytes
        self.builder.generate_pdf_receipt_bytes = lambda **kw: (self.builder_calls.append(kw), original(**kw))[1]
        self.orq = MultimodalOrchestrator(vault, processor, self.builder, WhatsAppMultimodalClient(), repo)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp_dir)

    def test_voucher_valido_usa_datos_reales_y_no_promete_saldo(self):
        self.ocr.text = "Banco Mercantil\nRef: 555666777\nMonto: Bs. 1.500,75"
        out = self.orq.handle_inbound_media(PHONE, "v.jpg", JPG)
        self.assertEqual(len(self.builder_calls), 1)
        data = self.builder_calls[0]["data"]
        self.assertEqual(data["reference"], "555666777")
        self.assertEqual(data["amount"], "1500.75")
        self.assertIn("Mercantil", data["bank"])
        self.assertIsNotNone(out["output_asset_id"])
        self.assertNotIn("saldo ha sido actualizado", out["reply_text"])
        self.assertNotIn("84729104", out["reply_text"])

    def test_imagen_sin_comprobante_no_genera_recibo(self):
        self.ocr.text = "paisaje con montañas"
        out = self.orq.handle_inbound_media(PHONE, "f.jpg", JPG)
        self.assertEqual(self.builder_calls, [])
        self.assertIsNone(out["output_asset_id"])
        self.assertIn("no logramos identificar un comprobante", out["reply_text"])

    def test_ocr_caido_informa_y_no_genera_recibo(self):
        self.ocr.unavailable = True
        out = self.orq.handle_inbound_media(PHONE, "f.jpg", JPG)
        self.assertEqual(self.builder_calls, [])
        self.assertIsNone(out["output_asset_id"])
        self.assertIn("no pudimos leerla", out["reply_text"])

    def test_audio_exitoso_incluye_transcripcion(self):
        self.stt.text = "Deseo activar un plan de datos"
        audio_ogg = b"OggS\x00\x02\x00\x00\x00\x00" + b"AUDIO_DATA" * 5
        out = self.orq.handle_inbound_media(PHONE, "nota.ogg", audio_ogg)
        self.assertIn("Deseo activar un plan de datos", out["reply_text"])
        self.assertIn("He recibido y procesado tu nota de voz exitosamente", out["reply_text"])

    def test_audio_fallido_avisa_honestamente(self):
        self.stt.unavailable = True
        audio_ogg = b"OggS\x00\x02\x00\x00\x00\x00" + b"AUDIO_DATA" * 5
        out = self.orq.handle_inbound_media(PHONE, "nota.ogg", audio_ogg)
        self.assertIn("no fue posible transcribir el audio en este momento", out["reply_text"])
        self.assertNotIn("exitosamente", out["reply_text"])

    def test_video_recibido_y_archivado(self):
        video_mp4 = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00" + b"VIDEO_BYTES" * 10
        out = self.orq.handle_inbound_media(PHONE, "clip.mp4", video_mp4)
        self.assertIn("He recibido tu video 'clip.mp4'", out["reply_text"])
        self.assertIn("bóveda privada segura", out["reply_text"])


if __name__ == "__main__":
    unittest.main()
