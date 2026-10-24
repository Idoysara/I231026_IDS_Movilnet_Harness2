#!/bin/bash
# ==============================================================================
# 🚀 LANZADOR SOBERANO — CAZADOR DE OFERTAS MOVILNET (IDS_CORE)
# Sello de Certificación: CERT-CAZADOR-PENTARCHY-20261018-SOVEREIGN
# Puerto Asignado: :8030 (FastAPI Core + PWA de Proximidad)
# ==============================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$DIR/../../" && pwd )"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "🎯  INICIANDO CAZADOR DE OFERTAS MOVILNET — CLUB DE AHORRO SOBERANO"
echo "======================================================================"
echo "📍 Directorio raíz: $PROJECT_ROOT"
echo "🔌 Puerto del servidor: http://localhost:8030"
echo "🛡️  Operadora de red: Movilnet (Prefijos 0416 / 0426)"
echo "----------------------------------------------------------------------"

# 1. Verificar entorno virtual
if [ ! -f ".venv/bin/python" ]; then
    echo "❌ Error: Entorno virtual .venv no encontrado en $PROJECT_ROOT."
    echo "Presione cualquier tecla para salir..."
    read -n 1
    exit 1
fi

# 2. Detener proceso previo en puerto 8030 si existe
PID_PREVIO=$(lsof -ti :8030)
if [ ! -z "$PID_PREVIO" ]; then
    echo "⚠️  Liberando puerto 8030 ocupado previamente (PID $PID_PREVIO)..."
    kill -9 $PID_PREVIO 2>/dev/null
    sleep 1
fi

# 3. Iniciar Servidor FastAPI
echo "🚀 Levantando servidor backend y PWA..."
export PYTHONPATH="$PROJECT_ROOT:$DIR"
.venv/bin/python -m uvicorn pruebas_clientes.28_Cazador_Ofertas.src.infrastructure.app:app --host 0.0.0.0 --port 8030 &
SERVER_PID=$!

# 4. Esperar a que el servidor responda
echo "⏳ Esperando confirmación de arranque en :8030..."
READY=0
for i in {1..20}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8030/health)
    if [ "$STATUS" == "200" ]; then
        READY=1
        break
    fi
    sleep 0.5
done

if [ "$READY" -eq 1 ]; then
    echo "✅ Servidor activo y saludable (HTTP 200 OK)."
    echo "🌐 Abriendo navegador en la aplicación PWA..."
    open "http://localhost:8030"
    
    # Notificación de escritorio en macOS
    osascript -e 'display notification "Cazador de Ofertas Movilnet listo en http://localhost:8030" with title "🎯 Cazador Movilnet Online" sound name "Glass"' 2>/dev/null

    echo "======================================================================"
    echo "🎉 ¡SISTEMA OPERATIVO Y DISPONIBLE!"
    echo "👉 Presione Ctrl+C en esta ventana para detener el servicio."
    echo "======================================================================"
    wait $SERVER_PID
else
    echo "❌ No se pudo confirmar el arranque del servidor en :8030."
    kill -9 $SERVER_PID 2>/dev/null
    echo "Presione cualquier tecla para salir..."
    read -n 1
    exit 1
fi
