#!/usr/bin/env python3
"""
scripts/measure_fastpath_latency.py — Medidor de Latencia Real del Fast-Path Telco
==================================================================================
Proyecto: AI_Movilnet_300926 — Gobernanza ZH-MHEP (toda cifra debe provenir de medición).

Mide, con time.perf_counter, la latencia del despachador determinista
(N8nDispatcherAgent.process_inbound_webhook) para casos multicarrier y emite
un reporte JSON con mediana, p95, máximo, intención resuelta y costo en tokens.

Uso:
    python scripts/measure_fastpath_latency.py --demo            # tabla legible
    python scripts/measure_fastpath_latency.py --json --runs 500 # JSON con sello SHA-256
    python scripts/measure_fastpath_latency.py --test            # auto-verificación
"""

import argparse
import hashlib
import json
import statistics
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.agents.agent_n8n_dispatcher import N8nDispatcherAgent  # noqa: E402


@dataclass(frozen=True)
class Case:
    phone: str
    carrier: str
    message: str


@dataclass(frozen=True)
class Measurement:
    phone: str
    carrier: str
    intent: str
    latency_mode: str
    tokens_cost_usd: float
    runs: int
    median_ms: float
    p95_ms: float
    max_ms: float


CASES: List[Case] = [
    Case("04165551234", "Movilnet", "Hola, deseo consultar mi saldo disponible"),
    Case("04140000002", "Movistar", "Cuál es mi contrato y plan activo?"),
    Case("04129998877", "Digitel", "Necesito hacer una recarga por pago móvil c2p"),
    Case("04261112233", "Movilnet", "Me robaron el teléfono, necesito bloqueo imei urgente"),
]


def _payload(case: Case) -> dict:
    return {
        "event": "messages.upsert",
        "instance": "Viki LPGTEC",
        "data": {
            "key": {"remoteJid": f"58{case.phone[1:]}@s.whatsapp.net", "id": f"LAT-{case.phone}"},
            "pushName": "Medicion",
            "message": {"conversation": case.message},
        },
    }


def measure_case(agent: N8nDispatcherAgent, case: Case, runs: int) -> Measurement:
    """Mide `runs` ejecuciones tras 5 de calentamiento. Rechaza runs < 1 (invariante)."""
    if runs < 1:
        raise ValueError("runs debe ser >= 1")
    for _ in range(5):
        agent.process_inbound_webhook(_payload(case))
    samples: List[float] = []
    res: dict = {}
    for _ in range(runs):
        t0 = time.perf_counter()
        res = agent.process_inbound_webhook(_payload(case))
        samples.append((time.perf_counter() - t0) * 1000.0)
    samples.sort()
    p95 = samples[min(len(samples) - 1, int(len(samples) * 0.95))]
    return Measurement(
        phone=case.phone, carrier=case.carrier,
        intent=str(res.get("intent")), latency_mode=str(res.get("latency_mode")),
        tokens_cost_usd=float(res.get("tokens_cost_usd", -1.0)), runs=runs,
        median_ms=round(statistics.median(samples), 3),
        p95_ms=round(p95, 3), max_ms=round(samples[-1], 3),
    )


def measure_all(runs: int) -> List[Measurement]:
    agent = N8nDispatcherAgent()
    return [measure_case(agent, c, runs) for c in CASES]


def seal(items: List[Measurement]) -> str:
    blob = json.dumps([asdict(m) for m in items], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def run_self_test() -> bool:
    items = measure_all(runs=20)
    assert len(items) == len(CASES)
    for m in items:
        assert m.latency_mode == "FAST_PATH_DETERMINISTIC", m
        assert m.tokens_cost_usd == 0.0, m
        assert 0.0 < m.median_ms < 50.0, m
    try:
        measure_case(N8nDispatcherAgent(), CASES[0], 0)
    except ValueError:
        pass
    else:
        raise AssertionError("runs=0 debió ser rechazado")
    print("✅ [MEDIDOR LATENCIA]: auto-verificación 100% OK")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Medidor de latencia real del Fast-Path Telco")
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--out", type=Path, default=None, help="Guardar reporte JSON sellado en esta ruta")
    a = ap.parse_args()
    if a.test:
        run_self_test()
    elif a.out:
        data = measure_all(a.runs)
        a.out.write_text(json.dumps({"measurements": [asdict(m) for m in data], "sha256": seal(data)},
                                    indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Reporte guardado en {a.out} (sha256={seal(data)})")
    elif a.json or a.demo:
        data = measure_all(a.runs)
        if a.json:
            print(json.dumps({"measurements": [asdict(m) for m in data], "sha256": seal(data)},
                             indent=2, ensure_ascii=False))
        else:
            print(f"{'Línea':<13}{'Operadora':<10}{'Intención':<16}{'Mediana ms':>11}{'P95 ms':>9}{'Max ms':>9}  Tokens")
            for m in data:
                print(f"{m.phone:<13}{m.carrier:<10}{m.intent:<16}{m.median_ms:>11}{m.p95_ms:>9}{m.max_ms:>9}  {m.tokens_cost_usd}")
            print(f"SHA-256: {seal(data)}  (runs={a.runs})")
    else:
        ap.print_help()
