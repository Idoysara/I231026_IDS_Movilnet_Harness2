"""
Módulo Autónomo de Despacho Multimodal — Benchmark de Rendimiento Carrier-Grade
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: Telemetría)
"""

import argparse
import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from infrastructure.database import get_multimodal_connection, init_multimodal_tables
from infrastructure.repository import MultimodalRepository
from infrastructure.storage_engine import StorageEngine
from application.vault_service import VaultService


def run_benchmark(iterations: int = 50) -> dict:
    """Mide la latencia de almacenamiento y consulta de bóveda."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "bench.db")
        conn = get_multimodal_connection(db_path)
        init_multimodal_tables(conn)
        repo = MultimodalRepository(conn)
        storage = StorageEngine(tmp_dir)
        service = VaultService(repo, storage)

        sample_bytes = b"OggS\x00\x02\x00\x00\x00\x00" + b"A" * 1024  # 1 KB

        latencies = []
        for i in range(iterations):
            phone = f"+58416{1000000 + i}"
            t0 = time.time()
            service.store_user_asset(phone, f"audio_{i}.ogg", sample_bytes)
            lat = (time.time() - t0) * 1000
            latencies.append(lat)

        conn.close()

        avg_lat = sum(latencies) / len(latencies)
        p95_lat = sorted(latencies)[int(len(latencies) * 0.95)]

        return {
            "iterations": iterations,
            "avg_latency_ms": round(avg_lat, 3),
            "p95_latency_ms": round(p95_lat, 3),
            "min_ms": round(min(latencies), 3),
            "max_ms": round(max(latencies), 3)
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Multimodal")
    parser.add_argument("--iterations", type=int, default=50, help="Número de iteraciones")
    args = parser.parse_args()

    results = run_benchmark(args.iterations)
    print("=" * 60)
    print("⚡ RESULTADOS DE BENCHMARK MULTIMODAL")
    print("=" * 60)
    print(f"Iteraciones:       {results['iterations']}")
    print(f"Latencia Promedio: {results['avg_latency_ms']} ms")
    print(f"Latencia P95:      {results['p95_latency_ms']} ms")
    print(f"Mínimo:            {results['min_ms']} ms")
    print(f"Máximo:            {results['max_ms']} ms")
    print("=" * 60)
    assert results["avg_latency_ms"] < 20.0, "La latencia promedio supera el SLA de 20ms"
    print("✅ Benchmark aprobado dentro de SLAs Carrier-Grade.")
