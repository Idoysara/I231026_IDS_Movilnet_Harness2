"""
Módulo Autónomo de Despacho Multimodal — Suite de Pruebas: Pipeline de Almacenamiento y Bóvedas
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: 100% PASS)
"""

import unittest
import tempfile
import os
import shutil
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from domain.enums import MediaType, MediaDirection, VaultStatus, ProcessingStatus
from domain.invariants import QuotaExceededError, SecurityException
from infrastructure.database import get_multimodal_connection, init_multimodal_tables
from infrastructure.repository import MultimodalRepository
from infrastructure.storage_engine import StorageEngine
from application.vault_service import VaultService
from application.media_processor import MediaProcessor
from application.transcription_engine import TranscriptionEngine
from tests.fakes import FakeOcrBackend, FakeSttBackend


class TestMediaPipeline(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test_vault.db")
        self.conn = get_multimodal_connection(self.db_path)
        init_multimodal_tables(self.conn)
        self.repo = MultimodalRepository(self.conn)
        self.storage = StorageEngine(os.path.join(self.tmp_dir, "vaults"))
        self.vault_service = VaultService(self.repo, self.storage, default_quota_bytes=10000)
        self.ocr = FakeOcrBackend()
        self.stt = FakeSttBackend()
        self.processor = MediaProcessor(
            self.vault_service, self.repo, TranscriptionEngine(ocr_backend=self.ocr, stt_backend=self.stt)
        )

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp_dir)

    def test_vault_creation_and_isolation(self):
        v1 = self.vault_service.get_or_create_user_vault("+584161112233")
        v2 = self.vault_service.get_or_create_user_vault("+584164445566")
        self.assertNotEqual(v1.vault_id, v2.vault_id)
        self.assertNotEqual(v1.msisdn_hash, v2.msisdn_hash)
        self.assertEqual(v1.quota_used_bytes, 0)
        self.assertEqual(v1.status, VaultStatus.ACTIVE)

    def test_store_audio_asset_updates_quota(self):
        sample_audio = b"OggS\x00\x02\x00\x00\x00\x00" + b"AUDIO_DATA" * 50
        asset = self.vault_service.store_user_asset(
            phone_number="+584161112233",
            filename="nota1.ogg",
            file_bytes=sample_audio,
            direction=MediaDirection.INBOUND
        )
        self.assertEqual(asset.media_type, MediaType.AUDIO)
        self.assertEqual(asset.file_size_bytes, len(sample_audio))

        quota = self.vault_service.check_user_quota("+584161112233")
        self.assertEqual(quota["quota_used_bytes"], len(sample_audio))
        self.assertTrue(quota["can_upload"])

    def test_quota_exceeded_raises_error(self):
        # La cuota configurada en setUp es 10,000 bytes
        huge_file = b"%PDF" + b"X" * 12000
        with self.assertRaises(QuotaExceededError):
            self.vault_service.store_user_asset(
                phone_number="+584161112233",
                filename="documento_grande.pdf",
                file_bytes=huge_file
            )

    def test_path_traversal_attack_neutralized(self):
        malicious_filename = "../../../etc/passwd"
        safe_bytes = b"%PDF-1.4\n1 0 obj"
        asset = self.vault_service.store_user_asset(
            phone_number="+584161112233",
            filename=malicious_filename,
            file_bytes=safe_bytes
        )
        # El archivo físico debe quedar contenido dentro de la bóveda
        self.assertNotIn("..", asset.file_rel_path)
        self.assertTrue(asset.file_rel_path.startswith("usr_"))

    def test_ingest_and_process_image(self):
        sample_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"VOUCHER_IMAGE"
        asset = self.processor.ingest_and_process(
            phone_number="+584161112233",
            filename="comprobante.jpg",
            file_bytes=sample_jpg
        )
        self.assertEqual(asset.media_type, MediaType.IMAGE)
        self.assertEqual(asset.processing_status, ProcessingStatus.PROCESSED)
        self.assertIn("Comprobante de Pago Móvil C2P", asset.transcription_text)
        # Datos extraídos del TEXTO del OCR (no valores fijos) y bytes reales entregados al motor
        self.assertEqual(asset.analysis_metadata["reference_number"], "0084729104")
        self.assertEqual(asset.analysis_metadata["amount_ves"], 250.0)
        self.assertEqual(self.ocr.received, [sample_jpg])

    def test_image_without_voucher_is_not_invented(self):
        self.ocr.text = "una foto cualquiera sin datos bancarios"
        asset = self.processor.ingest_and_process(
            phone_number="+584161112233", filename="foto.jpg",
            file_bytes=b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"OTRA"
        )
        self.assertFalse(asset.analysis_metadata["is_valid_voucher"])
        self.assertNotIn("reference_number", asset.analysis_metadata)
        self.assertNotIn("Comprobante de Pago Móvil C2P", asset.transcription_text)

    def test_ocr_unavailable_marks_asset_failed(self):
        self.ocr.unavailable = True
        asset = self.processor.ingest_and_process(
            phone_number="+584161112233", filename="foto.jpg",
            file_bytes=b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"X"
        )
        self.assertEqual(asset.processing_status, ProcessingStatus.FAILED)
        self.assertEqual(asset.analysis_metadata["ocr_status"], "OCR_UNAVAILABLE")
        self.assertFalse(asset.analysis_metadata["is_valid_voucher"])

    def test_ingest_and_process_audio(self):
        sample_audio = b"OggS\x00\x02\x00\x00\x00\x00" + b"AUDIO_DATA" * 10
        asset = self.processor.ingest_and_process(
            phone_number="+584161112233",
            filename="nota_voz.ogg",
            file_bytes=sample_audio
        )
        self.assertEqual(asset.media_type, MediaType.AUDIO)
        self.assertEqual(asset.processing_status, ProcessingStatus.PROCESSED)
        self.assertEqual(asset.transcription_text, self.stt.text)
        self.assertEqual(len(self.stt.received), 1)
        self.assertEqual(self.stt.received[0][0], sample_audio)

    def test_stt_unavailable_marks_audio_failed(self):
        self.stt.unavailable = True
        sample_audio = b"OggS\x00\x02\x00\x00\x00\x00" + b"AUDIO_DATA" * 10
        asset = self.processor.ingest_and_process(
            phone_number="+584161112233",
            filename="nota_voz.ogg",
            file_bytes=sample_audio
        )
        self.assertEqual(asset.media_type, MediaType.AUDIO)
        self.assertEqual(asset.processing_status, ProcessingStatus.FAILED)
        self.assertEqual(asset.transcription_text, "")

    def test_ingest_and_process_video(self):
        # MP4 magic bytes: ....ftypisom
        sample_video = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00" + b"VIDEO_PAYLOAD" * 20
        asset = self.processor.ingest_and_process(
            phone_number="+584161112233",
            filename="soporte.mp4",
            file_bytes=sample_video
        )
        self.assertEqual(asset.media_type, MediaType.VIDEO)
        self.assertEqual(asset.processing_status, ProcessingStatus.PROCESSED)
        self.assertIn("soporte.mp4", asset.transcription_text)
        self.assertEqual(asset.analysis_metadata.get("type"), "MP4_VIDEO")
        self.assertTrue(asset.file_rel_path.endswith(".mp4"))
        self.assertIn("/video/", f"/{asset.file_rel_path}")


if __name__ == "__main__":
    unittest.main()
