"""
Módulo Autónomo de Despacho Multimodal — Suite de Pruebas: Benchmark E2E y Cumplimiento de SLAs
Gobernanza: Universal Best Practices Engineering Rule (Pilares II, IV, V)
"""

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.benchmark_multimodal_e2e import run_e2e_benchmark


class TestBenchmarkE2E(unittest.TestCase):
    """Verifica que el microservicio cumpla los SLAs Carrier-Grade de latencia y 100% de éxito."""

    def test_e2e_benchmark_slas_and_success_rate(self):
        """Ejecuta el benchmark E2E y verifica que todas las operaciones cumplan SLAs estrictos."""
        results = run_e2e_benchmark(iterations=10)

        # 1. Tasa de éxito absoluta
        self.assertEqual(results["success_rate_percent"], 100.0)
        self.assertEqual(results["total_operations"], 40)

        pipelines = results["pipelines"]

        # 2. SLA Voucher C2P (Ingesta + Bóveda + Recibo PDF + Despacho) < 50ms promedio
        voucher_stats = pipelines["voucher_c2p"]
        self.assertEqual(voucher_stats["count"], 10)
        self.assertLess(voucher_stats["avg_ms"], 50.0)

        # 3. SLA Nota de voz (Ingesta + STT + Bóveda + Despacho) < 30ms promedio
        audio_stats = pipelines["voice_note_stt"]
        self.assertEqual(audio_stats["count"], 10)
        self.assertLess(audio_stats["avg_ms"], 30.0)

        # 4. SLA Video (Ingesta + Magic bytes + Bóveda + Despacho) < 30ms promedio
        video_stats = pipelines["video_ingest"]
        self.assertEqual(video_stats["count"], 10)
        self.assertLess(video_stats["avg_ms"], 30.0)

        # 5. SLA Consulta de cuota < 10ms promedio
        quota_stats = pipelines["vault_quota_query"]
        self.assertEqual(quota_stats["count"], 10)
        self.assertLess(quota_stats["avg_ms"], 10.0)


if __name__ == "__main__":
    unittest.main()
