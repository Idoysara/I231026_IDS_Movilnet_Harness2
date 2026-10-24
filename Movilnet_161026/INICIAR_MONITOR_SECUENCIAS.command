#!/bin/bash
# ==============================================================================
# INICIAR_MONITOR_SECUENCIAS.command — Lanzador Soberano de Doble Clic
# Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
# Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Cero Terminal)
# ==============================================================================

cd "$(dirname "$0")"

if [ -d "AI_Movilnet_300926-main" ]; then
    cd "AI_Movilnet_300926-main"
fi

echo "========================================================================"
echo "🌲 CENTRO DE MONITOREO DE SECUENCIAS CONVERSACIONALES E2E"
echo "📱 Servidor Movilnet Core WhatsApp Webhook: +58 424 153 3712 (00584241533712)"
echo "========================================================================"

PORT=8010
TS=$(date +%s)
URL="http://localhost:${PORT}/ui/monitor/conversatorio.html?v=${TS}"

# Verificar si el servicio ya está activo
if lsof -i :${PORT} >/dev/null 2>&1; then
    echo "🟢 Servidor Movilnet Core ya está activo en el puerto ${PORT}."
    echo "🌐 Abriendo Conversatorio de 2 Columnas (v${TS}): ${URL}"
    open "${URL}"
    echo "✅ Conversatorio abierto en tu navegador."
    exit 0
fi

echo "🚀 Iniciando servidor Movilnet Core en puerto ${PORT}..."
echo "🌐 URL de Monitoreo: ${URL}"
echo "------------------------------------------------------------------------"

# Abrir el navegador tras 1.5 segundos
(sleep 1.5 && open "${URL}") &

# Ejecutar el servidor con el venv si existe
if [ -f "venv/bin/python3" ]; then
    venv/bin/python3 api/service.py --port ${PORT}
else
    python3 api/service.py --port ${PORT}
fi
