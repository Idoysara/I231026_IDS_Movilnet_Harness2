#!/usr/bin/env python3
"""
audit_perimeter_waf.py — Script CLI de Diagnóstico Perimetral
==============================================================
Proyecto: AI_Movilnet_300926 | Alcance: PROYECTO
Uso:
    python3 scripts/audit_perimeter_waf.py --url https://api.movilnet.com.ve
    python3 scripts/audit_perimeter_waf.py --url http://www.movilnet.com.ve --port 80
    python3 scripts/audit_perimeter_waf.py --batch urls.txt
"""
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.discovery_tools import audit_perimeter


def main():
    parser = argparse.ArgumentParser(
        description="Diagnóstico perimetral WAF/SSL/Firewall para Fase 0 Telco Discovery"
    )
    parser.add_argument("--url", type=str, help="URL o dominio a auditar")
    parser.add_argument("--port", type=int, default=443, help="Puerto TCP (default: 443)")
    parser.add_argument("--batch", type=str, help="Archivo de texto con una URL por línea")
    parser.add_argument("--output", type=str, help="Archivo JSON de salida (opcional)")
    args = parser.parse_args()

    urls = []
    if args.url:
        urls = [args.url]
    elif args.batch:
        batch_file = Path(args.batch)
        if not batch_file.exists():
            print(f"❌ Archivo batch no encontrado: {args.batch}", file=sys.stderr)
            sys.exit(1)
        urls = [line.strip() for line in batch_file.read_text().splitlines() if line.strip()]
    else:
        parser.print_help()
        sys.exit(0)

    all_results = []
    for url in urls:
        print(f"\n🔍 Auditando: {url} (puerto {args.port})...")
        result = audit_perimeter(url, port=args.port)
        all_results.append(result)

        status_icon = "✅" if result.get("http_status") in [200, 301, 302] else "🚫"
        print(f"  {status_icon} Conectividad  : {result.get('connectivity')}")
        print(f"  🔒 SSL Válido   : {result.get('ssl_valid')}")
        print(f"  📡 HTTP Status  : {result.get('http_status', 'N/A')}")
        print(f"  ⏱️  Latencia     : {result.get('latency_ms', 'N/A')} ms")
        print(f"  🛡️  WAF Detectado: {result.get('waf_detected')} ({result.get('waf_vendor', 'N/A')})")
        if result.get("recommendations"):
            print("  💡 Recomendaciones:")
            for rec in result["recommendations"]:
                print(f"     • {rec}")
        if result.get("report_saved"):
            print(f"  📁 Reporte guardado: {result['report_saved']}")

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n✅ Resultados consolidados exportados: {out_path}")

    return all_results


if __name__ == "__main__":
    main()
