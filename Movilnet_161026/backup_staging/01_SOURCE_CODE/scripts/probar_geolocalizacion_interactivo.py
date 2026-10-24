#!/usr/bin/env python3
"""
scripts/probar_geolocalizacion_interactivo.py — Simulador Interactivo de Geolocalización Movilnet 4GMAX
========================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal

Permite a los ingenieros, evaluadores y directores de Movilnet probar en ambiente de DESARROLLO (develop):
1. Extracción de coordenadas GPS físicas (WGS84).
2. Localización de las 1,017 agencias certificadas (Sede Corporativa, OSACs, Agentes Autorizados, ACIs).
3. Firewall Perimetral de Portabilidad (Movilnet 0416/0426 vs Competencia 0414/0424/0412).
4. Generación en tiempo real (<20 ms) del mensaje WhatsApp con ruta Google Maps sin consumir tokens.
"""

from __future__ import annotations

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.fastpath_intent_interceptor import FastPathIntentInterceptor
from core.carrier_funnel_classifier import CarrierFunnelClassifier
from core.n8n_webhook_payload_extractor import N8nWebhookPayloadExtractor, NormalizedInboundMessage
from core.geo_catalog import is_point_in_venezuela


# Ciudades predefinidas para pruebas rápidas
CIUDADES_PREDEFINIDAS = {
    "1": ("Caracas (Plaza Altamira, Chacao)", 10.4960, -66.8530),
    "2": ("Caracas (El Silencio / Centro)", 10.5050, -66.9150),
    "3": ("Valencia (CC Metrópolis, San Diego)", 10.1990, -67.9550),
    "4": ("Maracaibo (Bella Vista / 5 de Julio)", 10.6650, -61.6150),
    "5": ("Maracay (Av. Bolívar / Centro)", 10.2469, -67.5958),
    "6": ("Barquisimeto (CC Las Trinitarias)", 10.0710, -69.2880),
    "7": ("Puerto La Cruz (Paseo Colón)", 10.2180, -64.6360),
    "8": ("San Cristóbal (Barrio Obrero)", 7.7669, -72.2250),
    "9": ("Maturín (Centro)", 9.7450, -63.1830),
    "10": ("Fuera de Venezuela (Prueba Bogotá)", 4.7110, -74.0721),
}


def ejecutar_evaluacion(
    phone: str,
    message_text: str = "Ubicación actual",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location_name: str = ""
) -> Dict[str, Any]:
    """
    Ejecuta el ciclo de intercepción FastPath ODA simulando la llegada de un mensaje o pin GPS.
    """
    interceptor = FastPathIntentInterceptor()
    carrier, carrier_label, is_competitor = CarrierFunnelClassifier.identify_carrier(phone)

    t0 = time.perf_counter()
    res = interceptor.intercept(
        message_text=message_text,
        phone_number=phone,
        latitude=latitude,
        longitude=longitude
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "phone": phone,
        "carrier": carrier.value,
        "carrier_label": carrier_label,
        "is_movilnet_subscriber": not is_competitor,
        "authorized_pipeline": res.authorized_pipeline,
        "intent": res.intent_detected,
        "latitude": latitude,
        "longitude": longitude,
        "latency_ms": latency_ms,
        "tokens_consumed": res.tokens_consumed,
        "data_source": res.data_source,
        "response_text": res.response_text,
    }


def imprimir_resultado_prueba(data: Dict[str, Any]):
    """Imprime el resultado estructurado de la prueba."""
    print("\n" + "═" * 78)
    print("📊 RESULTADO DE LA TELEMETRÍA PRE-PRODUCCIÓN:")
    print("═" * 78)
    print(f"📱 Número Evaluado:         {data['phone']} ({data['carrier_label']})")
    print(f"🛡️  Operadora / Pipeline:    {'✅ Abonado Movilnet' if data['is_movilnet_subscriber'] else '🎯 Prospecto Competencia (Portabilidad)'} ➔ {data['authorized_pipeline']}")
    
    if data["latitude"] is not None and data["longitude"] is not None:
        en_venezuela = is_point_in_venezuela(data["latitude"], data["longitude"])
        flag_geo = "🇻🇪 En Territorio Nacional" if en_venezuela else "⚠️ Fuera de Frontera Venezolana"
        print(f"📍 Coordenadas Físicas:    Lat {data['latitude']:.5f}, Lon {data['longitude']:.5f} ({flag_geo})")
    
    print(f"⏱️  Tiempo de Respuesta:     {data['latency_ms']:.2f} ms")
    print(f"🪙 Tokens Consumidos:       {data['tokens_consumed']} tokens (100% Cero Costo / FastPath)")
    print(f"📂 Origen de Certificación:  {data['data_source']}")
    print("═" * 78)
    print("\n📩 [MENSAJE EXACTO ENTREGADO A WHATSAPP]:\n")
    print(data["response_text"])
    print("\n" + "═" * 78 + "\n")


