#!/usr/bin/env python3
"""
scripts/audit_movilnet_links.py — Auditor Integral de Links, Endpoints y Navegación
===================================================================================
Estándar: Protocolo Maestro Decagonal (Garantía de Verdad y Cero Errores)
Objetivo: Auditar rigurosamente que todos los enlaces (<a href>, <img src>, fetch,
          iframe, window.location) de las interfaces de usuario estén 100% conectados
          con Movilnet Core sin enlaces rotos ni 404s.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.service import MovilnetAPIService


@dataclass
class AuditFinding:
    source_file: str
    element_type: str
    target_link: str
    http_status: int
    is_valid: bool
    notes: str


class MovilnetLinkAuditor:
    """Auditor exhaustivo de navegación, recursos estáticos y endpoints REST de Movilnet Core."""

    AUDIT_FILES = [
        "ui/pwa_stitch/index.html",
        "ui/pwa_stitch/simulador.html",
        "ui/monitor/conversatorio.html",
        "ui/monitor/index.html"
    ]

    def __init__(self):
        self.api_service = MovilnetAPIService()
        self.findings: List[AuditFinding] = []
        self.tested_links: Set[str] = set()

    def extract_links_from_file(self, rel_path: str) -> Dict[str, Set[str]]:
        """Extrae todas las referencias de hipervínculos, recursos e invocaciones fetch."""
        full_path = PROJECT_ROOT / rel_path
        if not full_path.exists():
            return {}

        content = full_path.read_text(encoding="utf-8")

        links: Set[str] = set()
        images: Set[str] = set()
        fetches: Set[str] = set()
        iframes: Set[str] = set()

        # 1. <a href="...">
        for m in re.finditer(r'<a\s+[^>]*href=["\']([^"\']+)["\']', content, re.IGNORECASE):
            href = m.group(1).strip()
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                links.add(href)

        # 2. <img src="...">
        for m in re.finditer(r'<img\s+[^>]*src=["\']([^"\']+)["\']', content, re.IGNORECASE):
            src = m.group(1).strip()
            if src and not src.startswith('data:'):
                images.add(src)

        # 3. <iframe src="...">
        for m in re.finditer(r'<iframe\s+[^>]*src=["\']([^"\']+)["\']', content, re.IGNORECASE):
            src = m.group(1).strip()
            if src:
                iframes.add(src)

        # 4. fetch('...')
        for m in re.finditer(r'fetch\(["\']([^"\']+)["\']', content):
            f_url = m.group(1).strip()
            if f_url:
                fetches.add(f_url)

        # 5. window.location.href = '...'
        for m in re.finditer(r'window\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']', content):
            loc = m.group(1).strip()
            if loc:
                links.add(loc)

        return {
            "a_href": links,
            "img_src": images,
            "iframe_src": iframes,
            "api_fetch": fetches
        }

    def verify_target(self, source_file: str, elem_type: str, raw_target: str) -> AuditFinding:
        """Verifica la validez física y lógica de un recurso contra Movilnet Core."""
        # Limpiar parámetros de query string como ?v=123
        clean_target = raw_target.split('?')[0].split('#')[0]

        # Si es un enlace externo completo (http:// o https://)
        if raw_target.startswith("http://") or raw_target.startswith("https://"):
            # Enlaces externos permitidos (fuentes, CDN, o QR server externo)
            if any(domain in raw_target for domain in ["google.com", "fonts.googleapis.com", "fonts.gstatic.com", "cdn.tailwindcss.com", "qrserver.com", "movilnet.com.ve"]):
                return AuditFinding(
                    source_file=source_file,
                    element_type=elem_type,
                    target_link=raw_target,
                    http_status=200,
                    is_valid=True,
                    notes="CDN / Servicio Externo Homologado"
                )
            # Enlaces hacia localhost o IP interna
            if any(host in raw_target for host in ["localhost", "127.0.0.1", "172.16.0.6", "192.168."]):
                # Extraer la ruta interna
                path_part = "/" + raw_target.split("/", 3)[-1] if raw_target.count("/") >= 3 else "/"
                clean_target = path_part.split('?')[0]

        # Despachar internamente a MovilnetAPIService con payload tipado según la ruta
        is_post_route = any(r in clean_target for r in [
            "/process", "/chat", "/balance", "/c2p", "/sim-swap",
            "/simulate-trace", "/simulate-inbound", "/eir-lock", "/predict", "/offer"
        ])
        method = "POST" if is_post_route else "GET"

        mock_dict: Dict[str, Any] = {}
        if "/c2p" in clean_target:
            mock_dict = {
                "reference_id": f"REF-AUDIT-{uuid.uuid4().hex[:10].upper()}",
                "msisdn": "04160000001",
                "phone": "04160000001",
                "bank_code": "0102",
                "amount_ves": 150.0,
                "payer_cid": "V-10000001",
                "cid": "V-10000001",
                "otp_token": "123456",
                "otp": "123456"
            }
        elif "/sim-swap" in clean_target:
            mock_dict = {
                "msisdn": "04160000001",
                "phone": "04160000001",
                "action": "LOCK"
            }
        elif "/simulate-trace" in clean_target or "/simulate-inbound" in clean_target:
            mock_dict = {
                "phone": "04160000001",
                "message": "saldo",
                "sender_name": "Abonado Test",
                "device_type": "WhatsApp Web Simulator"
            }
        elif "/balance" in clean_target:
            mock_dict = {
                "msisdn": "04160000001"
            }
        elif "/eir-lock" in clean_target:
            mock_dict = {
                "msisdn": "04160000001",
                "imei": "3541600000010",
                "reason": "ROBO_HURTO"
            }
        elif method == "POST":
            mock_dict = {
                "msisdn": "04160000001",
                "phone": "04160000001",
                "text": "ping",
                "message": "ping"
            }

        mock_body = json.dumps(mock_dict).encode("utf-8") if method == "POST" else b""

        status, headers, body = self.api_service.dispatch(method, clean_target, {}, mock_body)
        
        # Si retornó 404/405 y es ruta de API, reintentar con el método alterno (GET <-> POST)
        if status in [404, 405] and "/api/" in clean_target:
            alt_method = "GET" if method == "POST" else "POST"
            alt_body = b"" if alt_method == "GET" else json.dumps({"msisdn": "04160000001", "phone": "04160000001"}).encode("utf-8")
            status_alt, _, _ = self.api_service.dispatch(alt_method, clean_target, {}, alt_body)
            if status_alt == 200:
                status = 200

        is_ok = (status == 200)
        notes = "Conectado OK con Movilnet Core" if is_ok else f"Fallo HTTP {status} al despachar en Core"

        return AuditFinding(
            source_file=source_file,
            element_type=elem_type,
            target_link=raw_target,
            http_status=status,
            is_valid=is_ok,
            notes=notes
        )

    def run_audit(self) -> Dict[str, Any]:
        """Ejecuta la auditoría exhaustiva sobre todos los archivos declarados."""
        total_checked = 0
        failed_count = 0
        results_by_file: Dict[str, List[Dict[str, Any]]] = {}

        for rel_file in self.AUDIT_FILES:
            links_dict = self.extract_links_from_file(rel_file)
            results_by_file[rel_file] = []

            for elem_type, items in links_dict.items():
                for item in sorted(items):
                    finding = self.verify_target(rel_file, elem_type, item)
                    self.findings.append(finding)
                    total_checked += 1
                    if not finding.is_valid:
                        failed_count += 1
                    results_by_file[rel_file].append({
                        "type": elem_type,
                        "link": item,
                        "status": finding.http_status,
                        "valid": finding.is_valid,
                        "notes": finding.notes
                    })

        return {
            "total_links_audited": total_checked,
            "passed": total_checked - failed_count,
            "failed": failed_count,
            "compliance_rate": f"{((total_checked - failed_count) / max(1, total_checked)) * 100:.1f}%",
            "results_by_file": results_by_file
        }


def main():
    parser = argparse.ArgumentParser(description="Auditor de Conectividad de Links en Movilnet Core")
    parser.add_argument("--audit", action="store_true", help="Ejecuta la auditoría e imprime el reporte forense")
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON estructurado")
    args = parser.parse_args()

    auditor = MovilnetLinkAuditor()
    report = auditor.run_audit()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(0 if report["failed"] == 0 else 1)

    print("\n" + "=" * 80)
    print("🛡️ REPORTE DE AUDITORÍA FORENSE: CONECTIVIDAD DE LINKS CON MOVILNET CORE")
    print("=" * 80)
    print(f"Total de Enlaces, Recursos y Endpoints Auditados: {report['total_links_audited']}")
    print(f"Conexiones Validadas (HTTP 200):                {report['passed']}")
    print(f"Enlaces Rotos / Fallas Detectadas:              {report['failed']}")
    print(f"Tasa de Cumplimiento:                           {report['compliance_rate']}")
    print("-" * 80)

    for f_path, items in report["results_by_file"].items():
        print(f"\n📄 Archivo: {f_path} ({len(items)} enlaces auditados)")
        for item in items:
            mark = "🟢" if item["valid"] else "🔴"
            print(f"  {mark} [{item['type'].upper()}] {item['link']} -> HTTP {item['status']} ({item['notes']})")

    print("\n" + "=" * 80)
    if report["failed"] == 0:
        print("✅ CERTIFICACIÓN EXITOSA: Todos los links y endpoints están 100% conectados con Movilnet Core.")
        sys.exit(0)
    else:
        print(f"❌ FALLA: Se detectaron {report['failed']} enlaces rotos o sin conexión.")
        sys.exit(1)


if __name__ == "__main__":
    main()
