"""
Suite de Pruebas Automatizadas para Estación 5: Frontend PWA Mobile-First y Empaquetado OmniBox.
Verifica:
1. Disponibilidad y validación del Web App Manifest (/manifest.json).
2. Disponibilidad y sintaxis del Service Worker (/sw.js).
3. Integración PWA en index.html (manifest, mobile tags, Zero-Rating banner).
4. Disponibilidad de iconos SVG PWA (/static/icon-192.svg, /static/icon-512.svg).
5. Integridad del bundle nativo macOS (Cazador_Ofertas.app, Info.plist, launcher ejecutable).
6. Integridad de los scripts lanzadores .command con permisos ejecutables (+x).
"""
import os
import sys
import plistlib
from pathlib import Path
import pytest
from starlette.testclient import TestClient

# Configuración limpia de sys.path
CLIENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

for p in (str(PROJECT_ROOT), str(CLIENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.infrastructure.app import app

@pytest.fixture
def client():
    return TestClient(app)

# =============================================================================
# 1. PRUEBAS DEL FRONTEND PWA Y SERVICIO ESTÁTICO
# =============================================================================

def test_pwa_manifest_endpoint_y_estructura(client):
    """El endpoint /manifest.json debe retornar el manifiesto W3C con modo standalone."""
    resp = client.get("/manifest.json")
    assert resp.status_code == 200
    data = resp.json()

    assert data["name"] == "Cazador de Ofertas Movilnet"
    assert data["short_name"] == "Cazador"
    assert data["display"] == "standalone"
    assert data["theme_color"] == "#020617"
    assert data["background_color"] == "#020617"
    assert len(data["icons"]) >= 2

def test_pwa_service_worker_endpoint(client):
    """El endpoint /sw.js debe servir el Service Worker con cabeceras de JavaScript."""
    resp = client.get("/sw.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers.get("content-type", "")
    assert "cazador-movilnet" in resp.text
    assert "addEventListener('install'" in resp.text

def test_pwa_index_html_integracion(client):
    """El entrypoint / debe renderizar la PWA con metadatos y contenedor de mapa y QR."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # Validar metadatos PWA
    assert '<link rel="manifest" href="/manifest.json">' in html
    assert 'name="theme-color" content="#020617"' in html
    assert 'name="mobile-web-app-capable" content="yes"' in html
    
    # Validar secciones funcionales
    assert 'id="zero-rating-banner"' in html
    assert 'id="map"' in html
    assert 'id="qrcode-box"' in html
    assert 'id="pos-signature"' in html
    assert 'id="billing-msisdn"' in html

def test_pwa_iconos_svg_estaticos(client):
    """Los iconos SVG 192x192 y 512x512 deben estar disponibles bajo /static/."""
    resp192 = client.get("/static/icon-192.svg")
    assert resp192.status_code == 200
    assert "<svg" in resp192.text

    resp512 = client.get("/static/icon-512.svg")
    assert resp512.status_code == 200
    assert "<svg" in resp512.text

# =============================================================================
# 2. PRUEBAS DE EMPAQUETADO OMNIBOX (CERO TERMINAL EN MACOS)
# =============================================================================

def test_omnibox_macos_app_bundle():
    """El bundle nativo Cazador_Ofertas.app debe existir y tener Info.plist y launcher válidos."""
    app_dir = CLIENT_ROOT / "Cazador_Ofertas.app"
    plist_path = app_dir / "Contents" / "Info.plist"
    launcher_path = app_dir / "Contents" / "MacOS" / "launcher"

    assert app_dir.is_dir(), "El bundle Cazador_Ofertas.app no existe."
    assert plist_path.is_file(), "Info.plist no existe en el bundle .app."
    assert launcher_path.is_file(), "El ejecutable launcher no existe en MacOS/."

    # Validar Info.plist
    with open(plist_path, "rb") as f:
        plist_data = plistlib.load(f)
    assert plist_data.get("CFBundleExecutable") == "launcher"
    assert plist_data.get("CFBundleIdentifier") == "io.idscore.cazador.ofertas.movilnet"
    assert plist_data.get("CFBundleName") == "Cazador_Ofertas"

    # Validar permisos de ejecución
    assert os.access(launcher_path, os.X_OK), "El archivo launcher no tiene permisos de ejecución (+x)."

def test_omnibox_command_launchers():
    """Los scripts .command deben existir, tener permisos ejecutables y orquestar el puerto :8030."""
    start_cmd = CLIENT_ROOT / "🚀_INICIAR_CAZADOR_OFERTAS.command"
    stop_cmd = CLIENT_ROOT / "🛑_DETENER_CAZADOR_OFERTAS.command"

    assert start_cmd.is_file(), "El script 🚀_INICIAR_CAZADOR_OFERTAS.command no existe."
    assert stop_cmd.is_file(), "El script 🛑_DETENER_CAZADOR_OFERTAS.command no existe."

    assert os.access(start_cmd, os.X_OK), "🚀_INICIAR_CAZADOR_OFERTAS.command debe ser ejecutable (+x)."
    assert os.access(stop_cmd, os.X_OK), "🛑_DETENER_CAZADOR_OFERTAS.command debe ser ejecutable (+x)."

    with open(start_cmd, "r", encoding="utf-8") as f:
        content_start = f.read()
    assert ":8030" in content_start
    assert "uvicorn" in content_start

    with open(stop_cmd, "r", encoding="utf-8") as f:
        content_stop = f.read()
    assert ":8030" in content_stop
    assert "lsof -ti :8030" in content_stop
