#!/bin/bash
# ==============================================================================
# AUDITAR_CLOUDFLARE_1CLIC.command — Auditoría y Certificación Oficial Cloudflare
# ==============================================================================
# Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
# Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Cero Terminal)
# ==============================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if [ -f "./venv/bin/python3" ]; then
    PY_BIN="./venv/bin/python3"
else
    PY_BIN="python3"
fi

echo "========================================================================"
echo "🛡️  AUDITORÍA Y CERTIFICACIÓN EN VIVO: MOVILNET CORE EN CLOUDFLARE"
echo "========================================================================"
echo ""

$PY_BIN scripts/audit_cloudflare_certification.py

echo ""
read -p "Presione [Enter] para cerrar esta ventana..."
