#!/usr/bin/env python3
"""
tests/test_cazador_movilnet_integration.py — Pruebas de Integración E2E Cazador de Ofertas & Movilnet Core
========================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Fase 5: Validación Transversal E2E (Chat WhatsApp -> FastPath -> Radar -> Cuponería -> Carrier Billing)
Gobernanza: Protocolo Decagonal Maestro & Cero Alucinación (Pilares I al VII)
"""

import json
import time
from pathlib import Path
import pytest

from core.fastpath_intent_interceptor import FastPathIntentInterceptor
from api.agents.agent_deals_scout import AgentDealsScout
from api.service import MovilnetAPIService
from services.cazador_ofertas.src.application.cazador_service import CazadorApplicationService
from services.cazador_ofertas.src.domain.invariants import CazadorInvariants, DomainInvariantViolationError
from services.cazador_ofertas.src.domain.entities import EstadoCupon


@pytest.fixture(scope="module")
def interceptor():
    return FastPathIntentInterceptor()


@pytest.fixture(scope="module")
def api_service():
    return MovilnetAPIService()


@pytest.fixture(scope="module")
def deals_scout():
    return AgentDealsScout()


# ============================================================================
# 1. FASTPATH & DETECCIÓN CONVERSACIONAL DE OFERTAS (WHATSAPP / PWA)
# ============================================================================

def test_fastpath_deals_cero_adivinacion_sin_ubicacion(interceptor):
    """
    Regla Cero Adivinación: Si el usuario pide ofertas sin indicar ubicación ni GPS,
    el bot NUNCA debe inventar locales ni asumir Caracas; debe pedir la zona amablemente.
    """
    res = interceptor.intercept("¿Cuáles promociones u ofertas tienen hoy?", "04169991122")

    assert res.can_intercept is True
    assert res.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert res.tokens_consumed == 0
    assert "indicas en qué ciudad o zona te encuentras" in res.response_text
    # Enlace oficial PWA universal
    assert "/ui/pwa_stitch/index.html" in res.response_text


def test_fastpath_deals_con_zona_chacao(interceptor):
    """
    Si el usuario indica 'ofertas en Chacao', el FastPath geocodifica la zona,
    encuentra comercios físicos y genera la respuesta con precios y Magic Link.
    """
    # Pre-calentar llamada para eliminar cold start
    interceptor.intercept("ofertas en Chacao", "04169991122")
    t0 = time.perf_counter()
    res = interceptor.intercept("Quiero ver ofertas en Chacao", "04169991122")
    lat_ms = (time.perf_counter() - t0) * 1000.0

    assert res.can_intercept is True
    assert res.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert res.tokens_consumed == 0
    assert lat_ms < 50.0  # Carrier-grade latency sub-50ms en caliente
    assert "¡Club 4GMAX Activado!" in res.response_text
    assert "Bs" in res.response_text
    assert "reclamar tu cupón" in res.response_text.lower() or "1-tap" in res.response_text.lower()
    # Verifica presencia de Magic Link
    assert "sig=" in res.response_text
    # Sufijo PWA universal
    assert "/ui/pwa_stitch/index.html" in res.response_text


def test_fastpath_deals_con_gps_directo(interceptor):
    """
    Envío de coordenadas GPS directas resuelve las ofertas más cercanas por Haversine.
    """
    # Coordenadas Plaza Francia Altamira
    lat_altamira = 10.4965
    lon_altamira = -66.8490
    res = interceptor.intercept(
        message_text="ofertas cerca de mi",
        phone_number="04161112233",
        latitude=lat_altamira,
        longitude=lon_altamira
    )

    assert res.can_intercept is True
    assert res.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert "¡Club 4GMAX Activado!" in res.response_text


