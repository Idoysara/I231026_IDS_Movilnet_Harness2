#!/usr/bin/env python3
"""
tests/test_immediate_action_plan.py — Suite de Pruebas Automatizadas para el Plan de Acción Inmediato
====================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal

Cubre formalmente:
1. SessionIdentityIsolator (Aislamiento de identidad E.164, prevención de colisiones por pushName 'Ids').
2. SemanticResponseCache (Normalización, SHA-256, TTL inteligente, 0 caché en volátiles, ahorro de tokens).
3. FastPathIntentInterceptor (Intercepción determinista de saldo, planes, C2P y portabilidad en 0 tokens).
4. WebhookNoiseFilter (Filtrado de presencia, contactos, chats y descarte de fromMe=True).
5. Integración REST en MovilnetAPIService (/api/v1/cache/stats, /api/v1/fastpath/evaluate, /api/v1/session/isolate).
"""

import json
import sys
import tempfile
import shutil
from pathlib import Path

# Asegurar path raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import pytest
except ImportError:
    class _PytestMock:
        @staticmethod
        def fixture(func):
            return func
    pytest = _PytestMock()

from core.session_identity_isolator import SessionIdentityIsolator, SessionIdentity
from core.semantic_response_cache import SemanticResponseCache, CacheEntry
from core.fastpath_intent_interceptor import FastPathIntentInterceptor, FastPathResolution
from core.webhook_noise_filter import WebhookNoiseFilter, FilterVerdict, FilterResult
from api.service import MovilnetAPIService


# =====================================================================
# 1. Pruebas de Aislamiento de Identidad (SessionIdentityIsolator)
# =====================================================================
class TestSessionIdentityIsolator:

    def test_cross_contamination_prevention_same_pushname(self):
        """Verifica que dos números distintos con el mismo pushName 'Ids' NO compartan memoria."""
        id1 = SessionIdentityIsolator.isolate_session(
            remote_jid="584142554590@s.whatsapp.net",
            push_name="Ids"
        )
        id2 = SessionIdentityIsolator.isolate_session(
            remote_jid="584241533712@s.whatsapp.net",
            push_name="Ids"
        )

        assert id1.canonical_session_key != id2.canonical_session_key
        assert id1.canonical_session_key == "SESSION:E164:584142554590"
        assert id2.canonical_session_key == "SESSION:E164:584241533712"
        assert id1.blind_index_hash != id2.blind_index_hash

    def test_phone_sanitization_and_e164_formatting(self):
        """Verifica la sanitización de sufijos de WhatsApp y normalización."""
        res = SessionIdentityIsolator.isolate_session(remote_jid="584160000001:5@s.whatsapp.net")
        assert res.e164_phone == "584160000001"
        assert res.national_phone == "04160000001"
        assert res.operator == "MOVILNET"
        assert res.is_valid is True

    def test_carrier_prefix_detection(self):
        """Verifica la correcta clasificación de prefijos CONATEL."""
        movistar = SessionIdentityIsolator.isolate_session(phone_number="04141234567")
        digitel = SessionIdentityIsolator.isolate_session(phone_number="04121234567")
        movilnet = SessionIdentityIsolator.isolate_session(phone_number="04261234567")

        assert movistar.operator == "MOVISTAR"
        assert digitel.operator == "DIGITEL"
        assert movilnet.operator == "MOVILNET"


