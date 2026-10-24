#!/usr/bin/env python3
"""
test_phase2_api.py — Suite de Pruebas Automatizadas para la API REST & Contrato OpenAPI 3.1
========================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Fase 2: Paso 1 — Certificación de Microservicios REST y Contrato OpenAPI 3.1
Estándares: TM Forum ODA (TMF620, TMF622, TMF632, TMF676, TMF678, TMF680)
"""

import sys
import json
import time
import uuid
import socket
import unittest
import threading
from pathlib import Path
from typing import Dict, Any, Tuple

# Inclusión del directorio raíz
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.service import (
    MovilnetAPIService,
    InputValidator,
    MovilnetHTTPRequestHandler,
    get_openapi_specification,
    export_openapi_json
)
from db.repository import MovilnetRepository
from db.connection import compute_blind_index


class TestInputValidator(unittest.TestCase):
    """Pruebas unitarias para validación y sanitización defensiva de entradas."""

    def test_normalize_msisdn_valid(self):
        cases = [
            ("04161234567", "04161234567"),
            ("04269876543", "04269876543"),
            ("+584161234567", "04161234567"),
            ("584269876543", "04269876543"),
            ("0416-123-4567", "04161234567"),
            (" 0426 987 6543 ", "04269876543"),
        ]
        for inp, expected in cases:
            self.assertEqual(InputValidator.normalize_msisdn(inp), expected)

    def test_normalize_msisdn_invalid(self):
        invalid = ["04141234567", "04121234567", "12345", "abcdefg", "", None, "0416123456"]
        for inp in invalid:
            self.assertIsNone(InputValidator.normalize_msisdn(inp))

    def test_normalize_cid_valid(self):
        cases = [
            ("V-12345678", "V-12345678"),
            ("v12345678", "V-12345678"),
            ("12345678", "V-12345678"),
            ("E-87654321", "E-87654321"),
            ("J-309998881", "J-309998881"),
            (" V-10.000.001 ", "V-10000001"),
        ]
        for inp, expected in cases:
            self.assertEqual(InputValidator.normalize_cid(inp), expected)

    def test_normalize_cid_invalid(self):
        invalid = ["", None, "ABC", "123", "V-XYZ"]
        for inp in invalid:
            self.assertIsNone(InputValidator.normalize_cid(inp))

    def test_validate_amount(self):
        self.assertEqual(InputValidator.validate_amount("150.50"), 150.50)
        self.assertEqual(InputValidator.validate_amount(100), 100.0)
        self.assertIsNone(InputValidator.validate_amount(0))
        self.assertIsNone(InputValidator.validate_amount(-50))
        self.assertIsNone(InputValidator.validate_amount("invalido"))
        self.assertIsNone(InputValidator.validate_amount(None))


class TestOpenApiSpecification(unittest.TestCase):
    """Validación del Contrato OpenAPI 3.1.0 conforme a TM Forum ODA."""

    def setUp(self):
        self.spec = get_openapi_specification()

    def test_openapi_version_and_info(self):
        self.assertEqual(self.spec["openapi"], "3.1.0")
        self.assertIn("info", self.spec)
        self.assertEqual(self.spec["info"]["title"], "Movilnet Telco & FinTech Core API")
        self.assertIn("version", self.spec["info"])
        self.assertIn("contact", self.spec["info"])

    def test_required_paths_present(self):
        paths = self.spec["paths"]
        expected_paths = [
            "/health",
            "/api/v1/health",
            "/api/v1/status",
            "/api/v1/subscribers/balance",
            "/api/v1/payments/c2p",
            "/api/v1/security/sim-swap",
            "/api/v1/security/eir-lock",
            "/api/v1/catalog/plans",
            "/api/v1/catalog/plans/{plan_id}",
            "/api/v1/banks",
            "/openapi.json"
        ]
        for p in expected_paths:
            self.assertIn(p, paths, f"Ruta {p} debe existir en OpenAPI spec")

    def test_schemas_components(self):
        schemas = self.spec["components"]["schemas"]
        expected_schemas = [
            "HealthResponse",
            "SubscriberBalanceRequest",
            "SubscriberBalanceResponse",
            "C2PPaymentRequest",
            "C2PPaymentResponse",
            "SimSwapAuditRequest",
            "SimSwapAuditResponse",
            "EirLockRequest",
            "EirLockResponse",
            "ProductPlan",
            "BankSudeban",
            "ErrorResponse"
        ]
        for s in expected_schemas:
            self.assertIn(s, schemas, f"Schema {s} debe existir en components.schemas")

    def test_export_openapi_json_file(self):
        out_path = export_openapi_json()
        self.assertTrue(out_path.exists())
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["openapi"], "3.1.0")
        self.assertEqual(data["info"]["title"], "Movilnet Telco & FinTech Core API")


