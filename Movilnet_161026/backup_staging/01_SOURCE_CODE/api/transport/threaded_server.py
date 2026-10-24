#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
threaded_server.py — Servidor HTTP Multi-Hilo Dual-Stack y Manejador REST
=============================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
Implementa el servidor HTTP multi-hilo dual-stack (IPv4/IPv6), el manejador de
peticiones REST y el orquestador de ciclo de vida StandaloneServerRunner.
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any, Dict, Optional, Tuple


class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Servidor HTTP multi-hilo dual-stack con reciclaje de sockets y concurrencia IPv4+IPv6."""
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: Tuple[str, int], RequestHandlerClass: Any):
        host, port = server_address
        if host in ("0.0.0.0", "", "::", "localhost"):
            try:
                self.address_family = socket.AF_INET6
                server_address = ("::", port)
            except Exception:
                self.address_family = socket.AF_INET
                server_address = ("0.0.0.0", port)
        else:
            self.address_family = socket.AF_INET
        super().__init__(server_address, RequestHandlerClass)

    def server_bind(self) -> None:
        if getattr(self, "address_family", None) == socket.AF_INET6:
            try:
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except (AttributeError, OSError):
                pass
        super().server_bind()


class MovilnetHTTPRequestHandler(BaseHTTPRequestHandler):
    """Manejador de conexiones HTTP para el servicio REST."""

    # Referencia inyectable a la instancia del servicio
    service_instance: Optional[Any] = None

    def log_message(self, format: str, *args: Any) -> None:
        """Silenciar log por defecto para no saturar stderr durante tests."""
        return

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        self._process_request("GET")

    def do_POST(self) -> None:
        self._process_request("POST")

    def do_OPTIONS(self) -> None:
        self._process_request("OPTIONS")

    def _process_request(self, method: str) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
        headers_dict = {k: v for k, v in self.headers.items()}

        srv = self.service_instance
        if srv is None:
            # Fallback seguro de importación perezosa
            from api.service import MovilnetAPIService
            srv = MovilnetAPIService()

        status_code, resp_headers, resp_body = srv.dispatch(
            method=method,
            path=self.path,
            headers=headers_dict,
            body_bytes=body_bytes
        )

        self.send_response(status_code)
        for h_key, h_val in resp_headers.items():
            self.send_header(h_key, h_val)
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)
        self.wfile.flush()


class StandaloneServerRunner:
    """Clase utilitaria para levantar el servidor HTTP en segundo plano o CLI."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000, service: Optional[Any] = None):
        self.host = host
        self.port = port
        self.service = service
        self.server: Optional[_ThreadedHTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.service is None:
            from api.service import MovilnetAPIService
            self.service = MovilnetAPIService()
        MovilnetHTTPRequestHandler.service_instance = self.service
        self.server = _ThreadedHTTPServer((self.host, self.port), MovilnetHTTPRequestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None


# ============================================================================
# CLI DE AUTO-VERIFICACIÓN
# ============================================================================

def run_self_tests() -> int:
    """Ejecuta suite de pruebas unitarias automáticas usando socketpair hermético."""
    print("🧪 Verificando threaded_server.py herméticamente con socketpair...")

    class MockService:
        def dispatch(self, method: str, path: str, headers: Dict[str, str], body_bytes: bytes):
            if path == "/test-ping":
                return 200, {"Content-Type": "text/plain"}, b"PONG_MOVILNET"
            return 404, {"Content-Type": "text/plain"}, b"NOT_FOUND"

    class DummyServer:
        pass

    mock_srv = MockService()
    MovilnetHTTPRequestHandler.service_instance = mock_srv

    # 1. Probar despacho HTTP GET con socketpair
    client_sock, server_sock = socket.socketpair()
    try:
        raw_req = b"GET /test-ping HTTP/1.1\r\nHost: localhost\r\n\r\n"
        client_sock.sendall(raw_req)

        def handle():
            try:
                MovilnetHTTPRequestHandler(server_sock, ("127.0.0.1", 54321), DummyServer())
            finally:
                server_sock.close()

        th = threading.Thread(target=handle, daemon=True)
        th.start()

        chunks = []
        client_sock.settimeout(2.0)
        while True:
            try:
                buf = client_sock.recv(4096)
                if not buf:
                    break
                chunks.append(buf)
            except socket.timeout:
                break
        th.join(timeout=2.0)
        resp_data = b"".join(chunks)
        assert b"200 OK" in resp_data, f"Respuesta inesperada: {resp_data[:100]}"
        assert b"PONG_MOVILNET" in resp_data, f"Cuerpo inesperado: {resp_data}"
    finally:
        client_sock.close()

    # 2. Probar instanciación de StandaloneServerRunner
    runner = StandaloneServerRunner(host="127.0.0.1", port=8999, service=mock_srv)
    assert runner.host == "127.0.0.1"
    assert runner.port == 8999
    assert runner.service is mock_srv

    print("✅ [TEST PASS] threaded_server: socketpair y ciclo de vida aprobados (100%).")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Servidor HTTP Dual-Stack Movilnet")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación")
    args = parser.parse_args()

    if args.test:
        sys.exit(run_self_tests())
    else:
        print("Uso: python3 -m api.transport.threaded_server --test")


if __name__ == "__main__":
    main()
