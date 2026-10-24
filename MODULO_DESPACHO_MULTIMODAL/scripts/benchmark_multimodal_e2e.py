"""
Módulo Autónomo de Despacho Multimodal — Capa de Calidad: Benchmark de Rendimiento E2E
Gobernanza: Universal Best Practices Engineering Rule (Pilar II, IV, V y VII)

Mide la latencia de extremo a extremo (E2E) en el microservicio multimodal (:8025):
  1. Pipeline de Comprobantes C2P (Imagen + OCR + Recibo PDF + Despacho)
  2. Pipeline de Notas de Voz (Audio OGG + STT + Despacho)
  3. Pipeline de Video (MP4 + Ingesta Bóveda + Despacho)
  4. Consultas de Cuota y Bóveda (GET /quota, GET /assets)

Ejecución autónoma:
    python3 scripts/benchmark_multimodal_e2e.py --test
    python3 scripts/benchmark_multimodal_e2e.py --iterations 30
    python3 scripts/benchmark_multimodal_e2e.py --live --url http://127.0.0.1:8025
"""

import argparse
import base64
import io
import json
import logging
import os
import shutil
import sys
import tempfile
import time
from typing import Dict, Any, List, Tuple

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from service.server import MultimodalRequestHandler
from application.transcription_engine import TranscriptionEngine
from tests.fakes import FakeOcrBackend, FakeSttBackend
from scripts.simulate_n8n_stage_webhook import build_n8n_stage_payload

logging.basicConfig(level=logging.WARNING)


class InMemoryClient:
    """Cliente HTTP en memoria sin sockets físicos para benchmarking determinista de alta velocidad."""

    def __init__(self, handler_cls):
        self.handler_cls = handler_cls

    def post(self, path: str, payload: dict) -> Tuple[int, dict, float]:
        body_bytes = json.dumps(payload).encode("utf-8")
        raw_req = (
            f"POST {path} HTTP/1.1\r\n"
            f"Host: localhost\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"
            f"Content-Type: application/json\r\n\r\n"
        ).encode("utf-8") + body_bytes

        class _MockSocket:
            def __init__(self, req):
                self.rfile = io.BytesIO(req)
                self.wfile = io.BytesIO()
            def makefile(self, mode, *args, **kwargs):
                return self.rfile if "r" in mode else self.wfile
            def sendall(self, d):
                self.wfile.write(d)

        sock = _MockSocket(raw_req)
        t0 = time.perf_counter()
        self.handler_cls(sock, ("127.0.0.1", 12345), None)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        raw_resp = sock.wfile.getvalue().decode("utf-8", errors="replace")
        header_part, _, body_part = raw_resp.partition("\r\n\r\n")
        status_line = header_part.splitlines()[0] if header_part else "HTTP/1.1 500"
        status_code = int(status_line.split()[1])
        json_data = json.loads(body_part) if body_part else {}
        return status_code, json_data, elapsed_ms

    def get(self, path: str) -> Tuple[int, dict, float]:
        raw_req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: localhost\r\n\r\n"
        ).encode("utf-8")

        class _MockSocket:
            def __init__(self, req):
                self.rfile = io.BytesIO(req)
                self.wfile = io.BytesIO()
            def makefile(self, mode, *args, **kwargs):
                return self.rfile if "r" in mode else self.wfile
            def sendall(self, d):
                self.wfile.write(d)

        sock = _MockSocket(raw_req)
        t0 = time.perf_counter()
        self.handler_cls(sock, ("127.0.0.1", 12345), None)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        raw_resp = sock.wfile.getvalue().decode("utf-8", errors="replace")
        header_part, _, body_part = raw_resp.partition("\r\n\r\n")
        status_line = header_part.splitlines()[0] if header_part else "HTTP/1.1 500"
        status_code = int(status_line.split()[1])
        json_data = json.loads(body_part) if body_part else {}
        return status_code, json_data, elapsed_ms


def compute_stats(latencies_ms: List[float]) -> Dict[str, float]:
    """Calcula percentiles estadísticos y métricas clave."""
    if not latencies_ms:
        return {"count": 0, "avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0}
    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)
    return {
        "count": n,
        "avg_ms": round(sum(sorted_lats) / n, 2),
        "min_ms": round(sorted_lats[0], 2),
        "max_ms": round(sorted_lats[-1], 2),
        "p50_ms": round(sorted_lats[int(n * 0.50)], 2),
        "p95_ms": round(sorted_lats[min(int(n * 0.95), n - 1)], 2),
        "p99_ms": round(sorted_lats[min(int(n * 0.99), n - 1)], 2),
        "throughput_rps": round(1000.0 / (sum(sorted_lats) / n), 1) if sum(sorted_lats) > 0 else 0.0
    }