class TestMovilnetAPIDispatcher(unittest.TestCase):
    """Pruebas unitarias directas sobre el despachador de la API (In-Memory Fast Tests)."""

    @classmethod
    def setUpClass(cls):
        cls.repo = MovilnetRepository()
        cls.service = MovilnetAPIService(cls.repo)
        
        # Asegurar un abonado de prueba conocido
        cls.test_phone = "04169991122"
        cls.test_cid = "V-29991122"
        existing = cls.repo.get_subscriber_by_msisdn(cls.test_phone)
        if not existing:
            cls.repo.create_subscriber_with_line(
                cid=cls.test_cid,
                msisdn=cls.test_phone,
                plan_id="PLAN_10GB_4GMAX",
                balance_ves=125.50,
                quota_mb=10240
            )

    def _call(self, method: str, path: str, body: Any = None) -> Tuple[int, Dict[str, str], Any]:
        body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
        status, headers, resp_bytes = self.service.dispatch(method, path, {}, body_bytes)
        try:
            resp_data = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
        except Exception:
            resp_data = resp_bytes.decode("utf-8")
        return status, headers, resp_data

    # --- Health & Observabilidad ---

    def test_health_endpoint(self):
        status, headers, data = self._call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"]["status"], "CONNECTED")
        self.assertIn("uptime_seconds", data)

    def test_status_endpoint(self):
        status, headers, data = self._call("GET", "/api/v1/status")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["active_plans_count"], 1)
        self.assertGreaterEqual(data["sudeban_banks_count"], 1)
        self.assertAlmostEqual(data["bcv_official_rate_ves_usd"], 36.85, places=2)

    def test_openapi_json_endpoint(self):
        status, headers, data = self._call("GET", "/openapi.json")
        self.assertEqual(status, 200)
        self.assertEqual(data["openapi"], "3.1.0")

    def test_docs_swagger_ui_endpoint(self):
        status, headers, data = self._call("GET", "/docs")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("SwaggerUIBundle", data)

    # --- TMF678: Saldos y Cuotas ---

    def test_get_balance_by_msisdn_success(self):
        status, headers, data = self._call("POST", "/api/v1/subscribers/balance", {"msisdn": self.test_phone})
        self.assertEqual(status, 200)
        self.assertEqual(data["msisdn"], self.test_phone)
        self.assertEqual(data["plan_id"], "PLAN_10GB_4GMAX")
        self.assertGreaterEqual(data["balance_ves"], 0.0)
        self.assertIn("remaining_data_mb", data)
        self.assertIn("consumption_pct", data)

    def test_get_balance_by_cid_success(self):
        status, headers, data = self._call("POST", "/api/v1/subscribers/balance", {"cid": self.test_cid})
        self.assertEqual(status, 200)
        self.assertEqual(data["msisdn"], self.test_phone)

    def test_get_balance_invalid_msisdn(self):
        status, headers, data = self._call("POST", "/api/v1/subscribers/balance", {"msisdn": "04120000000"})
        self.assertEqual(status, 400)
        self.assertEqual(data["code"], "ERR_INVALID_MSISDN")

    def test_get_balance_not_found(self):
        status, headers, data = self._call("POST", "/api/v1/subscribers/balance", {"msisdn": "04169999999"})
        self.assertEqual(status, 404)
        self.assertEqual(data["code"], "ERR_NOT_FOUND")

    def test_get_balance_missing_parameters(self):
        status, headers, data = self._call("POST", "/api/v1/subscribers/balance", {})
        self.assertEqual(status, 400)
        self.assertEqual(data["code"], "ERR_BAD_REQUEST")

    # --- TMF676: Pasarela Financiera C2P ---

    def test_c2p_payment_success(self):
        ref = f"REF-TEST-{uuid.uuid4().hex[:8]}"
        initial_status, _, initial_bal = self._call("POST", "/api/v1/subscribers/balance", {"msisdn": self.test_phone})
        start_ves = initial_bal["balance_ves"]

        payload = {
            "reference_id": ref,
            "msisdn": self.test_phone,
            "bank_code": "0102",  # Banco de Venezuela
            "amount_ves": 50.00,
            "payer_cid": self.test_cid,
            "otp_token": "123456"
        }
        status, headers, data = self._call("POST", "/api/v1/payments/c2p", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "COMPLETADO")
        self.assertEqual(data["amount_ves"], 50.00)
        self.assertAlmostEqual(data["new_balance_ves"], start_ves + 50.00, places=2)

    def test_c2p_payment_duplicate_reference(self):
        ref = f"REF-DUP-{uuid.uuid4().hex[:8]}"
        payload = {
            "reference_id": ref,
            "msisdn": self.test_phone,
            "bank_code": "0102",
            "amount_ves": 30.00,
            "payer_cid": self.test_cid,
            "otp_token": "654321"
        }
        # Primer cobro: Éxito
        status1, _, _ = self._call("POST", "/api/v1/payments/c2p", payload)
        self.assertEqual(status1, 200)

        # Segundo cobro con la misma referencia: Debe retornar 409 Conflicto
        status2, _, data2 = self._call("POST", "/api/v1/payments/c2p", payload)
        self.assertEqual(status2, 409)
        self.assertEqual(data2["code"], "ERR_DUPLICATE_REFERENCE")

    def test_c2p_payment_invalid_amount(self):
        payload = {
            "reference_id": f"REF-INV-{uuid.uuid4().hex[:6]}",
            "msisdn": self.test_phone,
            "bank_code": "0102",
            "amount_ves": -25.00,
            "payer_cid": self.test_cid,
            "otp_token": "112233"
        }
        status, _, data = self._call("POST", "/api/v1/payments/c2p", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["code"], "ERR_INVALID_AMOUNT")

    def test_c2p_payment_invalid_bank_code(self):
        payload = {
            "reference_id": f"REF-BANK-{uuid.uuid4().hex[:6]}",
            "msisdn": self.test_phone,
            "bank_code": "9999",  # Banco inexistente
            "amount_ves": 40.00,
            "payer_cid": self.test_cid,
            "otp_token": "112233"
        }
        status, _, data = self._call("POST", "/api/v1/payments/c2p", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["code"], "ERR_BANK_NOT_SUPPORTED")

    def test_c2p_payment_invalid_otp(self):
        payload = {
            "reference_id": f"REF-OTP-{uuid.uuid4().hex[:6]}",
            "msisdn": self.test_phone,
            "bank_code": "0102",
            "amount_ves": 20.00,
            "payer_cid": self.test_cid,
            "otp_token": "12"  # Muy corto
        }
        status, _, data = self._call("POST", "/api/v1/payments/c2p", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["code"], "ERR_INVALID_OTP")

    # --- TMF680: Seguridad SIM-Swap & Bloqueo EIR ---

    def test_sim_swap_audit_nominal(self):
        status, _, data = self._call("POST", "/api/v1/security/sim-swap", {"msisdn": self.test_phone})
        self.assertEqual(status, 200)
        self.assertEqual(data["msisdn"], self.test_phone)
        self.assertIn("sim_swap_detected_24h", data)
        self.assertIn("risk_level", data)
        self.assertIn("otp_allowed", data)

    def test_sim_swap_audit_invalid_msisdn(self):
        status, _, data = self._call("POST", "/api/v1/security/sim-swap", {"msisdn": "invalid"})
        self.assertEqual(status, 400)
        self.assertEqual(data["code"], "ERR_INVALID_MSISDN")

    def test_eir_lock_terminal_nominal(self):
        victim_phone = "04268881122"
        existing = self.repo.get_subscriber_by_msisdn(victim_phone)
        if not existing:
            self.repo.create_subscriber_with_line(
                cid="V-28881122",
                msisdn=victim_phone,
                plan_id="PLAN_3GB_LIGERO",
                balance_ves=10.0
            )

        payload = {
            "msisdn": victim_phone,
            "imei": "358901234567890",
            "imsi": "734068881122001",
            "reason": "ROBO_ARMADO_TRANSPORTE",
            "police_report": "CICPC-DEL-2026-991"
        }
        status, _, data = self._call("POST", "/api/v1/security/eir-lock", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "LOCKED_IN_EIR")
        self.assertEqual(data["line_status"], "BLOQUEADO_ROBO")
        self.assertIn("ticket_id", data)

        # Verificar que la línea efectivamente quedó BLOQUEADO_ROBO en DB
        line_after = self.repo.get_line_details(victim_phone)
        self.assertEqual(line_after["status"], "BLOQUEADO_ROBO")

        # Verificar que no permite cobros C2P sobre una línea bloqueada (HTTP 422)
        c2p_blocked = {
            "reference_id": f"REF-BLOCKED-{uuid.uuid4().hex[:6]}",
            "msisdn": victim_phone,
            "bank_code": "0102",
            "amount_ves": 100.0,
            "payer_cid": "V-28881122",
            "otp_token": "998877"
        }
        status_c2p, _, data_c2p = self._call("POST", "/api/v1/payments/c2p", c2p_blocked)
        self.assertEqual(status_c2p, 422)
        self.assertEqual(data_c2p["code"], "ERR_LINE_BLOCKED")

    # --- TMF620: Catálogo de Planes & Bancos ---

    def test_catalog_plans_list(self):
        status, _, data = self._call("GET", "/api/v1/catalog/plans")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["total_plans"], 16)
        first_plan = data["plans"][0]
        self.assertIn("plan_id", first_plan)
        self.assertIn("name", first_plan)
        self.assertIn("price_usd", first_plan)
        self.assertIn("price_ves_approx", first_plan)

    def test_catalog_plan_by_id(self):
        status, _, data = self._call("GET", "/api/v1/catalog/plans/PLAN_10GB_4GMAX")
        self.assertEqual(status, 200)
        self.assertEqual(data["plan_id"], "PLAN_10GB_4GMAX")
        self.assertEqual(data["data_quota_mb"], 10240)

    def test_catalog_plan_by_id_not_found(self):
        status, _, data = self._call("GET", "/api/v1/catalog/plans/PLAN_INEXISTENTE")
        self.assertEqual(status, 404)
        self.assertEqual(data["code"], "ERR_NOT_FOUND")

    def test_banks_list(self):
        status, _, data = self._call("GET", "/api/v1/banks")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["total_banks"], 20)
        codes = [b["bank_code"] for b in data["banks"]]
        self.assertIn("0102", codes)  # Banco de Venezuela
        self.assertIn("0105", codes)  # Mercantil
        self.assertIn("0134", codes)  # Banesco

    def test_route_not_found_404(self):
        status, _, data = self._call("GET", "/api/v1/ruta_que_no_existe")
        self.assertEqual(status, 404)
        self.assertEqual(data["code"], "ERR_ROUTE_NOT_FOUND")


