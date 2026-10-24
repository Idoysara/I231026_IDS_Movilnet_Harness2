"""
Suite de Pruebas Automatizadas para Estación 4: Core Backend API REST y Deflector de Conectividad.
Verifica:
1. Generación y Validación de Magic Links Criptográficos HMAC Zero-Rating.
2. Inyección de Cabeceras HTTP de Exención de Datos (X-Movilnet-Zero-Rating).
3. Webhook Deflector WhatsApp con Grounding B2C Estricto (Cero Alucinación).
4. Webhook Deflector SMS SMPP con Clamping (<160 caracteres).
5. Endpoints Modulares de Consulta de Cupones por Usuario e Historial de Facturación.
6. Rechazo de números ajenos a Movilnet (0414/0412/0424).
"""
import sys
import time
from pathlib import Path
import pytest
from starlette.testclient import TestClient

# Configuración limpia de sys.path
CLIENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

for p in (str(PROJECT_ROOT), str(CLIENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.infrastructure.app import app, service, deflector_service
from src.infrastructure.deflector.magic_link_service import MagicLinkService
from src.domain.invariants import DomainInvariantViolationError

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def magic_service():
    return MagicLinkService(service)

# =============================================================================
# 1. PRUEBAS DEL SERVICIO MAGIC LINK & ZERO-RATING
# =============================================================================

def test_magic_link_generacion_y_verificacion(magic_service):
    """Generación de enlace firmado y validación criptográfica."""
    msisdn = "04161234567"
    link = magic_service.generar_magic_link(msisdn=msisdn, duracion_segundos=3600)
    
    assert "http://localhost:8030/?" in link
    assert "msisdn=04161234567" in link
    assert "sig=" in link
    assert "exp=" in link

    # Parsear parámetros generados
    import urllib.parse
    parsed = urllib.parse.urlparse(link)
    qs = urllib.parse.parse_qs(parsed.query)

    exp_val = int(qs["exp"][0])
    sig_val = qs["sig"][0]

    # Validar firma válida
    valido, motivo = magic_service.verificar_magic_link(
        msisdn=msisdn,
        exp_timestamp=exp_val,
        firma=sig_val
    )
    assert valido is True
    assert "exitosamente" in motivo

    # Validar firma adulterada
    valido_bad, motivo_bad = magic_service.verificar_magic_link(
        msisdn=msisdn,
        exp_timestamp=exp_val,
        firma="firma_falsa_hack_00000000000000"
    )
    assert valido_bad is False
    assert "inválida" in motivo_bad

    # Validar enlace expirado
    valido_exp, motivo_exp = magic_service.verificar_magic_link(
        msisdn=msisdn,
        exp_timestamp=int(time.time()) - 100,
        firma=sig_val
    )
    assert valido_exp is False
    assert "expirado" in motivo_exp

def test_headers_zero_rating(magic_service):
    """Verificación de cabeceras oficiales Zero-Rating de Movilnet."""
    msisdn = "04265554433"
    headers = magic_service.obtener_headers_zero_rating(msisdn)
    
    assert headers["X-Movilnet-Zero-Rating"] == "active"
    assert headers["X-Zero-Rating-Carrier"] == "Movilnet-0416-0426"
    assert headers["X-Zero-Rating-Subscriber"] == msisdn

    # Número no-Movilnet debe ser rechazado
    with pytest.raises(DomainInvariantViolationError):
        magic_service.obtener_headers_zero_rating("04149998877")

# =============================================================================
# 2. PRUEBAS DE DEFLEXIÓN CONVERSACIONAL (WHATSAPP & SMS SMPP)
# =============================================================================

def test_deflector_whatsapp_con_coincidencia(client):
    """Búsqueda conversacional por WhatsApp con ofertas existentes verificadas."""
    resp = client.post("/api/deflector/whatsapp", json={
        "canal": "whatsapp",
        "remitente": "+58 416 1234567",
        "mensaje": "Quiero comprar hamburguesa con descuento"
    })
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["canal"] == "whatsapp"
    assert data["destinatario"] == "04161234567"
    assert data["zero_rating_activo"] is True
    assert data["magic_link"] is not None
    assert "http://localhost:8030/?" in data["magic_link"]
    assert data["ofertas_encontradas"] >= 1
    assert "Cazador activado" in data["mensaje_saliente"]

def test_deflector_whatsapp_cero_alucinacion_sin_coincidencia(client):
    """Invariante B2C: Si no hay ofertas para el texto, NO alucina comercios ni precios."""
    resp = client.post("/api/deflector/whatsapp", json={
        "canal": "whatsapp",
        "remitente": "04269876543",
        "mensaje": "tienen telescopio astronomico y satelites espaciales?"
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["ofertas_encontradas"] == 0
    assert "no encontramos promociones activas" in data["mensaje_saliente"]
    # Aun así provee el enlace Zero-Rating al Radar general
    assert "http://localhost:8030/?" in data["magic_link"]

def test_deflector_whatsapp_con_coordenadas_gps(client):
    """Deflexión geolocalizada agrupada en los 3 anillos concéntricos."""
    resp = client.post("/api/deflector/whatsapp", json={
        "canal": "whatsapp",
        "remitente": "04162223344",
        "mensaje": "Dame ofertas cerca de mi ubicación actual",
        "ubicacion_lat": 10.4912,
        "ubicacion_lon": -66.8580
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["anillos_resumen"] is not None
    assert "zona_1_inmediata" in data["anillos_resumen"]
    assert data["ofertas_encontradas"] > 0
    assert "m)" in data["mensaje_saliente"]  # Distancia calculada en metros

def test_deflector_sms_smpp(client):
    """Mensaje SMS conciso con shortlink Zero-Rating garantizado."""
    resp = client.post("/api/deflector/sms-smpp", json={
        "canal": "sms",
        "remitente": "04163334455",
        "mensaje": "OFERTAS"
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["canal"] == "sms"
    assert data["destinatario"] == "04163334455"
    assert "Movilnet Cazador" in data["mensaje_saliente"]
    assert len(data["mensaje_saliente"]) <= 160

def test_deflector_rechazo_operadora_ajena(client):
    """Cualquier mensaje entrante de Digitel (0412) o Movistar (0414/0424) debe ser rechazado."""
    resp = client.post("/api/deflector/whatsapp", json={
        "canal": "whatsapp",
        "remitente": "04141112233",
        "mensaje": "Quiero ofertas"
    })
    assert resp.status_code == 422
    assert "no pertenece a la operadora Movilnet" in resp.json()["detail"]

# =============================================================================
# 3. PRUEBAS DE ENDPOINTS MODULARES REST
# =============================================================================

def test_endpoint_verificar_magic_link_http(client, magic_service):
    """Prueba del endpoint GET /api/deflector/verificar-link con inyección de cabeceras."""
    msisdn = "04161112222"
    link = magic_service.generar_magic_link(msisdn=msisdn, oferta_id="OFE-001")
    
    import urllib.parse
    parsed = urllib.parse.urlparse(link)
    qs = urllib.parse.parse_qs(parsed.query)

    exp_val = qs["exp"][0]
    sig_val = qs["sig"][0]

    # 1. Petición válida -> Status 200 y Cabecera Zero-Rating en response
    res = client.get(f"/api/deflector/verificar-link?msisdn={msisdn}&exp={exp_val}&sig={sig_val}&oferta=OFE-001")
    assert res.status_code == 200
    assert res.headers.get("x-movilnet-zero-rating") == "active"
    assert res.json()["valido"] is True

    # 2. Petición con firma adulterada -> Status 403 Forbidden
    res_bad = client.get(f"/api/deflector/verificar-link?msisdn={msisdn}&exp={exp_val}&sig=firma_invalida&oferta=OFE-001")
    assert res_bad.status_code == 403
    assert res_bad.json()["valido"] is False

def test_endpoint_consultar_cupones_usuario(client):
    """Consulta de cupones emitidos para una línea Movilnet."""
    msisdn = f"0416{int(time.time() * 1000) % 10000000:07d}"
    
    # 1. Reclamar cupón para este usuario
    rec = client.post("/api/cupon/reclamar", json={
        "oferta_id": "OFE-001",
        "msisdn": msisdn
    })
    assert rec.status_code == 201

    # 2. Consultar cupones del usuario
    res = client.get(f"/api/cupon/usuario/{msisdn}")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["total"] >= 1
    assert any(c["oferta_id"] == "OFE-001" for c in data["cupones"])

def test_endpoint_consultar_historial_billing(client):
    """Consulta de historial de débitos para un usuario Movilnet."""
    msisdn = "04268887766"
    idemp_key = f"TX-BILLING-HISTORIAL-{int(time.time())}"

    # 1. Realizar cobro
    deb = client.post("/api/billing/debitar", json={
        "msisdn": msisdn,
        "monto_ves": 120.0,
        "idempotency_key": idemp_key
    })
    assert deb.status_code == 200

    # 2. Consultar historial
    res = client.get(f"/api/billing/historial/{msisdn}")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["total"] >= 1
    assert any(t["idempotency_key"] == idemp_key for t in data["transacciones"])

def test_deflector_webhook_telegram(client):
    """Prueba del webhook específico para bots de Telegram."""
    payload = {
        "canal": "telegram",
        "remitente": "04169998877",
        "mensaje": "hamburguesa",
        "ubicacion_lat": 10.4925,
        "ubicacion_lon": -66.8550
    }
    res = client.post("/api/deflector/telegram", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["canal"] == "telegram"
    assert data["destinatario"] == "04169998877"
    assert "magic_link" in data
    assert data["zero_rating_activo"] is True
    assert data["ofertas_encontradas"] >= 1

def test_deflector_webhook_pwa(client):
    """Prueba del webhook para eventos directos de la PWA Mobile-First."""
    payload = {
        "canal": "pwa",
        "remitente": "04261112233",
        "mensaje": "farmacia",
        "ubicacion_lat": None,
        "ubicacion_lon": None
    }
    res = client.post("/api/deflector/pwa", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["canal"] == "pwa"
    assert data["destinatario"] == "04261112233"
    assert data["magic_link"] is not None

def test_deflector_webhook_n8n_gateway(client):
    """Prueba del Gateway Unificado Omnicanal consumido por n8n Workflow."""
    # 1. Petición simulada de n8n para WhatsApp
    res_wa = client.post("/api/deflector/n8n", json={
        "canal": "whatsapp",
        "remitente": "584165551234",
        "mensaje": "ofertas cerca de mi",
        "ubicacion_lat": 10.4900,
        "ubicacion_lon": -66.8500
    })
    assert res_wa.status_code == 200
    assert res_wa.json()["canal"] == "whatsapp"
    assert res_wa.json()["destinatario"] == "04165551234"

    # 2. Petición simulada de n8n para Telegram
    res_tg = client.post("/api/deflector/n8n", json={
        "canal": "telegram",
        "remitente": "04263334455",
        "mensaje": "zapatos",
        "ubicacion_lat": None,
        "ubicacion_lon": None
    })
    assert res_tg.status_code == 200
    assert res_tg.json()["canal"] == "telegram"
    assert res_tg.json()["destinatario"] == "04263334455"

def test_n8n_workflow_json_schema():
    """Valida la sintaxis, integridad de nodos y conexiones del archivo de workflow n8n."""
    import json
    wf_path = CLIENT_ROOT / "n8n" / "cazador_ofertas_n8n_workflow.json"
    assert wf_path.exists(), "El archivo cazador_ofertas_n8n_workflow.json debe existir físicamente"

    with open(wf_path, "r", encoding="utf-8") as f:
        wf = json.load(f)

    assert "nodes" in wf
    assert "connections" in wf
    assert len(wf["nodes"]) >= 10

    node_names = [n["name"] for n in wf["nodes"]]
    assert "Webhook WhatsApp" in node_names
    assert "Webhook Telegram" in node_names
    assert "Webhook PWA Event" in node_names
    assert "Normalizador Omnicanal" in node_names
    assert "¿Es Abonado Movilnet?" in node_names
    assert "Invocar Cazador Core API (:8030)" in node_names
    assert "Switch Canal Saliente" in node_names