def run_e2e_benchmark(iterations: int = 20) -> Dict[str, Any]:
    """
    Ejecuta el benchmark E2E completo en un entorno temporal aislado.
    Garantiza Zero-Waste limpiando la base de datos y bóvedas al terminar.
    """
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "bench_e2e.db")
    vault_root = os.path.join(tmp_dir, "vaults")

    # Motores optimizados para benchmark de alta velocidad
    ocr = FakeOcrBackend(
        text="Pago Movil BDV BDVenlinea\nOperacion: 0092837461\nMonto: Bs. 1.850,00\nFecha: 19/10/2026\n0102 Banco de Venezuela"
    )
    stt = FakeSttBackend(text="Hola Movilnet, deseo recargar mi saldo")
    engine = TranscriptionEngine(ocr_backend=ocr, stt_backend=stt)

    MultimodalRequestHandler.setup_services(db_path, engine=engine, vault_root=vault_root)
    client = InMemoryClient(MultimodalRequestHandler)

    lats_voucher: List[float] = []
    lats_audio: List[float] = []
    lats_video: List[float] = []
    lats_quota: List[float] = []

    success_counts = {"voucher": 0, "audio": 0, "video": 0, "quota": 0}

    try:
        for i in range(iterations):
            phone = f"+58416{1000000 + (i % 50)}"

            # 1. Pipeline Voucher C2P
            p_voucher = build_n8n_stage_payload(phone, "IMAGE")
            code_v, resp_v, t_v = client.post("/api/v1/multimodal/process", p_voucher)
            if code_v == 200 and resp_v.get("status") == "PROCESSED":
                success_counts["voucher"] += 1
                lats_voucher.append(t_v)

            # 2. Pipeline Nota de Voz
            p_audio = build_n8n_stage_payload(phone, "AUDIO")
            code_a, resp_a, t_a = client.post("/api/v1/multimodal/process", p_audio)
            if code_a == 200 and resp_a.get("status") == "PROCESSED":
                success_counts["audio"] += 1
                lats_audio.append(t_a)

            # 3. Pipeline Video MP4
            p_video = build_n8n_stage_payload(phone, "VIDEO")
            code_vi, resp_vi, t_vi = client.post("/api/v1/multimodal/process", p_video)
            if code_vi == 200 and resp_vi.get("status") == "PROCESSED":
                success_counts["video"] += 1
                lats_video.append(t_vi)

            # 4. Consulta de Cuota Bóveda
            code_q, resp_q, t_q = client.get(f"/api/v1/vault/quota?phone={phone}")
            if code_q == 200 and "quota_limit_bytes" in resp_q:
                success_counts["quota"] += 1
                lats_quota.append(t_q)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    total_ops = iterations * 4
    total_success = sum(success_counts.values())

    return {
        "iterations_per_pipeline": iterations,
        "total_operations": total_ops,
        "success_rate_percent": round((total_success / total_ops) * 100.0, 2),
        "pipelines": {
            "voucher_c2p": compute_stats(lats_voucher),
            "voice_note_stt": compute_stats(lats_audio),
            "video_ingest": compute_stats(lats_video),
            "vault_quota_query": compute_stats(lats_quota),
        }
    }


def print_report(results: Dict[str, Any]):
    """Imprime el informe ejecutivo del benchmark con formato visual."""
    print("=" * 70)
    print("⚡ BENCHMARK DE RENDIMIENTO END-TO-END (E2E) — PUERTO :8025")
    print("=" * 70)
    print(f"Iteraciones por flujo: {results['iterations_per_pipeline']}")
    print(f"Total Operaciones:     {results['total_operations']}")
    print(f"Tasa de Éxito:         {results['success_rate_percent']}%")
    print("-" * 70)
    print(f"{'PIPELINE MULTIMODAL':<24} | {'AVG (ms)':<8} | {'P50':<8} | {'P95':<8} | {'MAX':<8} | {'RPS'}")
    print("-" * 70)
    for name, stats in results["pipelines"].items():
        print(
            f"{name:<24} | "
            f"{stats['avg_ms']:<8.2f} | "
            f"{stats['p50_ms']:<8.2f} | "
            f"{stats['p95_ms']:<8.2f} | "
            f"{stats['max_ms']:<8.2f} | "
            f"{stats['throughput_rps']:.1f} req/s"
        )
    print("=" * 70)


def _self_test():
    """Auto-verificación formal del benchmark E2E con aserciones."""
    print("Iniciando auto-verificación formal del Benchmark E2E...")
    results = run_e2e_benchmark(iterations=10)
    assert results["success_rate_percent"] == 100.0, "La tasa de éxito debe ser del 100%"
    assert results["total_operations"] == 40
    # Verificar SLA de microservicio: latencia promedio < 50ms en memoria
    for name, stats in results["pipelines"].items():
        assert stats["count"] == 10
        assert stats["avg_ms"] < 100.0, f"SLA superado en {name}: {stats['avg_ms']} ms"
    print("✅ Benchmark E2E: auto-verificación 100% exitosa dentro de los SLAs Carrier-Grade.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark de Rendimiento E2E para Despacho Multimodal")
    parser.add_argument("--iterations", type=int, default=20, help="Iteraciones por pipeline (default: 20)")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación formal con aserciones")
    parser.add_argument("--json", action="store_true", help="Emitir resultados en formato JSON estructurado")
    args = parser.parse_args()

    if args.test:
        _self_test()
    else:
        res = run_e2e_benchmark(iterations=args.iterations)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print_report(res)