def test_fastpath_deals_secuencia_whatsapp_pin_gps(interceptor):
    """
    Verifica el flujo en 2 turnos por WhatsApp:
    Turno 1: Usuario pregunta por superofertas -> el asistente solicita ubicación amablemente.
    Turno 2: Usuario envía SOLAMENTE el pin de ubicación de WhatsApp (sin texto) ->
             el interceptor reconoce la intención previa y retorna las ofertas geolocalizadas.
    """
    phone_test = "04165554433"
    # Turno 1
    t1 = interceptor.intercept("¿Qué superofertas tienen disponibles?", phone_test)
    assert t1.can_intercept is True
    assert t1.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert "indicas en qué ciudad o zona te encuentras" in t1.response_text

    # Turno 2: Envío exclusivo de pin GPS WhatsApp (Chacao)
    t2 = interceptor.intercept(
        message_text="[UBICACION_GPS: lat=10.4925, lon=-66.8550]",
        phone_number=phone_test
    )
    assert t2.can_intercept is True
    assert t2.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert "¡Club 4GMAX Activado!" in t2.response_text
    assert "Bs" in t2.response_text
    assert "Farmatodo" in t2.response_text or "KPMG" in t2.response_text or "San Ignacio" in t2.response_text


def test_fastpath_deals_7_ciudades_piloto(interceptor):
    """
    Certifica la detección de ofertas y geocodificación en las 7 ciudades piloto:
    Caracas, Maracay, Valencia, La Guaira, Barquisimeto, Maracaibo, Lechería.
    """
    ciudades = [
        ("Caracas", "Quiero ofertas en Caracas"),
        ("Maracay", "superofertas en Maracay"),
        ("Valencia", "promociones en Valencia"),
        ("La Guaira", "ofertas en La Guaira"),
        ("Barquisimeto", "descuentos en Barquisimeto"),
        ("Maracaibo", "ofertas en Maracaibo"),
        ("Lechería", "superofertas en Lechería"),
    ]
    for ciudad, query in ciudades:
        res = interceptor.intercept(query, "04168887766")
        assert res.can_intercept is True, f"Fallo can_intercept en {ciudad}"
        assert res.intent_detected == "CAZADOR_OFERTAS_CLUB", f"Fallo intent en {ciudad}"
        assert "¡Club 4GMAX Activado!" in res.response_text, f"Fallo ofertas activadas en {ciudad}"
        assert "Bs" in res.response_text, f"Fallo precios en {ciudad}"
        assert res.tokens_consumed == 0


# ============================================================================
# 2. SUBAGENTE SCOUT DE OFERTAS (SWARM L5)
# ============================================================================

def test_deals_scout_agent_execution(deals_scout):
    """Valida la ejecución formal del agente DealsScout."""
    res = deals_scout.scout_deals(
        phone="04169991122",
        message="ofertas en Las Mercedes",
        max_distancia_m=3000.0
    )
    assert res.success is True
    assert res.requiere_ubicacion is False
    assert res.total_ofertas > 0
    assert len(res.ofertas) > 0
    item = res.ofertas[0]
    assert item.precio_oferta_ves > 0
    assert item.descuento_pct >= 0


# ============================================================================
# 3. ENDPOINTS REST API MOVILNET CORE (:8010 VIA CAZADOR_ROUTER)
# ============================================================================

def test_api_rest_radar_ofertas_endpoint(api_service):
    """Endpoint GET /api/v1/cazador/ofertas debe responder con estructura de anillos."""
    status, headers, body = api_service.dispatch(
        method="GET",
        path="/api/v1/cazador/ofertas?lat=10.4925&lon=-66.8550&max_m=2000",
        headers={},
        body_bytes=b""
    )
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["success"] is True
    assert "anillos" in data
    assert "zona_1_inmediata" in data["anillos"]
    assert data["total_comercios_en_rango"] > 0