# =====================================================================
# 2. Pruebas de Caché Semántico y Ahorro de Tokens (SemanticResponseCache)
# =====================================================================
class TestSemanticResponseCache:

    @pytest.fixture
    def temp_cache(self, tmp_path):
        db_file = tmp_path / "test_cache.db"
        return SemanticResponseCache(db_path=db_file)

    def test_normalization_and_sha256_key_consistency(self, temp_cache):
        """Verifica que frases equivalentes con signos y acentos generen la misma clave."""
        p1 = "¿Estoy en Los Palos Grandes, me puedes decir qué farmacias tengo cerca?"
        p2 = "estoy en los palos grandes me puedes decir que farmacias tengo cerca"

        norm1 = temp_cache.normalize_text(p1)
        norm2 = temp_cache.normalize_text(p2)
        assert norm1 == norm2
        assert temp_cache.generate_cache_key(norm1) == temp_cache.generate_cache_key(norm2)

    def test_cache_hit_and_token_saving(self, temp_cache):
        """Verifica el almacenamiento, recuperación y contabilidad de tokens."""
        prompt = "Recomendaciones de farmacias en Los Palos Grandes"
        resp = "Farmatodo y Locatel son las principales opciones."

        saved = temp_cache.set(prompt, resp)
        assert saved is True

        hit = temp_cache.get(prompt)
        assert hit is not None
        cached_text, tokens = hit
        assert cached_text == resp
        assert tokens > 0

    def test_volatile_queries_never_cached(self, temp_cache):
        """Invariante Zero-PII y Financiero: Consultas de saldo o pagos nunca se cachean."""
        p_saldo = "¿Cuánto saldo me queda en mi línea?"
        p_c2p = "Pagar 150 Bs por Pago Móvil C2P token 123456"

        assert temp_cache.set(p_saldo, "Saldo: 100 Bs") is False
        assert temp_cache.set(p_c2p, "Pago exitoso") is False
        assert temp_cache.get(p_saldo) is None
        assert temp_cache.get(p_c2p) is None


# =====================================================================
# 3. Pruebas de Intercepción Determinista Fast-Path (FastPathIntentInterceptor)
# =====================================================================
class TestFastPathIntentInterceptor:

    @pytest.fixture
    def interceptor(self):
        return FastPathIntentInterceptor()

    def test_balance_interception_zero_token(self, interceptor):
        """Verifica que consultas de saldo se resuelvan en 0 tokens."""
        res = interceptor.intercept("¿Cuál es mi saldo actual y megas?", "04160000001")
        assert res.can_intercept is True
        assert res.intent_detected == "SALDO_CUPO"
        assert res.tokens_consumed == 0
        assert "Movilnet 4GMAX" in res.response_text
        assert res.latency_ms < 50.0

    def test_plans_catalog_interception(self, interceptor):
        """Verifica la intercepción de catálogo de planes comerciales."""
        res = interceptor.intercept("Quiero ver los planes disponibles", "04160000001")
        assert res.can_intercept is True
        assert res.intent_detected == "CATALOGO_PLANES"
        assert res.tokens_consumed == 0
        assert "Catálogo de Planes" in res.response_text

    def test_portability_promo_interception(self, interceptor):
        """Verifica oferta comercial de portabilidad para abonados de la competencia."""
        res = interceptor.intercept("Cómo me paso a Movilnet con mi mismo número", "04142554590")
        assert res.can_intercept is True
        assert res.intent_detected == "OFERTA_PORTABILIDAD"
        assert "Portabilidad Numérica" in res.response_text

    def test_open_ended_conversation_passes_to_ai_agent(self, interceptor):
        """Verifica que consultas libres o complejas pasen al AI Agent de Gemini."""
        interceptor.reset_prospect_trial("04142554590")
        res = interceptor.intercept("Dame una receta de cocina para dos personas esta noche", "04142554590")
        assert res.can_intercept is False
        assert res.intent_detected == "CONVERSACION_LIBRE"
        assert res.response_text == ""

    def test_propaganda_guard_interception_13585(self, interceptor):
        """Verifica que invitaciones o difusiones (#13585 Caracas Tech Meetup) se intercepten sin emitir saldo ni megas."""
        meetup_msg = (
            "Este 15 de octubre volvemos con una nueva edición del Caracas Tech Meetup 🥂. "
            "Regístrate en https://luma.com/snugy0r7 • Evento con cupos limitados."
        )
        assert FastPathIntentInterceptor.detect_propaganda_or_invitation(meetup_msg) is True
        res = interceptor.intercept(meetup_msg, "04142554590")
        assert res.can_intercept is True
        assert res.intent_detected == "NON_SOLICITED_PROPAGANDA_GUARD"
        assert res.tokens_consumed == 0
        assert "Saldo Disponible" not in res.response_text
        assert "10.0 GB disponibles" not in res.response_text

    def test_pwa_links_and_prospect_trial_limits_sqlite(self, interceptor):
        """Verifica enlaces PWA dinámicos (0416/0426 vs 0412/0414/0424) y bloqueo a la 4ta consulta mensual en SQLite."""
        r_mov = interceptor.intercept("saldo", "04160000001")
        assert "/ui/pwa_stitch/index.html?carrier=movilnet" in r_mov.response_text

        r_comp = interceptor.intercept("portabilidad", "04123456789")
        assert "/ui/pwa_stitch/index.html?carrier=DIGITEL" in r_comp.response_text
        assert "Portabilidad Express en este Chat" in r_comp.response_text

        prospect_phone = "04249991122"
        interceptor.reset_prospect_trial(prospect_phone)
        assert interceptor.intercept("Consulta abierta 1", prospect_phone).can_intercept is False
        assert interceptor.intercept("Consulta abierta 2", prospect_phone).can_intercept is False
        assert interceptor.intercept("Consulta abierta 3", prospect_phone).can_intercept is False
        r_blocked = interceptor.intercept("Consulta abierta 4", prospect_phone)
        assert r_blocked.can_intercept is True
        assert r_blocked.intent_detected == "PROSPECT_TRIAL_LIMIT_REACHED"
        assert "/ui/pwa_stitch/index.html?carrier=MOVISTAR" in r_blocked.response_text
        assert "Portabilidad Express en este Chat" in r_blocked.response_text
        interceptor.reset_prospect_trial(prospect_phone)


