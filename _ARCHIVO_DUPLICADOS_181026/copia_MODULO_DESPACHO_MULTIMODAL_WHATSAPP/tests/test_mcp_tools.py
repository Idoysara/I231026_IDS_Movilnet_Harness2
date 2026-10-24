"""
Módulo Autónomo de Despacho Multimodal — Suite de Pruebas: Herramientas MCP
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

from mcp.mcp_multimodal_tools import MultimodalMcpTools


class TestMcpTools(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "mcp_test.db")
        self.tools = MultimodalMcpTools(self.db_path)

    def tearDown(self):
        self.tools.conn.close()
        shutil.rmtree(self.tmp_dir)

    def test_check_quota(self):
        res = self.tools.mcp_vault_check_quota("+584166251587")
        self.assertIn("quota_limit_bytes", res)
        self.assertEqual(res["quota_used_bytes"], 0)
        self.assertTrue(res["can_upload"])

    def test_generate_pdf_receipt_and_inspect(self):
        data = {"reference": "REF9988", "amount": "350.00", "bank": "0102 Banco de Venezuela"}
        res = self.tools.mcp_generate_pdf_receipt("+584166251587", data)
        self.assertEqual(res["status"], "GENERATED")
        self.assertIsNotNone(res["asset_id"])

        # Inspeccionar el activo recién creado
        inspect = self.tools.mcp_media_inspect_asset(res["asset_id"])
        self.assertEqual(inspect["asset_id"], res["asset_id"])
        self.assertEqual(inspect["media_type"], "DOCUMENT")

    def test_ocr_extraction(self):
        # Crear activo mock y validar extracción OCR
        sample_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"TEST_IMAGE"
        from domain.enums import MediaDirection
        asset = self.tools.vault_service.store_user_asset(
            phone_number="+584166251587",
            filename="foto.jpg",
            file_bytes=sample_jpg,
            direction=MediaDirection.INBOUND
        )
        ocr = self.tools.mcp_image_ocr_extract(asset.asset_id)
        self.assertEqual(ocr["intent"], "PAGO_C2P")
        self.assertIn("bank_code", ocr["extracted_data"])


if __name__ == "__main__":
    unittest.main()
