#!/bin/bash
# ==============================================================================
# REINICIAR_SERVICIOS_MOVILNET.command — Reiniciador Soberano de Doble Clic
# Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
# Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Cero Terminal)
# ==============================================================================

cd "$(dirname "$0")"

if [ -d "AI_Movilnet_300926-main" ]; then
    cd "AI_Movilnet_300926-main"
fi

echo "========================================================================"
echo "🔄 REINICIANDO STACK DE SERVICIOS CORE MOVILNET & CONVERSATORIO"
echo "📱 Bot Central WhatsApp: +58 424 153 3712 (00584241533712)"
echo "========================================================================"

PORT=8010

echo "1️⃣  Deteniendo procesos anteriores en puerto ${PORT} y supervisor..."
# Liberar puerto 8010 si está ocupado
PIDS_PORT=$(lsof -t -i :${PORT} 2>/dev/null)
if [ -n "$PIDS_PORT" ]; then
    echo "   🛑 Terminando PID(s) en puerto ${PORT}: $PIDS_PORT"
    kill -9 $PIDS_PORT 2>/dev/null
fi

# Detener supervisor anterior
pkill -f "live_core_supervisor.py" 2>/dev/null

sleep 1.5

echo "2️⃣  Iniciando Servidor Movilnet Core API en puerto ${PORT}..."
if [ -f "venv/bin/python3" ]; then
    nohup venv/bin/python3 api/service.py --port ${PORT} >/dev/null 2>&1 &
else
    nohup python3 api/service.py --port ${PORT} >/dev/null 2>&1 &
fi

sleep 1.5

echo "3️⃣  Iniciando Supervisor en Vivo n8n Cloud (Daemon 3s)..."
if [ -f "venv/bin/python3" ]; then
    nohup venv/bin/python3 scripts/live_core_supervisor.py --daemon >/dev/null 2>&1 &
else
    nohup python3 scripts/live_core_supervisor.py --daemon >/dev/null 2>&1 &
fi

sleep 1.5

TS=$(date +%s)
URL="http://localhost:${PORT}/ui/monitor/conversatorio.html?v=${TS}"

echo "------------------------------------------------------------------------"
if lsof -i :${PORT} >/dev/null 2>&1; then
    echo "🟢 ¡SERVICIOS REINICIADOS CON ÉXITO!"
    echo "🌐 Centro de Monitoreo: ${URL}"
    echo "📱 Para probar desde WhatsApp: https://wa.me/584241533712"
    echo "------------------------------------------------------------------------"
    echo "Abriendo sala de monitoreo en tu navegador..."
    open "${URL}"
else
    echo "⚠️  El puerto ${PORT} tardó en responder. Revisa los logs en logs/."
fi

echo ""
echo "✅ Todo listo. Puedes cerrar esta ventana."
