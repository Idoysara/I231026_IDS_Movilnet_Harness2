#!/usr/bin/env python3
"""
core/webhook_noise_filter.py — Guardián de Frontera y Filtro de Ruido para Webhooks
===================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal

Problema que Resuelve (Hallazgo Forense):
Durante la auditoría de ejecuciones en n8n Cloud se detectó que Evolution API envía eventos
secundarios masivos al webhook central:
  - 'presence.update': Se disparó 6 veces en 10 segundos (#13099 a #13104).
  - 'contacts.update': Disparado en cada interacción (#13096).
  - 'send.message': Eco emitido por Baileys al responder el bot (#13098).
Aunque el nodo Switch los frena antes de Gemini, saturan la cola de trabajo de n8n con cientos de
ejecuciones inútiles por hora.

Solución de Ingeniería:
1. Filtro estricto en la frontera (Edge Filter) que evalúa el payload crudo en <1ms.
2. Descarta inmediatamente ecos del bot (fromMe == True).
3. Descarta eventos que no contienen contenido conversacional (presence, contacts, chats).
4. Aprueba únicamente mensajes auténticos con texto, audio, imagen o documentos.
5. CLI autónomo con auto-verificación formal (--test, --demo).
"""

from __future__ import annotations

import re
import sys
import argparse
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class FilterVerdict(str, Enum):
    PASS_MESSAGE = "PASS_MESSAGE"
    DROP_FROM_ME_ECHO = "DROP_FROM_ME_ECHO"
    DROP_PRESENCE_UPDATE = "DROP_PRESENCE_UPDATE"
    DROP_CONTACTS_UPDATE = "DROP_CONTACTS_UPDATE"
    DROP_CHATS_UPDATE = "DROP_CHATS_UPDATE"
    DROP_EMPTY_CONTENT = "DROP_EMPTY_CONTENT"
    DROP_UNKNOWN_EVENT = "DROP_UNKNOWN_EVENT"
    DROP_SYSTEM_SECURITY_NOTICE = "DROP_SYSTEM_SECURITY_NOTICE"
    DROP_SPAM_INVITATION = "DROP_SPAM_INVITATION"
    DROP_COMMERCIAL_AUTOREPLY = "DROP_COMMERCIAL_AUTOREPLY"
    DROP_PROHIBITED_SENDER = "DROP_PROHIBITED_SENDER"


