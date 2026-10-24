#!/bin/bash
# ==============================================================================
# CONECTAR_N8N_EN_VIVO.command — Lanzador de Doble Clic para Conexión con n8n
# Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
# ==============================================================================

cd "$(dirname "$0")"

# Determinar directorio raíz de la aplicación
if [ -d "AI_Movilnet_300926-main" ]; then
    cd "AI_Movilnet_300926-main"
fi

echo "========================================================================"
echo "🚀 INICIANDO CONEXIÓN: MOVILNET ↔ n8n LPGTEC"
echo "========================================================================"

if [ -f ".env" ]; then
    AIRGAP_CHECK=$(grep -E "^AIRGAP_DEV_MODE=true|^ENVIRONMENT=development" .env 2>/dev/null)
    if [ -n "$AIRGAP_CHECK" ]; then
        echo "🛑 BLOQUEO DE SEGURIDAD (AIR-GAP DE DESARROLLO ACTIVO):"
        echo "   Este equipo MBP es exclusivamente AMBIENTE DE DESARROLLO."
        echo "   La conexión y sincronización con n8n Cloud de producción está bloqueada."
        echo "   La producción opera de forma aislada en otro equipo MBP."
        echo ""
        read -p "Presiona ENTER para salir..."
        exit 1
    fi
fi

if [ -f "venv/bin/python3" ]; then
    venv/bin/python3 scripts/connect_n8n_live.py
else
    python3 scripts/connect_n8n_live.py
fi

echo ""
read -p "Presiona ENTER para cerrar esta ventana..."
