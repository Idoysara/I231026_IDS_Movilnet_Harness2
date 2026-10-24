#!/usr/bin/env python3
"""
interactive_cli.py — Consola Interactiva para Pruebas Reales con Gemini y Movilnet
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Cargar .env
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from api.agents.agent_customer_care import CustomerCareAgent, AgentMessage
from api.agents.agent_fintech_c2p import FintechC2PAgent, C2PPaymentRequest
from api.agents.agent_emergency_eir import EmergencyEIRAgent, EmergencyEIRRequest, EIRLockType

def main():
    agent_care = CustomerCareAgent()
    agent_fintech = FintechC2PAgent()
    agent_eir = EmergencyEIRAgent()

    print("\033[1;36m" + "="*70)
    print("📡 CONSOLA DE PRUEBAS REALES — MOVILNET 4GMAX (NIVEL 5 SWARM)")
    print(f"🤖 Motor IA: {agent_care.reasoning_engine.model_name}")
    print("="*70 + "\033[0m")
    print("Comandos especiales:")
    print("  :c2p      -> Ejecuta una prueba real de recarga C2P")
    print("  :eir      -> Simula reporte de robo y bloqueo de terminal")
    print("  :salir    -> Finalizar la sesión interactiva\n")

    phone = "04160000001"

    while True:
        try:
            query = input(f"\033[1;32m[Abonado {phone}] >> \033[0m").strip()
            if not query:
                continue
            if query.lower() in [":salir", "salir", "exit", "quit"]:
                print("\n👋 Sesión finalizada.")
                break

            if query.lower() == ":c2p":
                print("\n💳 Procesando recarga C2P de prueba...")
                req = C2PPaymentRequest(
                    msisdn=phone,
                    amount_ves=100.0,
                    bank_code="0102",
                    payer_cid="V-10000001",
                    otp_token="123456"
                )
                res = agent_fintech.process_payment(req)
                print(f"Resultado: {res.status.value} en {res.latency_ms:.2f} ms")
                print(res.receipt_text)
                print()
                continue

            if query.lower() == ":eir":
                print("\n🚨 Ejecutando verificación y bloqueo EIR...")
                req = EmergencyEIRRequest(
                    msisdn=phone,
                    imei="358482091234565",
                    reason="Prueba interactiva de bloqueo de terminal",
                    cid="V-10000001"
                )
                res = agent_eir.process_emergency_lock(req)
                print(f"Estatus: {res.status.value} en {res.latency_ms:.2f} ms")
                print(res.security_notice)
                from db.repository import MovilnetRepository
                MovilnetRepository().update_line_status(phone, "ACTIVO")
                print()
                continue

            msg = AgentMessage(text=query, msisdn=phone, latitude=10.4920, longitude=-66.8820)
            resp = agent_care.process_message(msg)

            print(f"\n\033[1;34m[Movilnet IA — {resp.execution_mode.value} | {resp.latency_ms:.1f}ms | Tokens: {resp.tokens_consumed}]\033[0m")
            print(resp.response_text)
            if resp.interactive_options:
                opts = " | ".join([f"[{b['title']}]" for b in resp.interactive_options])
                print(f"\033[33mOpciones: {opts}\033[0m")
            print()

        except KeyboardInterrupt:
            print("\n👋 Sesión interrumpida.")
            break
        except Exception as e:
            print(f"\n\033[1;31mError: {e}\033[0m\n")

if __name__ == "__main__":
    main()