@dataclass
class FilterResult:
    should_process: bool
    verdict: FilterVerdict
    reason: str
    event_type: str
    sender_jid: Optional[str] = None
    extracted_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WebhookNoiseFilter:
    """Filtro de Ruido de Alta Velocidad para Webhooks de WhatsApp / Baileys."""

    ALLOWED_EVENTS = {"messages.upsert", "messages.update"}

    SYSTEM_SECURITY_NOTICE_REGEX = re.compile(
        r"(mensajes y llamadas est[aá]n cifrados|"
        r"llamadas y mensajes est[aá]n cifrados|"
        r"llamadas y mensajes personales con cifrado|"
        r"esperando el mensaje\.?\s*esto puede tomar tiempo|"
        r"c[oó]digo de seguridad cambi[oó]|"
        r"cifrado de extremo a extremo|"
        r"end-to-end encrypted)",
        re.IGNORECASE,
    )

    SPAM_INVITATION_REGEX = re.compile(
        r"\b(meetup|conferencia|entrada libre|te invitamos a|registro en luma|luma\.com|"
        r"patrocinado por|comunidad tech|hackathon|taller gratuito|after office|startup pitches)\b",
        re.IGNORECASE,
    )

    COMMERCIAL_AUTOREPLY_REGEX = re.compile(
        r"("
        r"gracias por comunicarte|"
        r"gracias por escribirnos|"
        r"gracias por contactar(nos)?|"
        r"en breve (te )?atenderemos|"
        r"un asesor te atender[aá]|"
        r"horario de atenci[oó]n|"
        r"bienvenido a nuestro canal|"
        r"mensaje autom[aá]tico|"
        r"auto-?respuesta|"
        r"automated message|"
        r"te responderemos lo antes posible"
        r")",
        re.IGNORECASE,
    )

    @classmethod
    def is_system_security_notice(cls, text: str) -> bool:
        """Evalúa si el texto corresponde a una notificación técnica de cifrado o seguridad de WhatsApp."""
        if not text:
            return False
        return bool(cls.SYSTEM_SECURITY_NOTICE_REGEX.search(text))

    @classmethod
    def is_spam_invitation(cls, text: str) -> bool:
        """Evalúa si el texto corresponde a una difusión o convocatoria externa no solicitada."""
        if not text:
            return False
        return bool(cls.SPAM_INVITATION_REGEX.search(text))

    @classmethod
    def is_commercial_autoreply(cls, text: str) -> bool:
        """Evalúa si el texto corresponde a un auto-respondedor comercial o mensaje corporativo automático."""
        if not text:
            return False
        return bool(cls.COMMERCIAL_AUTOREPLY_REGEX.search(text))

    PROHIBITED_NUMBERS = {
        "4166251587",
        "584166251587",
        "04166251587",
        "00584166251587",
    }

    @classmethod
    def is_prohibited_sender(cls, sender: Optional[str]) -> bool:
        """Determina si el remitente corresponde al número prohibido/decommissioned (0416-6251587)."""
        if not sender:
            return False
        digits = re.sub(r"\D", "", str(sender))
        return any(digits.endswith(p) or digits == p for p in cls.PROHIBITED_NUMBERS)

    @classmethod
    def evaluate(cls, raw_payload: Dict[str, Any], check_spam_invitation: bool = False) -> FilterResult:
        """
        Evalúa de forma determinista el payload recibido del webhook.
        Retorna FilterResult indicando si debe procesarse o descartarse en el borde.
        """
        if not isinstance(raw_payload, dict):
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_EMPTY_CONTENT,
                reason="Payload no es un diccionario JSON válido",
                event_type="INVALID"
            )

        # 1. Inspección del evento principal
        event = raw_payload.get("event", "")
        data = raw_payload.get("data", {})

        # Si el evento no está en los permitidos
        if event == "presence.update":
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_PRESENCE_UPDATE,
                reason="Evento de presencia (online/typing) no contiene mensajes",
                event_type=event
            )
        elif event == "contacts.update":
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_CONTACTS_UPDATE,
                reason="Evento de sincronización de contactos no contiene mensajes",
                event_type=event
            )
        elif event == "chats.update":
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_CHATS_UPDATE,
                reason="Evento de actualización de chat no contiene mensajes",
                event_type=event
            )
        elif event and event not in cls.ALLOWED_EVENTS and event != "send.message":
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_UNKNOWN_EVENT,
                reason=f"Evento '{event}' no admitido en el pipeline conversacional",
                event_type=event
            )

        # 2. Manejo de 'data' (puede ser lista o dict)
        message_data = data[0] if isinstance(data, list) and len(data) > 0 else data
        if not isinstance(message_data, dict):
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_EMPTY_CONTENT,
                reason="Objeto data vacío o malformado",
                event_type=event or "UNKNOWN"
            )

        key = message_data.get("key", {})
        # 3. Detección y descarte de eco propio (fromMe == True)
        from_me = key.get("fromMe", False) or raw_payload.get("fromMe", False)
        if from_me is True:
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_FROM_ME_ECHO,
                reason="Mensaje saliente generado por el bot (fromMe=True), descartado para evitar bucles",
                event_type=event or "send.message",
                sender_jid=key.get("remoteJid")
            )

        # 4. Extracción de contenido conversacional
        message = message_data.get("message", {})
        sender_jid = key.get("remoteJid") or raw_payload.get("sender") or message_data.get("from")

        # 4.1. Descarte tajante de número legacy prohibido (0416-6251587) - Regla Inviolable Capítulo 164
        if cls.is_prohibited_sender(sender_jid) or "4166251587" in str(raw_payload):
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_PROHIBITED_SENDER,
                reason="Número de línea legacy prohibido (0416-6251587) bloqueado en la frontera (Capítulo 164)",
                event_type=event or "PROHIBITED_SENDER",
                sender_jid=sender_jid
            )

        text = (
            message.get("conversation")
            or message.get("extendedTextMessage", {}).get("text")
            or message.get("imageMessage", {}).get("caption")
            or message.get("videoMessage", {}).get("caption")
            or ""
        )

        has_media = bool(
            message.get("audioMessage")
            or message.get("imageMessage")
            or message.get("videoMessage")
            or message.get("documentMessage")
        )

        if not text and not has_media:
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_EMPTY_CONTENT,
                reason="Payload no contiene texto ni archivos multimedia procesables",
                event_type=event or "EMPTY",
                sender_jid=sender_jid
            )

        # 5. Inspección semántica temprana: Avisos de seguridad/cifrado de WhatsApp (Traza #13368)
        if text and cls.is_system_security_notice(text):
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_SYSTEM_SECURITY_NOTICE,
                reason="Aviso automático del sistema de seguridad/cifrado de WhatsApp descartado en la frontera",
                event_type=event or "messages.upsert",
                sender_jid=sender_jid,
                extracted_text=text
            )

        # 6. Descarte de difusiones masivas o convocatorias no solicitadas en frontera si procede
        is_broadcast_jid = bool(sender_jid and (str(sender_jid).endswith("@broadcast") or str(sender_jid).endswith("@newsletter")))
        if text and (check_spam_invitation or is_broadcast_jid) and cls.is_spam_invitation(text):
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_SPAM_INVITATION,
                reason="Difusión o convocatoria no solicitada descartada en la frontera",
                event_type=event or "messages.upsert",
                sender_jid=sender_jid,
                extracted_text=text
            )

        # 7. Descarte de auto-respondedores comerciales de WhatsApp Business (Traza #13852 HiperFarma)
        if text and cls.is_commercial_autoreply(text):
            return FilterResult(
                should_process=False,
                verdict=FilterVerdict.DROP_COMMERCIAL_AUTOREPLY,
                reason="Auto-respondedor comercial o mensaje corporativo automático descartado en la frontera para proteger n8n Cloud",
                event_type=event or "messages.upsert",
                sender_jid=sender_jid,
                extracted_text=text
            )

        return FilterResult(
            should_process=True,
            verdict=FilterVerdict.PASS_MESSAGE,
            reason="Mensaje de abonado válido para procesamiento",
            event_type=event or "messages.upsert",
            sender_jid=sender_jid,
            extracted_text=text
        )


