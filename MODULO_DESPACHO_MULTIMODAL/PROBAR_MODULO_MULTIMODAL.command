#!/bin/bash
# ==============================================================================
# Lanzador 1-Clic: Suite Completa de Pruebas Automatizadas y Certificación SHA-256
# Telecomunicaciones Movilnet C.A. — Pilares V y VII de Buenas Prácticas
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "================================================================================"
echo "🧪 EJECUTANDO SUITE COMPLETA DE PRUEBAS DEL MÓDULO MULTIMODAL"
echo "================================================================================"

echo ""
echo "1. Ejecutando suite completa de pruebas unitarias y de integración..."
python3 -m unittest discover -s tests -p "test_*.py"

echo ""
echo "2. Ejecutando auto-verificación formal de scripts, parser y clientes..."
python3 scripts/init_multimodal_db.py --test
python3 scripts/cleanup_expired_vaults.py --test
python3 mcp/mcp_multimodal_tools.py --test
python3 application/voucher_parser.py --test
python3 infrastructure/whatsapp_client.py --test
python3 scripts/simulate_n8n_stage_webhook.py --test

echo ""
echo "3. Ejecutando benchmark de rendimiento End-to-End (E2E)..."
python3 scripts/benchmark_multimodal_e2e.py --iterations 20

echo ""
echo "4. Verificando árbol criptográfico SHA-256 inmutable..."
python3 scripts/generate_sha256_manifest.py --verify

echo ""
echo "================================================================================"
echo "🟢 VEREDICTO FINAL: 100% PASS (0 FALLOS, CERTIFICADO PARA PRODUCCIÓN)"
echo "================================================================================"
