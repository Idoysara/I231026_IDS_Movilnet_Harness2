#!/bin/bash
# ==============================================================================
# DESPLEGAR_A_LA_NUBE.command — Lanzador Soberano de Doble Clic
# Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
# Modo A: Despliegue en la Nube 24/7 (Render / Railway / Docker Gratuito)
# Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Cero Terminal)
# ==============================================================================

cd "$(dirname "$0")"

if [ -d "AI_Movilnet_300926-main" ]; then
    cd "AI_Movilnet_300926-main"
fi

clear
echo "========================================================================"
echo "☁️  MOVILNET CORE 4GMAX — DESPLIEGUE A LA NUBE 24/7 (MODO A)"
echo "========================================================================"
echo "🎯 Objetivo: Dejar el sistema corriendo en un servidor en la nube sin costo,"
echo "   para que los 4 millones de abonados puedan consultar su saldo y PWA"
echo "   a cualquier hora, sin que tu laptop tenga que estar encendida."
echo "========================================================================"
echo ""

# 0. Verificación estricta de Aislamiento de Entorno
if [ -f ".env" ]; then
    AIRGAP_CHECK=$(grep -E "^AIRGAP_DEV_MODE=true|^ENVIRONMENT=development" .env 2>/dev/null)
    if [ -n "$AIRGAP_CHECK" ]; then
        echo "🛑 BLOQUEO DE SEGURIDAD (AIR-GAP DE DESARROLLO ACTIVO):"
        echo "   Este equipo MBP es exclusivamente AMBIENTE DE DESARROLLO."
        echo "   El despliegue a la nube de producción está bloqueado para proteger la infraestructura."
        echo "   La producción opera de forma aislada en otro equipo MBP."
        echo ""
        read -p "Presiona ENTER para salir..."
        exit 1
    fi
fi

# 1. Ejecutar auditoría previa de preparación
echo "🔍 1. Ejecutando auditoría de preparación técnica para la nube..."
if [ -f "venv/bin/python3" ]; then
    venv/bin/python3 scripts/validate_cloud_deployment_readiness.py --test
else
    python3 scripts/validate_cloud_deployment_readiness.py --test
fi

if [ $? -ne 0 ]; then
    echo "❌ Error: La auditoría detectó discrepancias. Revisa los mensajes anteriores."
    read -p "Presiona Enter para salir..."
    exit 1
fi

echo ""
echo "========================================================================"
echo "🚀 OPCIONES DE DESPLIEGUE GRATUITO DISPONIBLES:"
echo "========================================================================"
echo "1) 🌐 Desplegar en RENDER (Plan Free $0.00 USD - render.yaml listo)"
echo "   👉 Te asigna: https://movilnet-core.onrender.com"
echo ""
echo "2) 🚂 Desplegar en RAILWAY (Plan Free $0.00 USD - railway.json listo)"
echo "   👉 Te asigna: https://movilnet-core.up.railway.app"
echo ""
echo "3) 📱 Ver Enlaces Mágicos de WhatsApp ya generados"
echo "4) 🚪 Salir"
echo "========================================================================"
echo -n "Selecciona una opción [1-4]: "
read opcion

case $opcion in
    1)
        echo ""
        echo "🌐 Abriendo Render en tu navegador..."
        echo "📋 Pasos en Render (1 Clic):"
        echo "   1. Inicia sesión en Render (con GitHub o Google)."
        echo "   2. Selecciona 'New Web Service' o 'Blueprints'."
        echo "   3. Conecta este repositorio de GitHub."
        echo "   4. ¡Listo! Render leerá 'render.yaml' y levantará el Core 24/7."
        open "https://dashboard.render.com"
        ;;
    2)
        echo ""
        echo "🚂 Abriendo Railway en tu navegador..."
        echo "📋 Pasos en Railway (1 Clic):"
        echo "   1. Inicia sesión en Railway."
        echo "   2. Haz clic en 'New Project' -> 'Deploy from GitHub repo'."
        echo "   3. Railway detectará el Dockerfile y levantará el Core 24/7."
        open "https://railway.app/new"
        ;;
    3)
        echo ""
        echo "📱 ENLACES MÁGICOS DE ONBOARDING WHATSAPP ➔ PWA:"
        echo "------------------------------------------------------------------------"
        echo "• Dominio Render:"
        echo "  👉 https://movilnet-core.onrender.com/ui/pwa_stitch/index.html?phone=04142554590"
        echo ""
        echo "• Dominio Corporativo Oficial Movilnet:"
        echo "  👉 https://autogestion.movilnet.com.ve/ui/pwa_stitch/index.html?phone=04142554590"
        echo "------------------------------------------------------------------------"
        echo "Al enviar estos enlaces por WhatsApp, cualquier celular en la calle"
        echo "abre la PWA en 1 toque con su saldo cargado automáticamente."
        ;;
    *)
        echo "Saliendo..."
        exit 0
        ;;
esac

echo ""
read -p "Presiona Enter para finalizar..."
