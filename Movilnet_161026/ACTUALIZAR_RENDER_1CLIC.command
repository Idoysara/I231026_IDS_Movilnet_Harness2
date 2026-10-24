#!/bin/bash
# ==============================================================================
# ACTUALIZAR_RENDER_1CLIC.command — Despliegue Automatizado a Render (1 Clic)
# Proyecto: Movilnet PWA & Asistente 4GMAX — Telecomunicaciones Movilnet C.A.
# Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Cero Terminal)
# ==============================================================================

cd "$(dirname "$0")"

clear
echo "========================================================================"
echo "🚀 ACTUALIZADOR 1-CLIC — NUBE RENDER (MOVILNET CORE 4GMAX)"
echo "========================================================================"
echo "🎯 Objetivo: Actualizar tu servidor en Render automáticamente sin tener"
echo "   que entrar a la web ni buscar el botón 'Manual Deploy'."
echo "========================================================================"
echo ""

# 0. Verificación estricta de Aislamiento de Entorno
if [ -f ".env" ]; then
    AIRGAP_CHECK=$(grep -E "^AIRGAP_DEV_MODE=true|^ENVIRONMENT=development" .env 2>/dev/null)
    if [ -n "$AIRGAP_CHECK" ]; then
        echo "🛑 BLOQUEO DE SEGURIDAD (AIR-GAP DE DESARROLLO ACTIVO):"
        echo "   Este equipo MBP está configurado estrictamente como AMBIENTE DE DESARROLLO."
        echo "   El despliegue a Render Cloud de producción está bloqueado para proteger la nube."
        echo "   La producción opera de forma aislada en otro equipo MBP."
        echo ""
        read -p "Presiona ENTER para salir..."
        exit 1
    fi
fi

# 1. Verificar si hay cambios locales para subir a GitHub
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    echo "📦 1. Sincronizando cambios locales con GitHub..."
    git add .
    git commit -m "feat(auto-sync): actualizacion previa a despliegue en Render"
    git push origin main
    echo "✅ Código actualizado en GitHub."
    echo ""
else
    echo "✅ 1. Repositorio local ya está al día con GitHub."
    echo ""
fi

# 2. Ejecutar el disparador autónomo de Render
echo "🌐 2. Activando compilación en los servidores de Render..."
if [ -f "venv/bin/python3" ]; then
    venv/bin/python3 scripts/trigger_render_deploy.py --trigger
else
    python3 scripts/trigger_render_deploy.py --trigger
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "🎉 ¡DESPLIEGUE EN RENDER ACTIVADO CON ÉXITO!"
    echo "========================================================================"
    echo "En aproximadamente 60 segundos tu PWA en la nube tendrá los últimos"
    echo "cambios activos en todo el mundo para celulares iPhone y Android."
    echo ""
    echo "🌐 URL Nube: https://movilnet-core.onrender.com/ui/pwa_stitch/index.html"
    echo "========================================================================"
else
    echo ""
    echo "⚠️ Para configurar tu Deploy Hook de Render por primera y única vez:"
    echo "1. Ve a Render (https://dashboard.render.com) en tu servicio 'movilnet-core'."
    echo "2. En la pestaña 'Settings', baja hasta la sección 'Deploy Hook'."
    echo "3. Copia la URL que empieza por: https://api.render.com/deploy/srv-..."
    echo ""
    if [ -f "venv/bin/python3" ]; then
        venv/bin/python3 scripts/trigger_render_deploy.py
    else
        python3 scripts/trigger_render_deploy.py
    fi
fi

echo ""
read -p "Presiona ENTER para cerrar..."
