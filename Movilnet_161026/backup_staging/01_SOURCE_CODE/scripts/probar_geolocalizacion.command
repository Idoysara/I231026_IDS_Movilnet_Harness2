#!/bin/bash
# ==============================================================================
# scripts/probar_geolocalizacion.command — Lanzador Soberano macOS Doble Clic
# ==============================================================================
# Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
# Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Cero Terminal)
# ==============================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "========================================================================"
echo "📍 TELECOMUNICACIONES MOVILNET C.A. — SIMULADOR OFICIAL DE AGENCIAS 4GMAX"
echo "========================================================================"
echo "Directorio Base: $DIR"
echo "Ambiente Actual: DESARROLLO (Rama develop)"
echo "Censo Oficial Certificado: 1,017 Agencias y Oficinas a Nivel Nacional"
echo "Fecha y Hora: $(date)"
echo "========================================================================"
echo ""

python3 scripts/probar_geolocalizacion_interactivo.py

echo ""
echo "========================================================================"
echo "🏆 SIMULACIÓN CONCLUIDA"
echo "========================================================================"
read -p "Presione [Enter] para cerrar esta ventana..."