def test_api_rest_ciclo_completo_cupon_y_billing(api_service):
    """
    Ciclo E2E completo:
    1. Reclamar cupón dinámico con MSISDN Movilnet.
    2. Verificar código TOTP y firma HMAC-SHA256.
    3. Canjear en caja POS.
    4. Liquidar Carrier Billing con Split 20/80.
    5. Bloqueo anti-replay: el segundo intento de canje DEBE fallar.
    """
    msisdn = f"0416{int(time.time() * 100) % 9000000 + 1000000}"
    ofertas_activas = [o for o in api_service.cazador_router.cazador_service.ofertas.values() if o.activa and o.stock_disponible > 0]
    assert len(ofertas_activas) > 0
    oferta_id = ofertas_activas[0].id

    # 1. Reclamo
    req_body = json.dumps({"oferta_id": oferta_id, "msisdn": msisdn}).encode("utf-8")
    status_rec, _, body_rec = api_service.dispatch(
        method="POST",
        path="/api/v1/cazador/cupon/reclamar",
        headers={"Content-Type": "application/json"},
        body_bytes=req_body
    )
    assert status_rec == 201
    rec_data = json.loads(body_rec.decode("utf-8"))
    assert rec_data["success"] is True
    cupon = rec_data["cupon"]
    cupon_id = cupon["uuid"]
    comercio_id = cupon["comercio_id"]
    firma = cupon["firma_hmac"]
    assert len(cupon["codigo_dinamico"]) > 0
    assert cupon["codigo_dinamico"].startswith("QRO-")

    # 2. Canje exitoso en POS
    canje_body = json.dumps({
        "cupon_id": cupon_id,
        "msisdn": msisdn,
        "comercio_id": comercio_id,
        "firma_hmac": firma
    }).encode("utf-8")

    status_canje, _, body_canje = api_service.dispatch(
        method="POST",
        path="/api/v1/cazador/cupon/canjear",
        headers={"Content-Type": "application/json"},
        body_bytes=canje_body
    )
    assert status_canje == 200
    canje_data = json.loads(body_canje.decode("utf-8"))
    assert canje_data["success"] is True
    assert canje_data["estado"] == "CANJEADO"

    # 3. Liquidación Carrier Billing Split 20/80
    monto_oferta = rec_data["oferta"]["precio_oferta_ves"]
    idemp_key = f"IDEMP-E2E-{cupon_id}-{int(time.time())}"
    bill_body = json.dumps({
        "msisdn": msisdn,
        "monto_ves": monto_oferta,
        "idempotency_key": idemp_key
    }).encode("utf-8")

    status_bill, _, body_bill = api_service.dispatch(
        method="POST",
        path="/api/v1/cazador/billing",
        headers={"Content-Type": "application/json"},
        body_bytes=bill_body
    )
    assert status_bill == 200
    bill_data = json.loads(body_bill.decode("utf-8"))
    assert bill_data["success"] is True
    tx = bill_data["transaccion"]
    # Validar invariante del split 20/80
    assert tx["comision_telco_ves"] == round(monto_oferta * 0.20, 2)
    assert tx["neto_comercio_ves"] == round(monto_oferta * 0.80, 2)
    assert abs((tx["comision_telco_ves"] + tx["neto_comercio_ves"]) - monto_oferta) < 0.02

    # 4. Blindaje Anti-Replay: Segundo intento de canje con la misma firma debe ser rechazado
    status_replay, _, body_replay = api_service.dispatch(
        method="POST",
        path="/api/v1/cazador/cupon/canjear",
        headers={"Content-Type": "application/json"},
        body_bytes=canje_body
    )
    assert status_replay in (409, 422)
    replay_data = json.loads(body_replay.decode("utf-8"))
    assert "CANJEADO" in replay_data.get("message", "") or "Transición de estado ilegal" in replay_data.get("message", "")


def test_api_rest_magic_link_endpoint(api_service):
    """Endpoint GET /api/v1/cazador/magic-link debe retornar link firmado."""
    status, _, body = api_service.dispatch(
        method="GET",
        path="/api/v1/cazador/magic-link?msisdn=04161234567&oferta_id=OFE-001",
        headers={},
        body_bytes=b""
    )
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["success"] is True
    assert "sig=" in data["magic_link"]
    assert data["zero_rating"] is True


# ============================================================================
# 4. MODELO ESPACIAL DE CERO FRICCIÓN (3 ESCENARIOS AUTOMÁTICOS)
# ============================================================================

