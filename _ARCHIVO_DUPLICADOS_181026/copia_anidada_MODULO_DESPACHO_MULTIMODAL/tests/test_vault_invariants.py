"""
Módulo Autónomo de Despacho Multimodal — Suite de Pruebas: Invariantes de Dominio
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: 100% PASS)
"""

import unittest
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from domain.enums import MediaType, MediaDirection, VaultStatus
from domain.invariants import (
    normalize_phone_number,
    generate_msisdn_hash,
    mask_phone_for_display,
    detect_mime_and_media_type,
    validate_file_size,
    append_universal_pwa_link,
    DomainInvariantViolationError,
    OFFICIAL_PWA_LINK
)


class TestVaultInvariants(unittest.TestCase):

    def test_phone_normalization_valid(self):
        self.assertEqual(normalize_phone_number("04166251587"), "+584166251587")
        self.assertEqual(normalize_phone_number("+58 416 625 1587"), "+584166251587")
        self.assertEqual(normalize_phone_number("584241533712"), "+584241533712")

    def test_phone_normalization_empty_raises(self):
        with self.assertRaises(DomainInvariantViolationError):
            normalize_phone_number("")

    def test_msisdn_hash_deterministic(self):
        h1 = generate_msisdn_hash("04166251587", "secret1")
        h2 = generate_msisdn_hash("+584166251587", "secret1")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_phone_masking(self):
        masked = mask_phone_for_display("04166251587")
        self.assertIn("****", masked)
        self.assertTrue(masked.startswith("+58416"))

    def test_magic_bytes_detection_jpeg(self):
        jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        mime, mtype = detect_mime_and_media_type(jpeg_header)
        self.assertEqual(mime, "image/jpeg")
        self.assertEqual(mtype, MediaType.IMAGE)

    def test_magic_bytes_detection_pdf(self):
        pdf_header = b"%PDF-1.4\n1 0 obj"
        mime, mtype = detect_mime_and_media_type(pdf_header)
        self.assertEqual(mime, "application/pdf")
        self.assertEqual(mtype, MediaType.DOCUMENT)

    def test_magic_bytes_detection_ogg(self):
        ogg_header = b"OggS\x00\x02\x00\x00"
        mime, mtype = detect_mime_and_media_type(ogg_header)
        self.assertEqual(mime, "audio/ogg")
        self.assertEqual(mtype, MediaType.AUDIO)

    def test_magic_bytes_unknown_rejected(self):
        malicious = b"\x7fELF\x02\x01\x01\x00"  # ELF binary
        with self.assertRaises(DomainInvariantViolationError):
            detect_mime_and_media_type(malicious)

    def test_file_size_exceeded_rejected(self):
        huge_bytes = b"A" * (6 * 1024 * 1024)  # 6 MB (> 5 MB for IMAGE)
        with self.assertRaises(DomainInvariantViolationError):
            validate_file_size(huge_bytes, MediaType.IMAGE)

    def test_universal_pwa_link_appended(self):
        msg = "Su saldo es Bs. 150.00"
        formatted = append_universal_pwa_link(msg)
        self.assertIn(OFFICIAL_PWA_LINK, formatted)
        self.assertTrue(formatted.startswith("Su saldo es Bs. 150.00"))

    def test_universal_pwa_link_idempotent(self):
        msg = f"Hola {OFFICIAL_PWA_LINK}"
        formatted = append_universal_pwa_link(msg)
        self.assertEqual(formatted.count(OFFICIAL_PWA_LINK), 1)


if __name__ == "__main__":
    unittest.main()