def modo_interactivo():
    """Modo interactivo paso a paso desde terminal para el usuario con auto-recuperación y bucle continuo."""
    while True:
        print("\033[1;36m" + "╔" + "═" * 76 + "╗")
        print("║     SIMULADOR INTERACTIVO PRE-PRODUCCIÓN: GPS Y AGENCIA MOVILNET 4GMAX     ║")
        print("║     Ambiente: develop | Dataset: 1,017 Agencias | Cero-Tokens (<20 ms)     ║")
        print("╚" + "═" * 76 + "╝\033[0m")

        # 1. Solicitar teléfono
        print("\n📱 Paso 1: Ingresa el número de teléfono celular a simular:")
        print("   (Ejemplos: 04161234567, 04269876543, 04142554590, 04128887766)")
        raw_phone = input("👉 Número de teléfono [Default: 04161234567]: ").strip()
        phone = raw_phone if raw_phone else "04161234567"

        # 2. Seleccionar tipo de entrada o escribir directamente
        print("\n📍 Paso 2: ¿Qué tipo de información deseas enviar?")
        print("   1) Ingresar Coordenadas GPS Físicas Manuales (Latitud y Longitud exactas)")
        print("   2) Seleccionar una Ciudad / Zona de Venezuela predefinida")
        print("   3) Escribir un Mensaje Textual con Ciudad (ej. 'Oficinas en Barquisimeto')")
        print("   4) Mensaje sin Ubicación ni Ciudad (Prueba Regla Cero Adivinación)")
        print("   5) Inyección de Webhook Real de WhatsApp (Payload Evolution API JSON)")
        print("   💡 [Tip inteligente]: También puedes escribir directamente el nombre de una ciudad (ej. 'Caracas')")
        
        opcion = input("👉 Selecciona una opción (1-5) o escribe tu consulta [Default: 2]: ").strip()
        if not opcion:
            opcion = "2"

        # Detección inteligente si el usuario escribe directamente una ciudad o consulta textual
        if not opcion.isdigit() and any(c.isalpha() for c in opcion):
            query_text = opcion if any(w in opcion.lower() for w in ["oficina", "agencia", "donde", "sucursal"]) else f"Oficinas en {opcion}"
            print(f"\n⚡ [Auto-Detección]: Interpretando '{opcion}' como consulta de ubicación...")
            res = ejecutar_evaluacion(phone, message_text=query_text)
            imprimir_resultado_prueba(res)

        # Detección si el usuario escribe coordenadas separadas por coma (ej. 10.49, -66.85)
        elif "," in opcion and any(c.isdigit() for c in opcion):
            try:
                parts = [float(p.strip()) for p in opcion.split(",")]
                if len(parts) >= 2:
                    lat, lon = parts[0], parts[1]
                    print(f"\n⚡ [Auto-Detección]: Interpretando coordenadas Lat {lat}, Lon {lon}...")
                    res = ejecutar_evaluacion(phone, message_text="Ubicación actual", latitude=lat, longitude=lon)
                    imprimir_resultado_prueba(res)
                else:
                    print("❌ Formato de coordenadas inválido. Debe ser: latitud, longitud")
            except ValueError:
                print("❌ No se pudieron convertir los valores a números decimales.")

        elif opcion == "1":
            print("\n✏️  Ingresa las coordenadas WGS84:")
            lat_in = input("   Latitud (ej. 10.4960): ").strip()
            lon_in = input("   Longitud (ej. -66.8530): ").strip()
            try:
                lat = float(lat_in)
                lon = float(lon_in)
                res = ejecutar_evaluacion(phone, message_text="Ubicación actual", latitude=lat, longitude=lon)
                imprimir_resultado_prueba(res)
            except ValueError:
                print("❌ Error: Las coordenadas deben ser números decimales válidos.")

        elif opcion == "2":
            print("\n🏙️  Selecciona una zona de prueba:")
            for k, v in CIUDADES_PREDEFINIDAS.items():
                print(f"   {k}) {v[0]}")
            sub_opc = input("👉 Elige la ciudad (1-10) [Default: 1]: ").strip() or "1"
            if sub_opc in CIUDADES_PREDEFINIDAS:
                ciudad_nombre, lat, lon = CIUDADES_PREDEFINIDAS[sub_opc]
                print(f"\n⚡ Simulando GPS en: {ciudad_nombre}...")
                res = ejecutar_evaluacion(phone, message_text=f"Pin GPS en {ciudad_nombre}", latitude=lat, longitude=lon)
                imprimir_resultado_prueba(res)
            elif sub_opc.lower() in [v[0].lower() for v in CIUDADES_PREDEFINIDAS.values()] or any(c.isalpha() for c in sub_opc):
                # Si escribió el nombre de la ciudad
                res = ejecutar_evaluacion(phone, message_text=f"Oficinas en {sub_opc}")
                imprimir_resultado_prueba(res)
            else:
                print("❌ Opción inválida.")

        elif opcion == "3":
            print("\n✍️  Escribe tu consulta textual sobre agencias:")
            msg = input("👉 Consulta [Default: ¿Dónde quedan las oficinas en Valencia?]: ").strip()
            if not msg:
                msg = "¿Dónde quedan las oficinas en Valencia?"
            print(f"\n⚡ Procesando consulta textual: \"{msg}\"...")
            res = ejecutar_evaluacion(phone, message_text=msg)
            imprimir_resultado_prueba(res)

        elif opcion == "4":
            msg = "¿Dónde puedo ir a reclamar o comprar un chip?"
            print(f"\n⚡ Simulando consulta sin datos de ubicación: \"{msg}\"...")
            res = ejecutar_evaluacion(phone, message_text=msg)
            imprimir_resultado_prueba(res)

        elif opcion == "5":
            print("\n📦 Inyectando Payload Oficial Evolution API ('messages.upsert' con 'locationMessage'):")
            sample_evo = {
                "event": "messages.upsert",
                "instance": "Viki LPGTEC",
                "data": {
                    "key": {"remoteJid": f"58{phone[1:]}@s.whatsapp.net", "id": "3EB0TESTING_PAYLOAD"},
                    "pushName": "Evaluador Pre-Producción",
                    "message": {
                        "locationMessage": {
                            "degreesLatitude": 10.4960,
                            "degreesLongitude": -66.8530,
                            "name": "Altamira Caracas"
                        }
                    },
                    "source": "ios"
                }
            }
            norm = N8nWebhookPayloadExtractor.extract_universal(sample_evo)
            res_exec = N8nWebhookPayloadExtractor.execute_in_movilnet_core(norm)
            
            print("\n" + "═" * 78)
            print("📊 RESPUESTA DEL NÚCLEO MOVILNET PARA EL EGRESS DE N8N:")
            print("═" * 78)
            print(f"Estado:              {res_exec['status']}")
            print(f"Latencia:            {res_exec['latency_ms']:.2f} ms")
            print(f"Tokens Consumidos:   {res_exec['tokens_cost_usd']} USD (Zero Cost)")
            print(f"Intención:           {res_exec['intent']}")
            print("\n📩 [TEXTO EGRESS WHATSAPP]:\n")
            print(res_exec["reply_text"])
            print("\n" + "═" * 78 + "\n")
        else:
            print("❌ Opción no reconocida.")

        # Preguntar si desea realizar otra prueba
        try:
            otro = input("🔄 ¿Deseas realizar otra prueba? (s/n) [Default: s]: ").strip().lower()
            if otro in ("n", "no", "salir", "exit", "q"):
                print("\n👋 ¡Gracias por realizar las pruebas pre-producción!")
                break
            print("\n" + "—" * 78 + "\n")
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Saliendo del simulador...")
            break