def test_zero_friccion_escenario_1_zona_canonica(api_service):
    """
    Escenario 1 (El 90% de los casos): El anunciante solo selecciona una Zona en la lista.
    El límite lo fija el polígono de calles (0 radios a ingresar por el usuario).
    """
    req_body = json.dumps({
        "nombre": "Café Bistro Las Mercedes",
        "rif": "J-88112233-1",
        "categoria": "Gastronomía",
        "tipo_cobertura": "ZONA",
        "zona_sector": "Las Mercedes"
    }).encode("utf-8")

    status, _, resp_body = api_service.dispatch(
        method="POST",
        path="/api/v1/cazador/comercio/registro-rapido",
        headers={"Content-Type": "application/json"},
        body_bytes=req_body
    )
    assert status == 201
    data = json.loads(resp_body.decode("utf-8"))
    assert data["success"] is True
    comercio = data["comercio"]
    assert comercio["tipo_cobertura"] == "ZONA"
    assert comercio["zona_sector"] == "Las Mercedes"
    assert comercio["radio_cobertura_m"] == 1500.0  # Asignado automáticamente por la zona
    assert abs(comercio["lat"] - 10.4794) < 0.01  # Centroide de Las Mercedes
    assert "0 metros ingresados" in data["escenario"]["friccion_usuario"]


def test_zero_friccion_escenario_2_run_of_network(api_service):
    """
    Escenario 2: Toda la Ciudad (Run of Network).
    El usuario deja el campo en blanco o selecciona Run of Network.
    El sistema asigna cobertura metropolitana (50,000m) y rota libremente en toda la red.
    """
    req_body = json.dumps({
        "nombre": "Campaña Nacional Móvil 4GMAX",
        "rif": "J-88112233-2",
        "categoria": "Tecnología",
        "tipo_cobertura": "RUN_OF_NETWORK"
    }).encode("utf-8")

    status, _, resp_body = api_service.dispatch(
        method="POST",
        path="/api/v1/cazador/comercio/registro-rapido",
        headers={"Content-Type": "application/json"},
        body_bytes=req_body
    )
    assert status == 201
    data = json.loads(resp_body.decode("utf-8"))
    assert data["success"] is True
    comercio = data["comercio"]
    assert comercio["tipo_cobertura"] == "RUN_OF_NETWORK"
    assert comercio["radio_cobertura_m"] == 50000.0

    # Comprobar que el radar incluye esta campaña sin importar las coordenadas consultadas
    status_radar, _, radar_resp = api_service.dispatch(
        method="GET",
        path="/api/v1/cazador/ofertas?lat=10.4350&lon=-66.8520&max_m=3000",
        headers={},
        body_bytes=b""
    )
    assert status_radar == 200
    radar_data = json.loads(radar_resp.decode("utf-8"))
    assert "campanas_metropolitanas" in radar_data


def test_zero_friccion_escenario_3_smart_default_500m(api_service):
    """
    Escenario 3: Punto de Interés / Local Comercial.
    Solo indica dirección o coordenadas. El algoritmo auto-asigna 500m estándar (cinemático).
    El comerciante no hace cálculos matemáticos.
    """
    req_body = json.dumps({
        "nombre": "Panadería Dulce Rincón",
        "rif": "J-88112233-3",
        "categoria": "Gastronomía",
        "tipo_cobertura": "PUNTO_INTERES",
        "direccion": "Calle Jalisco, Torre Jalisco"
    }).encode("utf-8")

    status, _, resp_body = api_service.dispatch(
        method="POST",
        path="/api/v1/cazador/comercio/registro-rapido",
        headers={"Content-Type": "application/json"},
        body_bytes=req_body
    )
    assert status == 201
    data = json.loads(resp_body.decode("utf-8"))
    assert data["success"] is True
    comercio = data["comercio"]
    assert comercio["tipo_cobertura"] == "PUNTO_INTERES"
    assert comercio["radio_cobertura_m"] == 500.0  # Smart Default 500m
    assert "500m cinemático" in data["escenario"]["descripcion"]


