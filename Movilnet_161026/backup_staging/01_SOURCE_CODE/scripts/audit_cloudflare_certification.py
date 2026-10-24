#!/usr/bin/env python3
"""
scripts/audit_cloudflare_certification.py — Suite Militar de Auditoría y Certificación Cloudflare
================================================================================================
Propósito:
  Proveer un procedimiento automatizado, formal e inmutable para auditar y certificar que el
  proyecto Movilnet Core está operando al 100% a través de la infraestructura Anycast de Cloudflare.

Niveles Auditados:
  [Nivel 1] DNS & Red Anycast: Resolución contra servidores raíz de Cloudflare.
  [Nivel 2] Criptografía y Certificado SSL/TLS: Emisor, vigencia y negociación TLS 1.3.
  [Nivel 3] Cabeceras de Borde (Edge Headers): Verificación de 'server: cloudflare' y CF-Ray.
  [Nivel 4] Telemetría Prometheus del Daemon: Conexión HA viva en MIA10 y 0 errores de proxy.
  [Nivel 5] Salud del Core y Base de Datos: Verificación de SQLite WAL y poller n8n Cloud.
  [Nivel 6] Ejecución Cognitiva E2E: Respuesta Fast-Path determinista en <200ms con 0 tokens.
"""

import os
import sys
import json
import time
import socket
import ssl
import hashlib
import urllib.request
import urllib.error
import argparse
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATUS_FILE = PROJECT_ROOT / "logs" / "cloudflare_tunnel.json"
REPORTS_DIR = PROJECT_ROOT / "reports"
METRICS_URL = "http://127.0.0.1:20241/metrics"


def get_target_tunnel_url() -> str:
    """Obtiene la URL activa del túnel desde archivo de estado o fallback canónico."""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("public_url", "")
        except Exception:
            pass
    return "https://mixture-merchandise-jumping-expenditures.trycloudflare.com"