def run_self_test():
    """Auto-verificación formal del simulador interactivo (Pilar V)."""
    # Test 1: Movilnet Subscriber Altamira
    res1 = ejecutar_evaluacion("04161234567", latitude=10.4960, longitude=-66.8530)
    assert res1["is_movilnet_subscriber"] is True
    assert res1["tokens_consumed"] == 0
    assert "Agencia Movilnet más cercana" in res1["response_text"]
    assert "Google Maps" in res1["response_text"]

    # Test 2: Competitor 0414 Valencia
    res2 = ejecutar_evaluacion("04142554590", latitude=10.1990, longitude=-67.9550)
    assert res2["is_movilnet_subscriber"] is False
    assert "Portabilidad" in res2["response_text"]
    assert res2["tokens_consumed"] == 0

    # Test 3: Text query Maracaibo
    res3 = ejecutar_evaluacion("04129998877", message_text="Oficinas en Maracaibo")
    assert "Maracaibo" in res3["response_text"]
    assert res3["tokens_consumed"] == 0

    print("✅ [AUTO-VERIFICACIÓN FORMAL]: 3/3 Pruebas de integración del simulador exitosas (100% PASS).")


def main():
    parser = argparse.ArgumentParser(description="Simulador Interactivo de Geolocalización Movilnet 4GMAX")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación formal matemática")
    parser.add_argument("--phone", type=str, default="", help="Número de teléfono celular (ej. 04161234567)")
    parser.add_argument("--lat", type=float, default=None, help="Latitud GPS WGS84")
    parser.add_argument("--lon", type=float, default=None, help="Longitud GPS WGS84")
    parser.add_argument("--query", type=str, default="", help="Consulta textual (ej. 'agencias en Valencia')")
    args = parser.parse_args()

    if args.test:
        run_self_test()
        return

    # Si se pasan parámetros directos por CLI
    if args.phone or args.lat is not None or args.query:
        phone = args.phone or "04161234567"
        query = args.query or "Ubicación actual"
        res = ejecutar_evaluacion(phone, message_text=query, latitude=args.lat, longitude=args.lon)
        imprimir_resultado_prueba(res)
        return

    # Modo interactivo por defecto
    modo_interactivo()


if __name__ == "__main__":
    main()