# =====================================================================
# 4. Pruebas de Filtro de Ruido de Webhook (WebhookNoiseFilter)
# =====================================================================
class TestWebhookNoiseFilter:

    def test_drop_presence_events(self):
        """Verifica que presence.update se descarte de inmediato sin crear ejecuciones."""
        payload = {"event": "presence.update", "data": {"id": "188364414275735@lid"}}
        res = WebhookNoiseFilter.evaluate(payload)
        assert res.should_process is False
        assert res.verdict == FilterVerdict.DROP_PRESENCE_UPDATE

    def test_drop_contacts_events(self):
        """Verifica que contacts.update se descarte de inmediato."""
        payload = {"event": "contacts.update", "data": [{"remoteJid": "123@lid"}]}
        res = WebhookNoiseFilter.evaluate(payload)
        assert res.should_process is False
        assert res.verdict == FilterVerdict.DROP_CONTACTS_UPDATE

    def test_drop_outgoing_bot_echo(self):
        """Verifica que fromMe=True se descarte para erradicar bucles de ping-pong."""
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "584142554590@s.whatsapp.net", "fromMe": True},
                "message": {"conversation": "Mensaje enviado por el bot"}
            }
        }
        res = WebhookNoiseFilter.evaluate(payload)
        assert res.should_process is False
        assert res.verdict == FilterVerdict.DROP_FROM_ME_ECHO

    def test_pass_valid_incoming_subscriber_message(self):
        """Verifica que mensajes válidos de clientes sean aprobados."""
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "584142650088@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Hola, buenas tardes"}
            }
        }
        res = WebhookNoiseFilter.evaluate(payload)
        assert res.should_process is True
        assert res.verdict == FilterVerdict.PASS_MESSAGE
        assert res.extracted_text == "Hola, buenas tardes"

    def test_drop_whatsapp_security_notice_13368(self):
        """Verifica que avisos del sistema de cifrado de WhatsApp (#13368) se descarten con DROP_SYSTEM_SECURITY_NOTICE."""
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "584142554590@s.whatsapp.net", "fromMe": False},
                "message": {
                    "conversation": (
                        'Información sobre "Esperando el mensaje. Esto puede tomar tiempo."\n'
                        "WhatsApp protege tus llamadas y mensajes personales con cifrado de extremo a extremo."
                    )
                }
            }
        }
        res = WebhookNoiseFilter.evaluate(payload)
        assert res.should_process is False
        assert res.verdict == FilterVerdict.DROP_SYSTEM_SECURITY_NOTICE