class TestSocketProtocolIntegration(unittest.TestCase):
    """
    Pruebas del protocolo HTTP completo a través de streams de sockets reales
    usando socket.socketpair() para verificar el comportamiento de red sin violar
    las políticas de sandbox del sistema operativo.
    """

    class _DummyServer:
        pass

    def setUp(self):
        self.service = MovilnetAPIService()
        MovilnetHTTPRequestHandler.service_instance = self.service

    def _send_raw_http(self, raw_bytes: bytes) -> Tuple[int, Dict[str, str], bytes]:
        client_sock, server_sock = socket.socketpair()
        try:
            client_sock.settimeout(2.0)
            client_sock.sendall(raw_bytes)

            # Procesar la petición en el handler de forma concurrente para evitar deadlock de buffer
            def handle():
                try:
                    MovilnetHTTPRequestHandler(server_sock, ("127.0.0.1", 54321), self._DummyServer())
                finally:
                    server_sock.close()

            th = threading.Thread(target=handle, daemon=True)
            th.start()

            # Leer respuesta del socket
            response_chunks = []
            while True:
                try:
                    chunk = client_sock.recv(8192)
                    if not chunk:
                        break
                    response_chunks.append(chunk)
                except socket.timeout:
                    break

            th.join(timeout=2.0)
            full_response = b"".join(response_chunks)
            header_part, body_part = full_response.split(b"\r\n\r\n", 1)
            lines = header_part.decode("utf-8").split("\r\n")
            status_line = lines[0]
            status_code = int(status_line.split(" ")[1])
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
            return status_code, headers, body_part
        finally:
            client_sock.close()

    def test_socket_health_get(self):
        req = b"GET /health HTTP/1.0\r\nHost: localhost\r\n\r\n"
        status, headers, body = self._send_raw_http(req)
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "healthy")

    def test_socket_openapi_json_get(self):
        req = b"GET /openapi.json HTTP/1.0\r\nHost: localhost\r\n\r\n"
        status, headers, body = self._send_raw_http(req)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["openapi"], "3.1.0")

    def test_socket_balance_post(self):
        payload = json.dumps({"msisdn": "04160000001"}).encode("utf-8")
        req = (
            b"POST /api/v1/subscribers/balance HTTP/1.0\r\n"
            b"Host: localhost\r\n"
            b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8")
            + payload
        )
        status, headers, body = self._send_raw_http(req)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["msisdn"], "04160000001")

    def test_socket_404_not_found(self):
        req = b"GET /api/v1/ruta_inexistente HTTP/1.0\r\nHost: localhost\r\n\r\n"
        status, headers, body = self._send_raw_http(req)
        self.assertEqual(status, 404)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["code"], "ERR_ROUTE_NOT_FOUND")


