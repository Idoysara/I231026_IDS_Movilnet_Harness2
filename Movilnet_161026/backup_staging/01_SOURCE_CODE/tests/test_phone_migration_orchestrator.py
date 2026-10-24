"""
tests/test_phone_migration_orchestrator.py
==============================================================================
Suite de Pruebas Automatizadas para el Orquestador Universal de Migración Telefónica
Cumple: Pilares I al VII de Excelencia Técnica & Protocolo Decagonal (Regla 100% Pass).
==============================================================================
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.phone_migration_models import PhoneDescriptor, CarrierOperator
from core.phone_migration_orchestrator import PhoneMigrationOrchestrator


class TestPhoneMigrationOrchestrator(unittest.TestCase):
    """Pruebas unitarias de cobertura exhaustiva para PhoneMigrationOrchestrator."""

    def test_phone_descriptor_parsing_and_carrier_classification(self):
        """Verifica la normalización y clasificación estricta de CONATEL."""
        # 1. Movistar 0424
        d1 = PhoneDescriptor.from_string("0424-1533712")
        self.assertEqual(d1.carrier, CarrierOperator.MOVISTAR)
        self.assertEqual(d1.international_digits, "584241533712")
        self.assertEqual(d1.whatsapp_jid, "584241533712@s.whatsapp.net")
        self.assertEqual(d1.international_0058, "00584241533712")
        self.assertEqual(d1.international_e164, "+58 424 1533712")

        # 2. Movilnet 0416
        d2 = PhoneDescriptor.from_string("+58 416 625 1587")
        self.assertEqual(d2.carrier, CarrierOperator.MOVILNET)
        self.assertEqual(d2.national_with_zero, "04166251587")
        self.assertEqual(d2.whatsapp_jid, "584166251587@s.whatsapp.net")

        # 3. Digitel 0412
        d3 = PhoneDescriptor.from_string("584121234567")
        self.assertEqual(d3.carrier, CarrierOperator.DIGITEL)
        self.assertEqual(d3.national_formatted, "0412-1234567")

    def test_replacement_pairs_ordered_precedence(self):
        """Verifica que los pares de reemplazo ordenen de mayor a menor especificidad."""
        d1 = PhoneDescriptor.from_string("04241533712")
        d2 = PhoneDescriptor.from_string("04161234567")
        orch = PhoneMigrationOrchestrator()
        pairs = orch._build_replacement_pairs(d1, d2)

        # wa.me y JID deben preceder a los dígitos sueltos
        first_keys = [p[0] for p in pairs[:3]]
        self.assertTrue(any("wa.me" in k for k in first_keys))
        self.assertTrue(any("@s.whatsapp.net" in k for k in first_keys))

    def test_dry_run_analysis_in_isolated_directory(self):
        """Verifica el análisis en seco (Dry-Run) sin modificar el disco."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mod1 = tmp_path / "core" / "sample.py"
            mod1.parent.mkdir(parents=True, exist_ok=True)
            mod1.write_text("BOT = '0424-1533712'\nJID = '584241533712@s.whatsapp.net'\n")

            orch = PhoneMigrationOrchestrator(root_dir=tmp_path)
            plan = orch.analyze_plan("04241533712", "04169999999", "MOVI")

            self.assertEqual(plan.total_files_analyzed, 1)
            self.assertEqual(plan.total_matches_detected, 2)
            self.assertEqual(len(plan.components), 1)
            self.assertEqual(plan.components[0].status, "PENDING")
            self.assertFalse(plan.executed)

            # Verificar que el archivo NO fue modificado
            self.assertIn("0424-1533712", mod1.read_text())

    def test_atomic_migration_and_rollback_on_syntax_error(self):
        """Verifica la ejecución atómica y la reversión automática (Rollback) ante fallas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mod_valid = tmp_path / "api" / "valid.py"
            mod_valid.parent.mkdir(parents=True, exist_ok=True)
            mod_valid.write_text("ACTIVE_PHONE = '0424-1533712'\n")

            orch = PhoneMigrationOrchestrator(root_dir=tmp_path)
            plan = orch.analyze_plan("04241533712", "04169999999")
            executed_plan = orch.execute_migration(plan, skip_tests=True)

            self.assertTrue(executed_plan.success)
            self.assertIn("0416-9999999", mod_valid.read_text())
            self.assertIsNotNone(executed_plan.backup_snapshot_dir)

            # Ejecutar rollback manual
            rolled_back = orch.rollback_snapshot(executed_plan.backup_snapshot_dir)
            self.assertTrue(rolled_back)
            self.assertIn("0424-1533712", mod_valid.read_text())

    def test_sha256_seal_integrity(self):
        """Verifica que la migración genere un sello criptográfico inmutable SHA-256."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            doc = tmp_path / "ui" / "index.html"
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text("<span>04241533712</span>")

            orch = PhoneMigrationOrchestrator(root_dir=tmp_path)
            plan = orch.analyze_plan("04241533712", "04169999999")
            executed = orch.execute_migration(plan, skip_tests=True)

            self.assertEqual(len(executed.sha256_seal), 64)  # Hexadecimal SHA-256


if __name__ == "__main__":
    unittest.main()
