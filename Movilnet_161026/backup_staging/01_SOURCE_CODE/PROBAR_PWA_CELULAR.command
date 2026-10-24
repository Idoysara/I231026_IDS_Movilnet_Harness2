#!/bin/bash
cd "$(dirname "$0")"
PORT=8010
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")
TAILSCALE_IP=$(ifconfig 2>/dev/null | grep -E "inet 100\." | awk '{print $2}' | head -n 1)

echo "========================================================================"
echo "📱 MOVILNET CORE 4GMAX — SIMULADOR PWA & PRUEBAS EN CELULAR"
echo "========================================================================"
echo "📡 En tu celular (misma red Wi-Fi): http://${LOCAL_IP}:${PORT}/ui/pwa_stitch/index.html?v=168"
if [ -n "${TAILSCALE_IP}" ]; then
    echo "🔒 En tu celular (Tailscale Global): http://${TAILSCALE_IP}:${PORT}/ui/pwa_stitch/index.html?v=168"
fi
echo "☁️  En tu celular (Nube Render 24/7): https://movilnet-core.onrender.com/ui/pwa_stitch/index.html?v=168"
echo "========================================================================"

open "http://localhost:${PORT}/ui/pwa_stitch/simulador.html?v=168"
