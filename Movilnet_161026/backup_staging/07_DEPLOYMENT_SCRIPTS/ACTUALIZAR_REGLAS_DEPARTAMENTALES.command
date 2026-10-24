#!/bin/bash
# ==============================================================================
# ACTUALIZAR_REGLAS_DEPARTAMENTALES.command — Lanzador 1-Clic de Reglas Movilnet
# Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
# Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Cero Terminal)
# ==============================================================================

cd "$(dirname "$0")"

echo "========================================================================"
echo "🔄 ACTUALIZACIÓN EN CALIENTE DE REGLAS DEPARTAMENTALES (HOT-RELOAD)"
echo "========================================================================"
echo "Áreas: Comercial, Finanzas C2P, Atención, Seguridad CONATEL y NOC"
echo "------------------------------------------------------------------------"

PORT=8010
PYTHON_EXEC="python3"
if [ -f "venv/bin/python3" ]; then
    PYTHON_EXEC="venv/bin/python3"
fi

$PYTHON_EXEC scripts/validate_department_rules.py --audit --reload-api --port $PORT

echo ""
echo "========================================================================"
echo "✅ Proceso completado. Las reglas están activas en memoria sin caídas."
echo "========================================================================"
