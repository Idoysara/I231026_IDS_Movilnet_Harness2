#!/bin/bash
# ==============================================================================
# scripts/desplegar_a_produccion.command — Pase a Producción Render Cloud 24/7
# ==============================================================================
# Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
# Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Cero Terminal)
# ==============================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "========================================================================"
echo "🚀 TELECOMUNICACIONES MOVILNET C.A. — PASE A PRODUCCIÓN CLOUD 24/7"
echo "========================================================================"
echo "Directorio Base: $DIR"
echo "Fecha y Hora: $(date)"
echo "Rama Activa: $(git rev-parse --abbrev-ref HEAD)"
echo "========================================================================"
echo ""

echo "▶️ [1/2] Verificando que la rama local sea 'main'..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "   ⚠️ Conmutando a rama main..."
    git checkout main
fi

echo ""
echo "▶️ [2/2] Publicando cambios hacia GitHub (origin/main) para Auto-Deploy en Render..."
git push origin main

STATUS=$?
echo ""
if [ $STATUS -eq 0 ]; then
    echo "========================================================================"
    echo "✅ ¡PASE A PRODUCCIÓN DISPARADO EXITOSAMENTE EN GITHUB Y RENDER!"
    echo "========================================================================"
    echo "Render Cloud compilará el código y lo pondrá en vivo en ~60 segundos."
    echo "🌐 Portal PWA Oficial: https://one21026-ids-movilnet-pwa.onrender.com"
    echo "🤖 WhatsApp Oficial: +58 424 153 3712 (n8n Cloud)"
    echo "========================================================================"
else
    echo "========================================================================"
    echo "❌ Error al hacer git push ($STATUS). Revisa tus credenciales de GitHub."
    echo "========================================================================"
fi
