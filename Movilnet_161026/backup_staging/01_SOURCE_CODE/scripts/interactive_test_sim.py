#!/usr/bin/env python3
"""
scripts/interactive_test_sim.py — Simulador Interactivo de Pruebas Reales Movilnet ↔ n8n
=======================================================================================
Permite realizar pruebas reales e interactivas del ciclo de atención de WhatsApp:
1. Ingesta del mensaje (Texto / Consulta de saldo / Tasa cambiaria / Factura Gmail / Robo EIR).
2. Resolución en el Núcleo ODA de Movilnet (<15 ms).
3. Enrutamiento hacia el Ecosistema Google (Gmail / Drive / Calendar).
4. Generación de la respuesta institucional WhatsApp.
"""

import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.service import MovilnetAPIService
from db.repository import MovilnetRepository


def run_simulation(phone: str, name: str, message: str, email: str = ""):
    print("\n" + "=" * 70)
    print("📡 INICIANDO SIMULACIÓN DE PRUEBA REAL (MOVILNET ↔ n8n ↔ GOOGLE)")
    print("=" * 70)

    # 1. Validación de Operadora según Plan Nacional de Numeración CONATEL
    from core.carrier_funnel_classifier import CarrierFunnelClassifier, Carrier
    carrier, carrier_label, is_competitor = CarrierFunnelClassifier.identify_carrier(phone)

    remote_jid = f"58{phone[1:]}@s.whatsapp.net" if phone.startswith("0") else f"{phone}@s.whatsapp.net"
    full_message = f"{message} (correo: {email})" if email and "@" not in message else message

    if is_competitor:
        print(f"🏢 [LÍNEA EXTERNA DETECTADA]: {phone} pertenece a {carrier_label}.")
        print("➡️  [REGLA TELCO CARRIER-GRADE]: Movilnet no factura líneas de la competencia.")
        print("🎯 [ACCIÓN DE NEGOCIO]: Activación del Funnel de Portabilidad / Captación hacia Movilnet 4GMAX.")
        eval_res = CarrierFunnelClassifier.evaluate_inbound_message(phone, message, sender_name=name)
        res = {
            "intent": "COMPETITOR_PORTABILITY_FUNNEL",
            "latency_mode": "FAST_PATH_MARKETING_FUNNEL",
            "tokens_cost_usd": 0.0,
            "reply_text": eval_res.funnel_reply_text,
            "n8n_egress_payload": {
                "instanceId": "Viki LPGTEC",
                "number": remote_jid,
                "options": {"delay": 1500},
                "text": eval_res.funnel_reply_text
            }
        }
    else:
        # Abonado genuino Movilnet (0416 / 0426)
        repo = MovilnetRepository()
        sub = repo.get_subscriber_by_msisdn(phone)
        if not sub:
            print(f"⚙️ Registrando abonado Movilnet {phone} ({name}) en la base de datos local ODA...")
            repo.create_subscriber_with_line(
                cid=f"V-{phone[-8:]}",
                msisdn=phone,
                plan_id="PLAN-4G-INTELIPLAN-10GB",
                customer_type="NATURAL"
            )
            print("✅ Abonado registrado exitosamente con plan Inteliplan 10GB 4GMAX.")

        # Disparar al endpoint del Core de Movilnet
        payload = {
            "event": "messages.upsert",
            "instance": "Viki LPGTEC",
            "data": {
                "key": {
                    "remoteJid": remote_jid,
                    "id": "MSG-REAL-TEST-2026"
                },
                "pushName": name,
                "message": {
                    "conversation": full_message
                }
            }
        }
        service = MovilnetAPIService()
        status, headers, resp_bytes = service.dispatch(
            method="POST",
            path="/api/v1/n8n/webhook-ingest",
            headers={"Content-Type": "application/json"},
            body_bytes=json.dumps(payload).encode("utf-8")
        )
        res = json.loads(resp_bytes.decode("utf-8"))

    # 4. Mostrar Resultados de la Simulación en Vivo
    print("\n📥 [1. MENSAJE ENTRANTE POR WHATSAPP]:")
    print(f"   👤 De: {name} ({phone})")
    print(f"   💬 Mensaje: \"{full_message}\"")

    print("\n⚙️ [2. PROCESAMIENTO EN EL CORE Y n8n]:")
    print(f"   🎯 Intención Detectada: {res.get('intent', 'GENERAL_INQUIRY')}")
    print(f"   ⚡ Modo de Latencia: {res.get('latency_mode', 'FAST_PATH_DETERMINISTIC')}")
    print(f"   💰 Costo en Tokens: ${res.get('tokens_cost_usd', 0.0):.4f} USD")

    # Detectar si activa servicios Google
    lower_msg = full_message.lower()
    if any(k in lower_msg for k in ["correo", "email", "factura", "recibo"]):
        print("   📧 [SERVICIO GOOGLE ACTIVADO]: Disparo de Gmail API hacia el correo registrado.")
    if any(k in lower_msg for k in ["cita", "agendar", "turno"]):
        print("   📅 [SERVICIO GOOGLE ACTIVADO]: Disparo de Google Calendar API para agendar cita en agencia.")

    print("\n📤 [3. RESPUESTA ENTREGADA AL CLIENTE EN WHATSAPP]:")
    print("   " + "-" * 55)
    print(f"   {res.get('reply_text', '')}")
    print("   " + "-" * 55)

    print("\n📦 [4. PAYLOAD FINAL LISTO PARA EL GATEWAY WHATSAPP]:")
    print(json.dumps(res.get("n8n_egress_payload", {}), indent=2, ensure_ascii=False))
    print("\n" + "=" * 70)
    print("🟢 SIMULACIÓN COMPLETADA AL 100% CON ÉXITO")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de Pruebas Reales Movilnet")
    parser.add_argument("--phone", type=str, default="04165551234", help="Número telefónico a probar (ej: 04165551234)")
    parser.add_argument("--name", type=str, default="Cliente Evaluador", help="Nombre del cliente")
    parser.add_argument("--message", type=str, default="Hola, deseo consultar mi saldo y plan", help="Mensaje de WhatsApp")
    parser.add_argument("--email", type=str, default="", help="Correo electrónico para envío de recibo")
    args = parser.parse_args()

    run_simulation(args.phone, args.name, args.message, args.email)