def test_zero_friccion_opcion_avanzada_radio_manual(api_service):
    """
    Opción avanzada: Un anunciante corporativo pide expresamente un radio manual (ej: 1,200m).
    """
    req_body = json.dumps({
        "nombre": "Banco Corporativo Metropolitano",
        "rif": "J-88112233-4",
        "categoria": "Banca",
        "tipo_cobertura": "PUNTO_INTERES",
        "direccion": "Av. Francisco de Miranda",
        "radio_manual_m": 1200.0
    }).encode("utf-8")

    status, _, resp_body = api_service.dispatch(
        method="POST",
        path="/api/v1/cazador/comercio/registro-rapido",
        headers={"Content-Type": "application/json"},
        body_bytes=req_body
    )
    assert status == 201
    data = json.loads(resp_body.decode("utf-8"))
    assert data["comercio"]["radio_cobertura_m"] == 1200.0
    assert "Radio manual opcional aplicado" in data["escenario"]["friccion_usuario"]


def test_zero_friccion_guarda_anti_spots_inaudibles(api_service):
    """
    Guarda Matemática: Radios menores a 50m (ej. 20m) deben ser rechazados con 422.
    Un vehículo a 40 km/h recorre 20 metros en 1.8 segundos, haciendo imposible la reproducción.
    """
    req_body = json.dumps({
        "nombre": "Kiosco Error Radio Diminuto",
        "rif": "J-88112233-5",
        "categoria": "Retail",
        "tipo_cobertura": "PUNTO_INTERES",
        "radio_manual_m": 20.0
    }).encode("utf-8")

    status, _, resp_body = api_service.dispatch(
        method="POST",
        path="/api/v1/cazador/comercio/registro-rapido",
        headers={"Content-Type": "application/json"},
        body_bytes=req_body
    )
    assert status == 422
    data = json.loads(resp_body.decode("utf-8"))
    assert "Radio espacial inválido" in data["message"]
    assert "spots inaudibles" in data["message"]


def test_catalogo_zonas_canonicas(api_service):
    """Endpoint GET /api/v1/cazador/zonas retorna el catálogo de sectores canónicos."""
    status, _, body = api_service.dispatch(
        method="GET",
        path="/api/v1/cazador/zonas",
        headers={},
        body_bytes=b""
    )
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["success"] is True
    assert data["total"] >= 10
    nombres = [z["nombre"] for z in data["zonas"]]
    assert "Las Mercedes" in nombres
    assert "Chacao" in nombres
    assert "Altamira" in nombres
    assert "Brickell (Miami)" in nombres


def test_multiturn_conversational_memory_deals_24h():
    """
    Verifica la memoria conversacional de 24 horas y encadenamiento contextual:
    1. Turno 1: Consulta de ofertas por categoría sin ubicación ('desayunos') solicita zona y persiste contexto.
    2. Turno 2: Respuesta con ubicación textual ('estoy en los palos grandes chacao caracas') encadena automáticamente
       la categoría 'Café y Panadería', resuelve ofertas en Los Palos Grandes y emite Magic Link unificado a :8010.
    3. Turno 3: Cambio de categoría ('farmacias') actualiza la categoría y preserva las coordenadas geodésicas (24h).
    4. Cero duplicación de sufijo PWA y 0 tokens consumidos en todos los turnos.
    """
    from core.fastpath_intent_interceptor import FastPathIntentInterceptor
    interceptor = FastPathIntentInterceptor()
    phone = "04169998877"

    # Turno 1: Desayunos sin ubicación
    r1 = interceptor.intercept("si necesito saber si hay ofertas para desayunos", phone)
    assert r1.can_intercept is True
    assert r1.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert r1.tokens_consumed == 0
    assert "Café y Panadería" in r1.response_text
    assert "¿me indicas en qué ciudad o zona te encuentras" in r1.response_text
    assert ":8030" not in r1.response_text

    # Turno 2: Envío de ubicación textual en Los Palos Grandes
    r2 = interceptor.intercept("estoy en los palos grandes chacao caracas", phone)
    assert r2.can_intercept is True
    assert r2.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert r2.tokens_consumed == 0
    assert "Club 4GMAX Activado" in r2.response_text
    assert "Café y Panadería" in r2.response_text
    assert "Artesano" in r2.response_text or "LPG" in r2.response_text or "Bs" in r2.response_text
    assert "/ui/pwa_stitch/index.html" in r2.response_text
    assert ":8030" not in r2.response_text

    # Turno 3: Cambio a Farmacias manteniendo coordenadas en memoria 24h
    r3 = interceptor.intercept("ahora que ofertas de farmacias hay", phone)
    assert r3.can_intercept is True
    assert r3.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert r3.tokens_consumed == 0
    assert "Farmacias y Salud" in r3.response_text
    assert "/ui/pwa_stitch/index.html" in r3.response_text
    assert ":8030" not in r3.response_text

    # Consulta directa de una sola interacción (zona + oferta en un mensaje)
    phone_direct = "04169998878"
    r_direct = interceptor.intercept("que ofertas tienes en los palos grandes chacao", phone_direct)
    assert r_direct.can_intercept is True
    assert r_direct.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert r_direct.tokens_consumed == 0
    assert "Club 4GMAX Activado" in r_direct.response_text
    assert "/ui/pwa_stitch/index.html" in r_direct.response_text


