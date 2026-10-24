"""
Módulo Autónomo de Despacho Multimodal — Suite de Pruebas: Integridad Criptográfica del Manifiesto SHA-256
Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Certificación y Trazabilidad Inmutable)
"""

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.generate_sha256_manifest import verify_manifest, MANIFEST_JSON_PATH, CERTIFICATE_MD_PATH


class TestManifestIntegrity(unittest.TestCase):
    """Verifica que el árbol criptográfico SHA-256 del proyecto esté completo e íntegro."""

    def test_certificate_files_exist(self):
        """Verifica que el manifiesto JSON y el certificado Markdown existan."""
        self.assertTrue(os.path.exists(MANIFEST_JSON_PATH), "El archivo MANIFEST_SHA256.json no existe")
        self.assertTrue(os.path.exists(CERTIFICATE_MD_PATH), "El archivo CERTIFICADO_FINAL_SHA256_ENTREGA.md no existe")

    def test_all_files_match_sha256_hashes(self):
        """Verifica que todos los archivos registrados coincidan con sus firmas SHA-256."""
        self.assertTrue(verify_manifest(), "La verificación de integridad SHA-256 falló")


if __name__ == "__main__":
    unittest.main()
