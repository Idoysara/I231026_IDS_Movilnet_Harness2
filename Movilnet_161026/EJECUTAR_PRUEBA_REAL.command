#!/bin/bash
# ==============================================================================
# EJECUTAR_PRUEBA_REAL.command — Lanzador Soberano de Doble Clic para Mac (1 Clic)
# Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
# Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Cero Terminal)
# ==============================================================================

cd "$(dirname "$0")"

echo "========================================================================"
echo "🚀 INICIANDO COMANDO MAESTRO DE PRUEBA REAL — CORE MOVILNET"
echo "========================================================================"

PORT=8010

# 1. Asegurar que el servidor Core esté activo
if ! lsof -i :${PORT} >/dev/null 2>&1; then
    echo "⚙️  Servidor Core no detectado en puerto ${PORT}. Levantando en segundo plano..."
    if [ -f "venv/bin/python3" ]; then
        nohup venv/bin/python3 api/service.py --port ${PORT} > /dev/null 2>&1 &
    else
        nohup python3 api/service.py --port ${PORT} > /dev/null 2>&1 &
    fi
    sleep 1.5
fi

# 2. Ejecutar orquestador unificado de prueba real
if [ -f "venv/bin/python3" ]; then
    venv/bin/python3 scripts/ejecutar_prueba_real.py
else
    python3 scripts/ejecutar_prueba_real.py
fi