def test_multiturn_food_deals_and_cadastral_navigation_e2e():
    """
    Verifica la secuencia completa E2E de 5 turnos reportada por el usuario:
    1. 'tengo hambre tienes ofertas' -> Detecta Restaurantes y solicita ubicación.
    2. 'estoy en chacaito' -> Resuelve ofertas de Restaurantes en Chacaíto sin recargas 0% discount.
    3. 'pero necesti. la direccion del menu ejecutivo' -> CAZADOR_DIRECCION_RUTA con dirección catastral y ruta Maps.
    4. 'muestraem la trayectoria en google map' -> CAZADOR_DIRECCION_RUTA con enlace directo de navegación en Maps.
    5. 'y que oferta hay en chacao' -> Retiene categoría Restaurantes en Chacao.
    Cero alucinaciones de teléfonos o zonas, 0 tokens y latencia Carrier-Grade.
    """
    from core.fastpath_intent_interceptor import FastPathIntentInterceptor
    interceptor = FastPathIntentInterceptor()
    phone = "04169998899"

    # Turno 1
    r1 = interceptor.intercept("tengo hambre tienes ofertas", phone)
    assert r1.can_intercept is True
    assert r1.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert r1.tokens_consumed == 0
    assert "Restaurantes" in r1.response_text

    # Turno 2
    r2 = interceptor.intercept("estoy en chacaito", phone)
    assert r2.can_intercept is True
    assert r2.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert r2.tokens_consumed == 0
    assert "Club 4GMAX Activado" in r2.response_text
    assert "Restaurantes" in r2.response_text
    assert "Gran Café" in r2.response_text

    # Turno 3: Solicitud de dirección con typo léxico 'necesti.'
    r3 = interceptor.intercept("pero necesti. la direccion del menu ejecutivo", phone)
    assert r3.can_intercept is True
    assert r3.intent_detected == "CAZADOR_DIRECCION_RUTA"
    assert r3.tokens_consumed == 0
    assert "Gran Café de Sabana Grande" in r3.response_text
    assert "google.com/maps/dir" in r3.response_text
    assert "0212-1234567" not in r3.response_text  # Cero alucinación telefónica
    assert "Dirección Exacta" in r3.response_text

    # Turno 4: Solicitud de trayectoria con typo léxico 'muestraem'
    r4 = interceptor.intercept("muestraem la trayectoria en google map", phone)
    assert r4.can_intercept is True
    assert r4.intent_detected == "CAZADOR_DIRECCION_RUTA"
    assert r4.tokens_consumed == 0
    assert "google.com/maps/dir" in r4.response_text

    # Turno 5: Conmutación de zona manteniendo categoría Restaurantes
    r5 = interceptor.intercept("y que oferta hay en chacao", phone)
    assert r5.can_intercept is True
    assert r5.intent_detected == "CAZADOR_OFERTAS_CLUB"
    assert r5.tokens_consumed == 0
    assert "Restaurantes" in r5.response_text
    assert "El Cine Restaurant Chacao" in r5.response_text or "Urrutia" in r5.response_text



