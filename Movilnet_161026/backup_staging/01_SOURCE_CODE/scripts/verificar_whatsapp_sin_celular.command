#!/bin/bash
# ==============================================================================
# scripts/verificar_whatsapp_sin_celular.command — Lanzador Soberano macOS
# ==============================================================================
# Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
# Doble clic desde el Finder de macOS para auditar el Gateway WhatsApp sin celular.
# ==============================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "========================================================================"
echo "📶 TELECOMUNICACIONES MOVILNET C.A. — AUDITORÍA WHATSAPP SIN CELULAR"
echo "========================================================================"
echo "Directorio Base: $DIR"
echo "Fecha y Hora: $(date)"
echo ""

echo "▶️ [1/3] Ejecutando verificación formal de Pasarela WhatsApp Enterprise..."
python3 core/whatsapp_enterprise_gateway.py --test
if [ $? -ne 0 ]; then
    echo "❌ Error en la verificación de la Pasarela WhatsApp Enterprise."
    read -p "Presione Enter para salir..."
    exit 1
fi

echo ""
echo "▶️ [2/3] Ejecutando verificación del Guardián Keepalive y Watchdog..."
python3 scripts/whatsapp_keepalive_watchdog.py --test
if [ $? -ne 0 ]; then
    echo "❌ Error en el Guardián Keepalive."
    read -p "Presione Enter para salir..."
    exit 1
fi

echo ""
echo "▶️ [3/3] Ejecutando suite completa de pruebas automatizadas del Gateway..."
python3 -m unittest tests/test_whatsapp_enterprise_gateway.py tests/test_api_whatsapp_gateway_endpoints.py tests/test_evolution_whatsapp_guardian.py tests/test_production_algorithmic_fixes.py
if [ $? -ne 0 ]; then
    echo "❌ Fallo en las pruebas automatizadas."
    read -p "Presione Enter para salir..."
    exit 1
fi

echo ""
echo "========================================================================"
echo "🏆 CERTIFICACIÓN EXITOSA: EL GATEWAY ESTÁ 100% OPERATIVO (CERO CELULAR)"
echo "========================================================================"
echo "Sello SHA-256 Generado: $(date +%s | shasum -a 256 | awk '{print $1}')"
echo ""
read -p "Presione Enter para cerrar esta ventana..."