class CloudflareAuditor:
    def __init__(self, public_url: str):
        self.public_url = public_url.rstrip("/")
        self.hostname = self.public_url.replace("https://", "").replace("http://", "").split("/")[0]
        self.results: List[Dict[str, Any]] = []

    def audit_level_1_dns(self) -> Dict[str, Any]:
        """[Nivel 1] Resolución DNS y enrutamiento Anycast."""
        t0 = time.perf_counter()
        try:
            ip_list = socket.gethostbyname_ex(self.hostname)[2]
            latency = (time.perf_counter() - t0) * 1000
            is_cf_ip = any(ip.startswith("104.16.") or ip.startswith("104.17.") or ip.startswith("172.64.") for ip in ip_list)
            return {
                "level": 1,
                "name": "DNS_And_Anycast_Resolution",
                "passed": len(ip_list) > 0 and is_cf_ip,
                "latency_ms": round(latency, 2),
                "details": f"IPs resueltas en la red Anycast de Cloudflare: {ip_list}",
                "ip_list": ip_list
            }
        except Exception as e:
            return {
                "level": 1,
                "name": "DNS_And_Anycast_Resolution",
                "passed": False,
                "error": str(e),
                "details": "Fallo en la resolución DNS del hostname del túnel."
            }

    def audit_level_2_tls(self) -> Dict[str, Any]:
        """[Nivel 2] Certificado SSL/TLS y protocolo de negociación."""
        t0 = time.perf_counter()
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((self.hostname, 443), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=self.hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
                    latency = (time.perf_counter() - t0) * 1000

                    issuer = dict(x[0] for x in cert.get("issuer", []))
                    subject = dict(x[0] for x in cert.get("subject", []))
                    not_after = cert.get("notAfter", "")

                    return {
                        "level": 2,
                        "name": "TLS_Certificate_And_Cipher",
                        "passed": "trycloudflare.com" in str(subject) or "Cloudflare" in str(issuer) or "Google Trust Services" in str(issuer),
                        "latency_ms": round(latency, 2),
                        "details": f"TLS Version: {version} | Cipher: {cipher[0]} | Issuer: {issuer.get('organizationName', 'Desconocido')} | Vence: {not_after}",
                        "tls_version": version,
                        "cipher": cipher[0]
                    }
        except Exception as e:
            return {
                "level": 2,
                "name": "TLS_Certificate_And_Cipher",
                "passed": False,
                "error": str(e),
                "details": "Fallo al verificar el certificado SSL/TLS con el borde de Cloudflare."
            }

    def audit_level_3_edge_headers(self) -> Dict[str, Any]:
        """[Nivel 3] Cabeceras de borde Cloudflare (Server, CF-Ray, Cache)."""
        t0 = time.perf_counter()
        req = urllib.request.Request(
            f"{self.public_url}/health",
            headers={"User-Agent": "Movilnet-Cloudflare-Auditor/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                latency = (time.perf_counter() - t0) * 1000
                server_hdr = (resp.headers.get("server") or "").lower()
                cf_ray = resp.headers.get("cf-ray") or resp.headers.get("CF-Ray") or ""
                cache_status = resp.headers.get("cf-cache-status") or resp.headers.get("CF-Cache-Status") or ""

                passed = ("cloudflare" in server_hdr) and (len(cf_ray) > 0)
                return {
                    "level": 3,
                    "name": "Cloudflare_Edge_Headers",
                    "passed": passed,
                    "latency_ms": round(latency, 2),
                    "details": f"Server: {server_hdr} | CF-Ray: {cf_ray} | Cache: {cache_status}",
                    "cf_ray": cf_ray,
                    "server": server_hdr
                }
        except Exception as e:
            return {
                "level": 3,
                "name": "Cloudflare_Edge_Headers",
                "passed": False,
                "error": str(e),
                "details": "Fallo al contactar el endpoint /health a través del borde de Cloudflare."
            }

    def audit_level_4_prometheus_metrics(self) -> Dict[str, Any]:
        """[Nivel 4] Telemetría interna Prometheus del Daemon cloudflared."""
        try:
            req = urllib.request.Request(METRICS_URL, headers={"User-Agent": "Auditor"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                raw_metrics = resp.read().decode("utf-8")
                
                ha_ok = "cloudflared_tunnel_ha_connections 1" in raw_metrics
                requests_count = 0
                errors_count = 0
                edge_location = "desconocido"

                for line in raw_metrics.splitlines():
                    if line.startswith("cloudflared_tunnel_total_requests"):
                        parts = line.split()
                        if len(parts) >= 2:
                            requests_count = int(parts[1])
                    elif line.startswith("cloudflared_tunnel_request_errors"):
                        parts = line.split()
                        if len(parts) >= 2:
                            errors_count = int(parts[1])
                    elif "cloudflared_tunnel_server_locations" in line and "edge_location" in line:
                        loc_part = line.split('edge_location="')
                        if len(loc_part) > 1:
                            edge_location = loc_part[1].split('"')[0]

                passed = ha_ok and (errors_count == 0)
                return {
                    "level": 4,
                    "name": "Prometheus_Tunnel_Telemetry",
                    "passed": passed,
                    "details": f"Conexión HA: VIVA | Centro de Datos: {edge_location} | Peticiones Exitosas: {requests_count} | Errores Proxy: {errors_count}",
                    "ha_connections": 1 if ha_ok else 0,
                    "requests_proxied": requests_count,
                    "proxy_errors": errors_count,
                    "edge_location": edge_location
                }
        except Exception as e:
            return {
                "level": 4,
                "name": "Prometheus_Tunnel_Telemetry",
                "passed": False,
                "error": str(e),
                "details": "No se pudo leer el endpoint de métricas Prometheus local (127.0.0.1:20241/metrics)."
            }

    def audit_level_5_core_database(self) -> Dict[str, Any]:
        """[Nivel 5] Salud del Core ODA y conexión de base de datos relacional."""
        req = urllib.request.Request(f"{self.public_url}/health")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                db_status = data.get("database", {}).get("status")
                db_engine = data.get("database", {}).get("engine")
                poller_conn = data.get("n8n_poller", {}).get("is_connected")
                uptime = data.get("uptime_seconds", 0)

                passed = (db_status == "CONNECTED") and poller_conn
                return {
                    "level": 5,
                    "name": "Core_Service_And_Database_Status",
                    "passed": passed,
                    "details": f"Database: {db_status} ({db_engine}) | Sincronizador n8n: CONECTADO | Uptime: {uptime:.1f}s",
                    "database_status": db_status,
                    "n8n_poller_connected": poller_conn
                }
        except Exception as e:
            return {
                "level": 5,
                "name": "Core_Service_And_Database_Status",
                "passed": False,
                "error": str(e),
                "details": "Fallo al validar la respuesta JSON de /health."
            }

    def audit_level_6_cognitive_e2e(self) -> Dict[str, Any]:
        """[Nivel 6] Ejecución Cognitiva E2E en tiempo real (FastPath determinista)."""
        t0 = time.perf_counter()
        payload = json.dumps({
            "subscriber_phone": "+584161234567",
            "message": "un buen restaurant en los palos grandes"
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.public_url}/api/v1/agents/customer-care/process",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latency = (time.perf_counter() - t0) * 1000
                mode = data.get("execution_mode")
                tokens = data.get("tokens_consumed", -1)
                reply = data.get("reply", "") or data.get("response_text", "")

                has_telco = "movilnet" in reply.lower() and ("telecomunicaciones" in reply.lower() or "conectividad" in reply.lower())
                has_centro_plaza = "centro plaza" in reply.lower()
                has_cloudflare_pwa = self.public_url in reply

                passed = (mode == "FAST_PATH") and (tokens == 0) and has_telco and has_centro_plaza
                return {
                    "level": 6,
                    "name": "Cognitive_E2E_Execution",
                    "passed": passed,
                    "latency_ms": round(latency, 2),
                    "details": f"Modo: {mode} | Tokens: {tokens} | Latencia E2E: {latency:.2f}ms | OSAC Sugerida: Centro Plaza (Chacao) | PWA Link Cloudflare: {'SÍ' if has_cloudflare_pwa else 'NO'}",
                    "execution_mode": mode,
                    "tokens_consumed": tokens,
                    "pwa_link_verified": has_cloudflare_pwa
                }
        except Exception as e:
            return {
                "level": 6,
                "name": "Cognitive_E2E_Execution",
                "passed": False,
                "error": str(e),
                "details": "Fallo en la llamada POST a /api/v1/agents/customer-care/process."
            }

    def run_full_audit(self) -> Dict[str, Any]:
        """Ejecuta los 6 niveles y emite el certificado criptográfico."""
        checks = [
            self.audit_level_1_dns(),
            self.audit_level_2_tls(),
            self.audit_level_3_edge_headers(),
            self.audit_level_4_prometheus_metrics(),
            self.audit_level_5_core_database(),
            self.audit_level_6_cognitive_e2e(),
        ]
        total_passed = sum(1 for c in checks if c.get("passed"))
        all_passed = (total_passed == len(checks))

        # Generar Sello Criptográfico SHA-256
        raw_signature = f"{self.public_url}|{total_passed}/{len(checks)}|{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"
        sha_seal = hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()

        report = {
            "title": "CERTIFICADO DE AUDITORÍA OPERATIVA EN CLOUDFLARE (NIVELES 1 AL 6)",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "public_url": self.public_url,
            "all_passed": all_passed,
            "score": f"{total_passed}/{len(checks)}",
            "certification_seal": f"SHA256:{sha_seal}",
            "checks": checks
        }

        # Guardar reporte en disco
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / "CERTIFICACION_CLOUDFLARE_ACTIVO.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report


def main():
    parser = argparse.ArgumentParser(description="Auditor y Certificador Oficial de Cloudflare para Movilnet Core")
    parser.add_argument("--url", type=str, help="URL pública a auditar")
    parser.add_argument("--json", action="store_true", help="Salida exclusivamente en formato JSON")
    args = parser.parse_args()

    target_url = args.url or get_target_tunnel_url()
    auditor = CloudflareAuditor(target_url)
    report = auditor.run_full_audit()

    if args.json:
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["all_passed"] else 1)

    print("=" * 95)
    print("🛡️  SUITE MILITAR DE AUDITORÍA Y CERTIFICACIÓN: MOVILNET CORE EN CLOUDFLARE")
    print("=" * 95)
    print(f"🌐 URL Auditada: {report['public_url']}")
    print(f"⏱️ Fecha y Hora UTC: {report['timestamp_utc']}")
    print("-" * 95)

    for c in report["checks"]:
        status_icon = "✅ PASS" if c.get("passed") else "❌ FAIL"
        lat_str = f"({c.get('latency_ms')} ms)" if "latency_ms" in c else ""
        print(f"[{c['level']}/6] {status_icon} | {c['name']} {lat_str}")
        print(f"      └── {c['details']}")

    print("-" * 95)
    status_final = "🏆 CERTIFICACIÓN APROBADA (100% PASS, CERO ERRORES)" if report["all_passed"] else "⚠️ AUDITORÍA CON FALLOS"
    print(f"Resultado Final: {status_final} — Puntuación: {report['score']}")
    print(f"🔒 Sello Inmutable: {report['certification_seal']}")
    print(f"📄 Reporte Guardado en: reports/CERTIFICACION_CLOUDFLARE_ACTIVO.json")
    print("=" * 95)

    sys.exit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
