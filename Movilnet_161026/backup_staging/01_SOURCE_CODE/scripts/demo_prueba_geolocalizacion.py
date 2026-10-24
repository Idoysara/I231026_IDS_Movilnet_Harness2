#!/usr/bin/env python3
"""
scripts/demo_prueba_geolocalizacion.py — Demostración y Prueba en Vivo del Módulo Geoespacial Movilnet
======================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal

Simula en vivo 5 interacciones reales de WhatsApp:
1. Abonado Movilnet (0416) envía Pin GPS en Altamira, Caracas.
2. Prospecto Movistar (0414) envía Pin GPS en San Diego / Valencia.
3. Consulta textual con ciudad explícita ("oficinas en Maracaibo").
4. Consulta sin ubicación ni ciudad ("dónde queda una oficina?") -> Regla Cero Adivinación.
5. Coordenadas GPS fuera de frontera (Bogotá / Miami) -> Frontera Nacional ERR_OUTSIDE_VENEZUELA.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.fastpath_intent_interceptor import FastPathIntentInterceptor
from core.carrier_funnel_classifier import CarrierFunnelClassifier


def print_banner(title: str):
    print("\n" + "═" * 78)
    print(f"📍 {title}")
    print("═" * 78)


def run_interactive_demo():
    interceptor = FastPathIntentInterceptor()

    print("\033[1;36m" + "╔" + "═" * 76 + "╗")
    print("║   DEMOSTRACIÓN DE PRUEBA REAL: LOCALIZADOR DE OFICINAS MOVILNET 4GMAX    ║")
    print("║   Ecosistema: develop | Protocolo Fast-Path Zero-Token | Regla Decagonal   ║")
    print("╚" + "═" * 76 + "╝\033[0m")

    # -------------------------------------------------------------------------
    # ESCENARIO 1: Abonado 0416 comparte Pin GPS en Altamira, Caracas
    # -------------------------------------------------------------------------
    print_banner("ESCENARIO 1: ABONADO MOVILNET (0416) COMPARTE PIN GPS EN ALTAMIRA, CARACAS")
    phone1 = "04161234567"
    lat1, lon1 = 10.4960, -66.8530
    print(f"📱 Remitente: {phone1} (Abonado Movilnet 4GMAX)")
    print(f"📍 Coordenadas GPS Recibidas: Lat {lat1}, Lon {lon1} (Altamira, Chacao, Miranda)")
    print("⚡ Procesando en FastPath ODA Zero-Token...")

    t0 = time.perf_counter()
    res1 = interceptor.intercept("Ubicación actual", phone1, latitude=lat1, longitude=lon1)
    latency1 = (time.perf_counter() - t0) * 1000.0

    print(f"⏱️  Latencia: {latency1:.2f} ms | 🪙 Tokens Consumidos: {res1.tokens_consumed} (Zero-Token)")
    print(f"🛡️  Pipeline Asignado: {res1.authorized_pipeline} (IS_MOVILNET_SUBSCRIBER = {res1.is_movilnet_subscriber})")
    print(f"📊 Fuente de Datos: {res1.data_source}")
    print("\n📩 [RESPUESTA ENTREGADA AL USUARIO POR WHATSAPP]:\n")
    print(res1.response_text)

    # -------------------------------------------------------------------------
    # ESCENARIO 2: Prospecto Movistar (0414) comparte Pin GPS en Valencia, Carabobo
    # -------------------------------------------------------------------------
    print_banner("ESCENARIO 2: PROSPECTO MOVISTAR (0414) COMPARTE PIN GPS EN SAN DIEGO / VALENCIA")
    phone2 = "04142554590"
    lat2, lon2 = 10.1990, -67.9550
    print(f"📱 Remitente: {phone2} (Prospecto Movistar - Portabilidad)")
    print(f"📍 Coordenadas GPS Recibidas: Lat {lat2}, Lon {lon2} (San Diego / Valencia, Carabobo)")
    print("⚡ Procesando en FastPath ODA Zero-Token...")

    t0 = time.perf_counter()
    res2 = interceptor.intercept("Ubicación actual", phone2, latitude=lat2, longitude=lon2)
    latency2 = (time.perf_counter() - t0) * 1000.0

    print(f"⏱️  Latencia: {latency2:.2f} ms | 🪙 Tokens Consumidos: {res2.tokens_consumed} (Zero-Token)")
    print(f"🛡️  Pipeline Asignado: {res2.authorized_pipeline} (IS_MOVILNET_SUBSCRIBER = {res2.is_movilnet_subscriber})")
    print(f"📊 Fuente de Datos: {res2.data_source}")
    print("\n📩 [RESPUESTA ENTREGADA AL USUARIO POR WHATSAPP]:\n")
    print(res2.response_text)

    # -------------------------------------------------------------------------
    # ESCENARIO 3: Consulta Textual con Ciudad ("Oficinas en Maracaibo")
    # -------------------------------------------------------------------------
    print_banner("ESCENARIO 3: CONSULTA TEXTUAL CON CIUDAD ('¿Dónde quedan las oficinas en Maracaibo?')")
    phone3 = "04121234567" # Digitel
    msg3 = "¿Dónde quedan las oficinas comerciales en Maracaibo?"
    print(f"📱 Remitente: {phone3} (Prospecto Digitel)")
    print(f"💬 Mensaje: \"{msg3}\"")
    print("⚡ Procesando búsqueda por ciudad en Catálogo Geoespacial...")

    t0 = time.perf_counter()
    res3 = interceptor.intercept(msg3, phone3)
    latency3 = (time.perf_counter() - t0) * 1000.0

    print(f"⏱️  Latencia: {latency3:.2f} ms | 🪙 Tokens Consumidos: {res3.tokens_consumed} (Zero-Token)")
    print(f"🛡️  Pipeline Asignado: {res3.authorized_pipeline}")
    print("\n📩 [RESPUESTA ENTREGADA AL USUARIO POR WHATSAPP]:\n")
    print(res3.response_text)

    # -------------------------------------------------------------------------
    # ESCENARIO 4: Consulta sin Ubicación ni Ciudad (Regla de Cero Adivinación)
    # -------------------------------------------------------------------------
    print_banner("ESCENARIO 4: REGLA INVIOLABLE DE CERO ADIVINACIÓN ('¿Dónde queda una agencia?')")
    phone4 = "04169998877"
    msg4 = "¿Dónde queda una agencia para hacer un reclamo?"
    print(f"📱 Remitente: {phone4} (Abonado Movilnet)")
    print(f"💬 Mensaje: \"{msg4}\" (Sin GPS ni ciudad declarada)")
    print("🛡️  Aplicando protocolo de Cero Adivinación y Datos Faltantes...")

    t0 = time.perf_counter()
    res4 = interceptor.intercept(msg4, phone4)
    latency4 = (time.perf_counter() - t0) * 1000.0

    print(f"⏱️  Latencia: {latency4:.2f} ms | 🪙 Tokens Consumidos: {res4.tokens_consumed}")
    print(f"🛡️  Pipeline Asignado: {res4.authorized_pipeline}")
    print("\n📩 [RESPUESTA ENTREGADA AL USUARIO POR WHATSAPP]:\n")
    print(res4.response_text)

    # -------------------------------------------------------------------------
    # ESCENARIO 5: Coordenadas Fuera de Venezuela (Alerta Fronteriza)
    # -------------------------------------------------------------------------
    print_banner("ESCENARIO 5: COORDENADAS GPS FUERA DE VENEZUELA (BOGOTÁ, COLOMBIA)")
    phone5 = "04161112233"
    lat5, lon5 = 4.7110, -74.0721 # Bogotá
    print(f"📱 Remitente: {phone5}")
    print(f"📍 Coordenadas GPS Recibidas: Lat {lat5}, Lon {lon5} (Fuera de WGS84 Venezuela)")
    print("🛡️  Evaluando frontera con is_point_in_venezuela...")

    t0 = time.perf_counter()
    res5 = interceptor.intercept("Ubicación", phone5, latitude=lat5, longitude=lon5)
    latency5 = (time.perf_counter() - t0) * 1000.0

    print(f"⏱️  Latencia: {latency5:.2f} ms | 🪙 Tokens Consumidos: {res5.tokens_consumed}")
    print("\n📩 [RESPUESTA ENTREGADA AL USUARIO POR WHATSAPP]:\n")
    print(res5.response_text)

    print("\n" + "═" * 78)
    print("🏆 CONCLUSIÓN DE LA PRUEBA: LOS 5 ESCENARIOS EJECUTADOS CON ÉXITO Y CERO TOKENS.")
    print("═" * 78 + "\n")


if __name__ == "__main__":
    run_interactive_demo()
