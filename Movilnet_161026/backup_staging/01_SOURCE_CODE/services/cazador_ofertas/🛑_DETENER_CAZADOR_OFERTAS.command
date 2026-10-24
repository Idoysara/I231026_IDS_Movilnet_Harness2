#!/bin/bash
# ==============================================================================
# 🛑 DETENER CAZADOR DE OFERTAS MOVILNET (PUERTO :8030)
# ==============================================================================

echo "======================================================================"
echo "🛑  DETENIENDO CAZADOR DE OFERTAS MOVILNET"
echo "======================================================================"

PID_ACTIVO=$(lsof -ti :8030)
if [ -n "$PID_ACTIVO" ]; then
    echo "⚠️  Proceso detectado en puerto :8030 (PID $PID_ACTIVO). Terminando..."
    kill -9 $PID_ACTIVO 2>/dev/null
    sleep 1
    echo "✅ Puerto :8030 liberado correctamente."
    osascript -e 'display notification "Servidor en puerto 8030 detenido con éxito." with title "🛑 Cazador Detenido" sound name "Tink"' 2>/dev/null
else
    echo "ℹ️  No se encontraron procesos activos en el puerto :8030."
fi

echo "======================================================================"
echo "👋 Sistema detenido de forma segura."
echo "======================================================================"
sleep 2
