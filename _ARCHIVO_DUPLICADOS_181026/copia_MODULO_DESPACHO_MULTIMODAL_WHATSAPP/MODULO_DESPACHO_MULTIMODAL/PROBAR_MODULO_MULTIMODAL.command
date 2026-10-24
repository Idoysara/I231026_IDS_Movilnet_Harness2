#!/bin/bash
# ==============================================================================
# Lanzador 1-Clic: Suite Completa de Pruebas Automatizadas (100% PASS)
# Telecomunicaciones Movilnet C.A. — Pilar V de Buenas Prácticas
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "================================================================================"
echo "🧪 EJECUTANDO SUITE COMPLETA DE PRUEBAS DEL MÓDULO MULTIMODAL"
echo "================================================================================"

echo ""
echo "1. Ejecutando pruebas unitarias y de integración..."
python3 -m unittest discover -s tests -p "test_*.py"

echo ""
echo "2. Ejecutando auto-verificación de scripts y MCP..."
python3 scripts/init_multimodal_db.py --test
python3 scripts/cleanup_expired_vaults.py --test
python3 mcp/mcp_multimodal_tools.py --test

echo ""
echo "3. Ejecutando benchmark de rendimiento (30 iteraciones)..."
python3 scripts/benchmark_multimodal.py --iterations 30

echo ""
echo "================================================================================"
echo "🟢 VEREDICTO FINAL: 100% PASS (0 FALLOS, CERTIFICADO PARA PRODUCCIÓN)"
echo "================================================================================"