# =====================================================================
# 5. Pruebas de Integración REST en MovilnetAPIService
# =====================================================================
class TestServiceEndpointsIntegration:

    @pytest.fixture
    def service(self):
        return MovilnetAPIService()

    def test_get_cache_stats_endpoint(self, service):
        """Verifica GET /api/v1/cache/stats."""
        status, headers, body = service.dispatch(
            method="GET",
            path="/api/v1/cache/stats",
            headers={},
            body_bytes=b""
        )
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "total_entries" in data
        assert "total_tokens_saved" in data

    def test_post_fastpath_evaluate_handled(self, service):
        """Verifica POST /api/v1/fastpath/evaluate para consulta determinista."""
        req_body = json.dumps({"message": "cuál es mi saldo", "phone": "04160000001"}).encode("utf-8")
        status, headers, body = service.dispatch(
            method="POST",
            path="/api/v1/fastpath/evaluate",
            headers={"Content-Type": "application/json"},
            body_bytes=req_body
        )
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["handled"] is True
        assert data["source"] == "FAST_PATH_TELCO"
        assert data["tokens_saved"] > 0

    def test_post_fastpath_evaluate_delegated(self, service):
        """Verifica POST /api/v1/fastpath/evaluate para consulta libre."""
        req_body = json.dumps({"message": "explícame la física cuántica", "phone": "04160000001"}).encode("utf-8")
        status, headers, body = service.dispatch(
            method="POST",
            path="/api/v1/fastpath/evaluate",
            headers={"Content-Type": "application/json"},
            body_bytes=req_body
        )
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["handled"] is False
        assert data["source"] == "DELEGATE_TO_COGNITIVE_AI"

    def test_post_session_isolate_endpoint(self, service):
        """Verifica POST /api/v1/session/isolate."""
        req_body = json.dumps({
            "remote_jid": "584142554590@s.whatsapp.net",
            "push_name": "Ids"
        }).encode("utf-8")
        status, headers, body = service.dispatch(
            method="POST",
            path="/api/v1/session/isolate",
            headers={"Content-Type": "application/json"},
            body_bytes=req_body
        )
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["canonical_session_key"] == "SESSION:E164:584142554590"
        assert data["operator"] == "MOVISTAR"


if __name__ == "__main__":
    import tempfile
    import shutil
    print("🧪 Ejecutando suite test_immediate_action_plan...")
    
    # 1. TestSessionIdentityIsolator
    t1 = TestSessionIdentityIsolator()
    t1.test_cross_contamination_prevention_same_pushname()
    t1.test_phone_sanitization_and_e164_formatting()
    t1.test_carrier_prefix_detection()
    print("  ✅ TestSessionIdentityIsolator: PASS")
    
    # 2. TestSemanticResponseCache
    td = tempfile.mkdtemp()
    try:
        t2 = TestSemanticResponseCache()
        c = t2.temp_cache(Path(td))
        t2.test_normalization_and_sha256_key_consistency(c)
        t2.test_cache_hit_and_token_saving(c)
        t2.test_volatile_queries_never_cached(c)
        print("  ✅ TestSemanticResponseCache: PASS")
    finally:
        shutil.rmtree(td, ignore_errors=True)
        
    # 3. TestFastPathIntentInterceptor
    t3 = TestFastPathIntentInterceptor()
    inter = t3.interceptor()
    t3.test_balance_interception_zero_token(inter)
    t3.test_plans_catalog_interception(inter)
    t3.test_portability_promo_interception(inter)
    t3.test_open_ended_conversation_passes_to_ai_agent(inter)
    t3.test_propaganda_guard_interception_13585(inter)
    t3.test_pwa_links_and_prospect_trial_limits_sqlite(inter)
    print("  ✅ TestFastPathIntentInterceptor: PASS")
    
    # 4. TestWebhookNoiseFilter
    t4 = TestWebhookNoiseFilter()
    t4.test_drop_presence_events()
    t4.test_drop_contacts_events()
    t4.test_drop_outgoing_bot_echo()
    t4.test_pass_valid_incoming_subscriber_message()
    t4.test_drop_whatsapp_security_notice_13368()
    print("  ✅ TestWebhookNoiseFilter: PASS")
    
    # 5. TestServiceEndpointsIntegration
    t5 = TestServiceEndpointsIntegration()
    srv = t5.service()
    t5.test_get_cache_stats_endpoint(srv)
    t5.test_post_fastpath_evaluate_handled(srv)
    t5.test_post_fastpath_evaluate_delegated(srv)
    t5.test_post_session_isolate_endpoint(srv)
    print("  ✅ TestServiceEndpointsIntegration: PASS")
    
    print("🎉 [100% PASS] Todas las pruebas del Plan de Acción Inmediato aprobadas exitosamente.")

