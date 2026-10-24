#!/usr/bin/env python3
"""
scripts/run_e2e_real_channels_stress.py — Generador de Tráfico Concurrente E2E y Auditoría Omnicanal
==================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Hito: Fase 4 — Paso 4: Auditoría Integral de Accesibilidad (a11y) & Suite E2E Omnicanal Masivo.
"""

import concurrent.futures
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.service import MovilnetAPIService
from api.webhook_bridge import DEFAULT_WEBHOOK_SECRET, HMACSignatureValidator


class OmnichannelE2ETrafficRunner:
    """
    Simulador de alta fidelidad de tráfico concurrente masivo en canales reales:
    WhatsApp Business API, Telegram Bot, PWA Mobile Client y OCS Balances.
    """

    WEBHOOK_SECRET = DEFAULT_WEBHOOK_SECRET
    KNOWN_MSISDNS = [
        "04160000001",
        "04160000003",
        "04160000004",
        "04160000005",
        "04160000007"
    ]

    def __init__(self, service: MovilnetAPIService = None):
        self.service = service or MovilnetAPIService()

    def generate_hmac_signature(self, body_bytes: bytes, timestamp_str: str) -> str:
        """Calcula firma HMAC-SHA256 según estándar de seguridad de Movilnet."""
        return HMACSignatureValidator.generate_signature(body_bytes, self.WEBHOOK_SECRET, timestamp_str)

    def simulate_whatsapp_request(self, msisdn: str, text: str, idx: int) -> Tuple[int, float, Dict[str, Any]]:
        """Simula mensaje entrante vía webhook de WhatsApp Business con firma HMAC y Anti-Replay."""
        now_ts = str(int(time.time()))
        delivery_id = f"wa-e2e-dlv-{idx}-{now_ts}-{os.urandom(4).hex()}"
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "WHATSAPP_ENT_01",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "584160000000", "phone_number_id": "PNID_01"},
                        "contacts": [{"profile": {"name": f"Abonado_{idx}"}, "wa_id": msisdn}],
                        "messages": [{
                            "from": msisdn,
                            "id": f"wamid-{idx}-{now_ts}",
                            "timestamp": now_ts,
                            "text": {"body": text},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self.generate_hmac_signature(body_bytes, now_ts)
        headers = {
            "Content-Type": "application/json",
            "X-Movilnet-Signature": sig,
            "X-Movilnet-Timestamp": now_ts,
            "X-Movilnet-Delivery-ID": delivery_id,
            "X-Movilnet-Event-Type": "whatsapp.inbound"
        }

        t0 = time.perf_counter()
        status, resp_headers, resp_bytes = self.service.dispatch(
            "POST", "/api/v1/webhooks/inbound-events", headers, body_bytes
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        resp_data = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
        return status, elapsed_ms, resp_data

    def simulate_telegram_request(self, chat_id: int, msisdn: str, text: str, idx: int) -> Tuple[int, float, Dict[str, Any]]:
        """Simula mensaje entrante desde webhook del bot oficial de Telegram."""
        now_ts = str(int(time.time()))
        delivery_id = f"tg-e2e-dlv-{idx}-{now_ts}-{os.urandom(4).hex()}"
        payload = {
            "update_id": 900000 + idx,
            "message": {
                "message_id": 10000 + idx,
                "from": {"id": chat_id, "first_name": f"User_{idx}", "is_bot": False},
                "chat": {"id": chat_id, "type": "private"},
                "date": int(now_ts),
                "text": text,
                "contact": {"phone_number": msisdn, "first_name": f"User_{idx}"}
            }
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self.generate_hmac_signature(body_bytes, now_ts)
        headers = {
            "Content-Type": "application/json",
            "X-Movilnet-Signature": sig,
            "X-Movilnet-Timestamp": now_ts,
            "X-Movilnet-Delivery-ID": delivery_id,
            "X-Movilnet-Event-Type": "telegram.inbound"
        }

        t0 = time.perf_counter()
        status, resp_headers, resp_bytes = self.service.dispatch(
            "POST", "/api/v1/webhooks/inbound-events", headers, body_bytes
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        resp_data = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
        return status, elapsed_ms, resp_data

    def simulate_pwa_c2p_recharge(self, msisdn: str, amount_ves: float, bank_code: str, idx: int) -> Tuple[int, float, Dict[str, Any]]:
        """Simula una recarga financiera instantánea desde la interfaz Mi Movilnet PWA."""
        ref_id = f"PWA-E2E-{idx}-{int(time.time())}-{os.urandom(3).hex()}"
        payload = {
            "reference_id": ref_id,
            "msisdn": msisdn,
            "bank_code": bank_code,
            "amount_ves": amount_ves,
            "payer_cid": "V-10000001",
            "otp_token": "123456"
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        t0 = time.perf_counter()
        status, resp_headers, resp_bytes = self.service.dispatch(
            "POST", "/api/v1/payments/c2p", headers, body_bytes
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        resp_data = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
        return status, elapsed_ms, resp_data

    def simulate_pwa_balance_query(self, msisdn: str, idx: int) -> Tuple[int, float, Dict[str, Any]]:
        """Simula una consulta de saldo OCS en tiempo real desde la PWA."""
        payload = {"msisdn": msisdn}
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        t0 = time.perf_counter()
        status, resp_headers, resp_bytes = self.service.dispatch(
            "POST", "/api/v1/subscribers/balance", headers, body_bytes
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        resp_data = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
        return status, elapsed_ms, resp_data

    def run_stress_suite(self, total_requests: int = 100, max_workers: int = 10) -> Dict[str, Any]:
        """
        Ejecuta ráfagas concurrentes distribuidas en los 4 canales reales del sistema:
        - WhatsApp (25%)
        - Telegram (25%)
        - PWA Balance OCS (25%)
        - PWA Recarga C2P (25%)
        """
        latencies: List[float] = []
        statuses: Dict[int, int] = {}
        channel_counts = {"whatsapp": 0, "telegram": 0, "pwa_balance": 0, "pwa_c2p": 0}

        queries_pool = [
            "Consultar mi saldo disponible",
            "¿Cuáles son los planes 4GMAX?",
            "Quiero recargar saldo a mi número 0416",
            "¿Cuántos megas me quedan?",
            "Estado de mi línea Movilnet"
        ]
        banks_pool = ["0102", "0134", "0105", "0108"]

        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(total_requests):
                phone = self.KNOWN_MSISDNS[i % len(self.KNOWN_MSISDNS)]
                mod = i % 4
                if mod == 0:
                    text = queries_pool[i % len(queries_pool)]
                    futures.append(executor.submit(self.simulate_whatsapp_request, phone, text, i))
                    channel_counts["whatsapp"] += 1
                elif mod == 1:
                    text = queries_pool[(i + 1) % len(queries_pool)]
                    futures.append(executor.submit(self.simulate_telegram_request, 50000 + i, phone, text, i))
                    channel_counts["telegram"] += 1
                elif mod == 2:
                    futures.append(executor.submit(self.simulate_pwa_balance_query, phone, i))
                    channel_counts["pwa_balance"] += 1
                else:
                    amt = 50.0 + (i % 5) * 25.0
                    bank = banks_pool[i % len(banks_pool)]
                    futures.append(executor.submit(self.simulate_pwa_c2p_recharge, phone, amt, bank, i))
                    channel_counts["pwa_c2p"] += 1

            for f in concurrent.futures.as_completed(futures):
                try:
                    status, elap, data = f.result()
                    latencies.append(elap)
                    statuses[status] = statuses.get(status, 0) + 1
                except Exception as e:
                    statuses[500] = statuses.get(500, 0) + 1

        total_duration = time.perf_counter() - start_time
        latencies.sort()
        count = len(latencies)
        avg_lat = sum(latencies) / count if count > 0 else 0.0
        p50 = latencies[int(count * 0.50)] if count > 0 else 0.0
        p95 = latencies[int(count * 0.95)] if count > 0 else 0.0
        p99 = latencies[int(count * 0.99)] if count > 0 else 0.0
        tps = count / total_duration if total_duration > 0 else 0.0

        return {
            "total_requests": count,
            "duration_seconds": round(total_duration, 4),
            "throughput_tps": round(tps, 2),
            "status_distribution": statuses,
            "success_rate_pct": round((statuses.get(200, 0) / count) * 100.0, 2) if count > 0 else 0.0,
            "channels_executed": channel_counts,
            "latencies_ms": {
                "min": round(latencies[0], 3) if count > 0 else 0.0,
                "avg": round(avg_lat, 3),
                "p50": round(p50, 3),
                "p95": round(p95, 3),
                "p99": round(p99, 3),
                "max": round(latencies[-1], 3) if count > 0 else 0.0
            }
        }


if __name__ == "__main__":
    runner = OmnichannelE2ETrafficRunner()
    print("🚀 Iniciando prueba piloto de tráfico concurrente omnicanal (100 transacciones)...")
    res = runner.run_stress_suite(total_requests=100, max_workers=10)
    print(json.dumps(res, indent=2))
