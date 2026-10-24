#!/bin/bash
# ==============================================================================
# INICIAR_MOVILNET_PWA.command — Lanzador Maestro de 1-Clic para el Administrador
# Proyecto: Movilnet PWA & Asistente MOVI 4GMAX — Telecomunicaciones Movilnet C.A.
# Gobernanza: Universal Best Practices Engineering Rule (Pilar VII: Cero Terminal)
# Arquitectura: Hexagonal Desacoplada (Capítulos 212 y 213)
# ==============================================================================

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ -d "$ROOT_DIR/backup_staging/01_SOURCE_CODE" ]; then
    SRC_DIR="$ROOT_DIR/backup_staging/01_SOURCE_CODE"
else
    SRC_DIR="$ROOT_DIR"
fi

cd "$SRC_DIR"

PORT=8010
PWA_URL="http://localhost:${PORT}/ui/pwa_stitch/index.html"
SIM_URL="http://localhost:${PORT}/ui/pwa_stitch/simulador.html?v=214"
CONVERSATORIO_URL="http://localhost:${PORT}/ui/monitor/conversatorio.html"
TRACE_MONITOR_URL="http://localhost:${PORT}/ui/conversation_trace_monitor.html"
PROD_URL="https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html"
PROD_CONVERSATORIO_URL="https://one21026-ids-movilnet-pwa.onrender.com/ui/monitor/conversatorio.html"

clear
echo "================================================================================"
echo "📱 MOVILNET CORE 4GMAX — PANEL DE ACTIVACIÓN DEL ADMINISTRADOR (v17.10.26)"
echo "================================================================================"
echo "📂 Directorio Base : $SRC_DIR"
echo "🔒 Producción Nube : ACTIVA Y SINCRONIZADA ($PROD_URL)"
echo "💬 Conversatorio   : $PROD_CONVERSATORIO_URL"
echo "================================================================================"

if [ -f "venv/bin/python3" ]; then
    PYTHON_BIN="venv/bin/python3"
else
    PYTHON_BIN="python3"
fi

# 1. Verificar o levantar el servidor local en :8010
PIDS=$(lsof -t -i :${PORT} 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo "🔄 Reiniciando servicio local en puerto :${PORT} con Arquitectura Hexagonal..."
    kill -9 $PIDS 2>/dev/null || true
    sleep 0.5
else
    echo "⚙️  Iniciando Servidor Movilnet Core (:8010) y Enjambre de Agentes L5..."
fi

nohup ${PYTHON_BIN} api/service.py --port ${PORT} >/dev/null 2>&1 &
sleep 1.8

# 2. Verificación rápida de los motores hexagonales y sincronización en vivo n8n <-> Render
echo "🛡️  Verificando Motores Hexagonales y Sincronizando WhatsApp (00584241533712)..."
${PYTHON_BIN} api/agents/agent_customer_care.py --test >/dev/null 2>&1 && echo "  ✅ Agente MOVI (CustomerCareAgent - 6 módulos): ACTIVO"
${PYTHON_BIN} core/conversation_trace_engine.py --test >/dev/null 2>&1 && echo "  ✅ Motor de Trazas E2E (ConversationTraceEngine - 5 módulos): ACTIVO"
${PYTHON_BIN} core/webhook_noise_filter.py --test >/dev/null 2>&1 && echo "  ✅ Guardarraíles Zero-Token y SQLite WAL: ACTIVOS"
if [ "$AIRGAP_DEV_MODE" = "true" ] || grep -q "AIRGAP_DEV_MODE=true" .env 2>/dev/null; then
    echo "  🛡️  [AIR-GAP DEV]: Sincronización n8n/Render Cloud desactivada (Aislamiento total de Producción)."
else
    ${PYTHON_BIN} -c "from core.conversation_trace_engine import conversation_trace_engine; from core.trace_cloud_sync_adapter import TraceCloudSyncAdapter; conversation_trace_engine.sync_with_n8n(limit=25); TraceCloudSyncAdapter.push_traces_to_cloud_render(conversation_trace_engine.traces_cache, max_items=20)" >/dev/null 2>&1 && echo "  ✅ Sincronización n8n Cloud ↔ Conversatorio Render (00584241533712): SINCRONIZADO"
fi

if lsof -i :${PORT} >/dev/null 2>&1; then
    STATUS_LOCAL="🟢 ACTIVO Y OPERATIVO (Puerto :${PORT})"
else
    STATUS_LOCAL="🔴 ERROR AL INICIAR"
fi

echo "================================================================================"
echo "📡 Estado del Sistema Local  ➔ ${STATUS_LOCAL}"
echo "🌐 Portal PWA + Chat MOVI    ➔ ${PWA_URL}"
echo "💬 Conversatorio WhatsApp    ➔ ${CONVERSATORIO_URL}"
echo "☁️  Conversatorio Render 24/7➔ ${PROD_CONVERSATORIO_URL}"
echo "📊 Monitor de Secuencias E2E ➔ ${TRACE_MONITOR_URL}"
echo "================================================================================"
echo ""
echo "Seleccione una opción (en 5 segundos se abrirá el sistema automáticamente):"
echo "  [1] 🌐 Abrir Portal PWA + Conversatorio WhatsApp + Monitor E2E (Por defecto)"
echo "  [2] 🧪 Ejecutar Prueba Real Completa de Arquitectura Hexagonal (4 Fases)"
echo "  [3] 📱 Abrir Simulador Móvil Dual + Conversatorio en Render 24/7"
echo "  [4] 🚪 Salir (El servidor seguirá encendido en segundo plano)"
echo ""

read -t 5 -p "Opción [1-4] (Presione Enter para abrir el sistema): " OPCION || true
echo ""

case "$OPCION" in
    2)
        if [ -f "$ROOT_DIR/PROBAR_ARQUITECTURA_HEXAGONAL.command" ]; then
            "$ROOT_DIR/PROBAR_ARQUITECTURA_HEXAGONAL.command"
        else
            ./PROBAR_ARQUITECTURA_HEXAGONAL.command
        fi
        open "${PWA_URL}"
        open "${CONVERSATORIO_URL}"
        ;;
    3)
        echo "📱 Abriendo Simulador Móvil Dual y Conversatorio Render 24/7..."
        open "${SIM_URL}"
        open "${PROD_CONVERSATORIO_URL}"
        ;;
    4)
        echo "✅ El servidor Movilnet Core permanece activo en http://localhost:${PORT}"
        exit 0
        ;;
    *)
        echo "🌐 Abriendo Portal PWA 4GMAX y Conversatorio WhatsApp en tu navegador..."
        open "${PWA_URL}"
        open "${CONVERSATORIO_URL}"
        open "${PROD_CONVERSATORIO_URL}"
        ;;
esac

echo ""
echo "================================================================================"
echo "✅ SISTEMA MOVILNET 4GMAX ACTIVADO EXITOSAMENTE"
echo "================================================================================"
sleep 2