class TestApiPerformanceAndConcurrency(unittest.TestCase):
    """Pruebas de estrés y latencia estricta (<25ms P95, <500ms total)."""

    @classmethod
    def setUpClass(cls):
        cls.repo = MovilnetRepository()
        cls.service = MovilnetAPIService(cls.repo)
        cls.test_phone = "04160000001"
        cls.test_cid = "V-10000001"
        cls.repo.update_line_status(cls.test_phone, "ACTIVO")

    def test_latency_balance_query_sub_millisecond(self):
        latencies = []
        for _ in range(50):
            t0 = time.perf_counter()
            status, _, _ = self.service.dispatch(
                "POST",
                "/api/v1/subscribers/balance",
                {},
                b'{"msisdn": "04160000001"}'
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            self.assertEqual(status, 200)

        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        avg = sum(latencies) / len(latencies)

        print(f"\n   ⚡ Latencia REST API: Promedio={avg:.3f}ms | P50={p50:.3f}ms | P95={p95:.3f}ms | Max={latencies[-1]:.3f}ms")
        self.assertLess(avg, 10.0, "La latencia promedio del microservicio debe ser inferior a 10ms")
        self.assertLess(p95, 25.0, "El percentil 95 debe responder en menos de 25ms")

    def test_multithreaded_concurrency(self):
        errors = []
        successes = []

        def worker(idx: int):
            ref = f"REF-CONCUR-{idx}-{uuid.uuid4().hex[:6]}"
            payload = json.dumps({
                "reference_id": ref,
                "msisdn": self.test_phone,
                "bank_code": "0102",
                "amount_ves": 1.00,
                "payer_cid": self.test_cid,
                "otp_token": "123456"
            }).encode("utf-8")
            status, _, data_bytes = self.service.dispatch("POST", "/api/v1/payments/c2p", {}, payload)
            if status == 200:
                successes.append(idx)
            else:
                errors.append((idx, status, data_bytes))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Ocurrieron errores en concurrencia: {errors}")
        self.assertEqual(len(successes), 10)


if __name__ == "__main__":
    unittest.main()