def main():
    parser = argparse.ArgumentParser(description="Filtro de Ruido de Frontera para Webhooks WhatsApp")
    parser.add_argument("--test", action="store_true", help="Ejecutar suite formal de pruebas")
    parser.add_argument("--demo", action="store_true", help="Demostración con eventos reales")
    args = parser.parse_args()

    if args.test:
        print("🧪 [TEST] Verificando WebhookNoiseFilter (Pilares I al VII)...")
        # Test 1: Descarte de presence.update
        p_presence = {"event": "presence.update", "data": {"id": "123@lid"}}
        r1 = WebhookNoiseFilter.evaluate(p_presence)
        assert r1.should_process is False
        assert r1.verdict == FilterVerdict.DROP_PRESENCE_UPDATE

        # Test 2: Descarte de contacts.update
        p_contacts = {"event": "contacts.update", "data": [{"remoteJid": "123@lid"}]}
        r2 = WebhookNoiseFilter.evaluate(p_contacts)
        assert r2.should_process is False
        assert r2.verdict == FilterVerdict.DROP_CONTACTS_UPDATE

        # Test 3: Descarte de eco saliente (fromMe == True)
        p_echo = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "584142554590@s.whatsapp.net", "fromMe": True},
                "message": {"conversation": "Respuesta enviada por el bot"}
            }
        }
        r3 = WebhookNoiseFilter.evaluate(p_echo)
        assert r3.should_process is False
        assert r3.verdict == FilterVerdict.DROP_FROM_ME_ECHO

        # Test 4: Pase de mensaje auténtico de cliente
        p_valid = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "584142554590@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Hola, cuál es mi saldo?"}
            }
        }
        r4 = WebhookNoiseFilter.evaluate(p_valid)
        assert r4.should_process is True
        assert r4.verdict == FilterVerdict.PASS_MESSAGE
        assert r4.extracted_text == "Hola, cuál es mi saldo?"

        # Test 5: Descarte de aviso del sistema de WhatsApp (Traza #13368)
        p_trace_13368 = {
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
        r5 = WebhookNoiseFilter.evaluate(p_trace_13368)
        assert r5.should_process is False, "ERROR: La traza #13368 debió descartarse como aviso de sistema!"
        assert r5.verdict == FilterVerdict.DROP_SYSTEM_SECURITY_NOTICE

        p_e2e_notice = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "584142554590@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Los mensajes y llamadas están cifrados de extremo a extremo. Código de seguridad cambió."}
            }
        }
        r6 = WebhookNoiseFilter.evaluate(p_e2e_notice)
        assert r6.should_process is False
        assert r6.verdict == FilterVerdict.DROP_SYSTEM_SECURITY_NOTICE

        # Test 6: Descarte de difusión no solicitada en lista broadcast (DROP_SPAM_INVITATION)
        p_spam_bcast = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "status@broadcast", "fromMe": False},
                "message": {"conversation": "Te invitamos a nuestra conferencia y meetup con entrada libre. Registro en luma.com"}
            }
        }
        r7 = WebhookNoiseFilter.evaluate(p_spam_bcast)
        assert r7.should_process is False
        assert r7.verdict == FilterVerdict.DROP_SPAM_INVITATION

        # Test 7: Descarte de auto-respondedor comercial WhatsApp Business (Traza #13852 HiperFarma)
        p_commercial = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "584121234567@s.whatsapp.net", "fromMe": False},
                "message": {
                    "conversation": "Gracias por comunicarte con hiperfarmagranfamilia. ¿Cómo podemos ayudarte? En breve  atenderemos su solicitud 😉"
                }
            }
        }
        r8 = WebhookNoiseFilter.evaluate(p_commercial)
        assert r8.should_process is False, "ERROR: El auto-respondedor comercial debió descartarse en frontera!"
        # Test 9: Descarte de número prohibido legacy (0416-6251587 / 584166251587)
        p_prohibited = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "584166251587@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Hoka"}
            }
        }
        r9 = WebhookNoiseFilter.evaluate(p_prohibited)
        assert r9.should_process is False, "ERROR: El número prohibido 0416-6251587 debió descartarse en frontera!"
        assert r9.verdict == FilterVerdict.DROP_PROHIBITED_SENDER

        print("✅ [TEST PASS] Todos los invariantes de WebhookNoiseFilter (incluyendo #13368, #13852 y 0416-6251587) aprobados con 100% de éxito.")
        return

    if args.demo:
        sample_presence = {"event": "presence.update", "data": {"id": "188364414275735@lid"}}
        sample_notice = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "584160000002@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Los mensajes y llamadas están cifrados de extremo a extremo."}
            }
        }
        sample_msg = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "584160000001@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Buenas tardes, quiero recargar mi saldo"}
            }
        }
        res_p = WebhookNoiseFilter.evaluate(sample_presence)
        res_n = WebhookNoiseFilter.evaluate(sample_notice)
        res_m = WebhookNoiseFilter.evaluate(sample_msg)
        print("\n🔬 Demostración de Filtrado de Frontera:")
        print(f"   Evento 1 (presence.update):      ¿Procesar?: {res_p.should_process} | Veredicto: {res_p.verdict.value}")
        print(f"   Evento 2 (Aviso Cifrado #13368): ¿Procesar?: {res_n.should_process} | Veredicto: {res_n.verdict.value}")
        print(f"   Evento 3 (Mensaje de texto):     ¿Procesar?: {res_m.should_process}  | Veredicto: {res_m.verdict.value} | Texto: '{res_m.extracted_text}'\n")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
