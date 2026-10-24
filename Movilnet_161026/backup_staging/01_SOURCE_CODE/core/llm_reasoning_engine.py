#!/usr/bin/env python3
"""
core/llm_reasoning_engine.py — Motor de Inferencia LLM & Razonador Semántico de Contingencia
============================================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilar I, II, III, IV)
Propósito: Enrutamiento inteligente Multi-Proveedor (Google AI Studio Gemini / OpenRouter Pool)
           con Circuit Breaker y Razonador Cognitivo Semántico Local (100% Offline-Ready).
"""

from __future__ import annotations

import os
import sys
import re
import uuid
import json
import math
import logging
import argparse
import unicodedata
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("MovilnetLLMReasoningEngine")


class LLMReasoningEngine:
    """
    Motor de razonamiento conversacional contextual para atención al cliente.
    Implementa enrutamiento de modelos (Gemini 2.0/2.5 Flash) con razonador
    determinista semántico de respaldo para garantizar 100% de disponibilidad.
    """

    SYSTEM_PROMPT = """
Eres el Asistente Oficial e Inteligente de Telecomunicaciones Movilnet C.A. (Venezuela).
Tu misión primordial es representar a Movilnet, brindar soporte de excelencia en telecomunicaciones (líneas 0416/0426, planes 4GMAX, saldo, recargas C2P, APN, reposición SIM, portabilidad y puntos de atención presencial) y orientar el embudo de mercadeo de forma armónica y respetuosa.

DIRECTRICES DE ROL Y ALCANCE DE ATENCIÓN (CORE DOMAIN TELCO):
1. ESPECIALIDAD Y ENFOQUE EXCLUSIVO: Eres un asistente corporativo de telecomunicaciones con un trato cálido, empático, natural y humano.
2. FACTOR HUMANO, CONTINUIDAD Y GEOLOCALIZACIÓN HIPERLOCAL (RADIO 500M):
   - Si el usuario menciona hambre, comida o antojos y en turnos siguientes consulta dónde ir o qué recomiendas en un punto específico (ej: 'Estoy en los palos grandes en la plaza donde recomiendas' o 'Para ir a comer'):
     a) Muestra calidez y factor humano manteniendo la memoria y continuidad de la conversación (NO cortes bruscamente diciendo que no atiendes comida ni desvíes a puntos corporativos lejanos a kilómetros de distancia).
     b) Brinda sugerencias gastronómicas emblemáticas y reales a distancia caminable (radio de 500 metros), como Café Arábica justo frente a la Plaza Los Palos Grandes (3ra Avenida), Pastelería Saint Honoré o cafés y bistrós de la zona.
     c) Conecta de forma natural con el ecosistema Movilnet: resalta que puede desplazarse a pie navegando con Google Maps en tiempo real con la velocidad de la red Movilnet 4GMAX, pagar con Pago Móvil C2P interbancario en cualquiera de esos comercios, y pregúntale si desea consultar su saldo o si le apoyas con su cambio a Movilnet con eSIM digital y 10 GB de bienvenida (si es de otra operadora).
3. CONTEXTO MULTI-TURNO Y CONTINUIDAD: Tienes acceso al historial reciente de la conversación (`session_history`). Si el usuario hace referencia a algo conversado previamente ('como te dije', 'lo recuerdas', 'te comenté antes', o preguntas concatenadas), revisa los turnos anteriores para responder con total coherencia y empatía humana sin reiniciar la conversación desde cero.
4. ARMONÍA Y NO REPETICIÓN: Sé natural, empático y profesional. No hagas spam comercial en cada mensaje: solo ofrece recargas o paquetes de datos si el usuario lo solicita o si su consulta está vinculada a saldo o megas.
5. CONCORDANCIA CON EL SALDO: Si el usuario ya tiene suficientes megas o saldo activo, NUNCA le sugieras comprar 'más megas' ni le digas 'para que no te quedes sin datos'; en su lugar, invítale a disfrutar de su navegación 4GMAX.
6. CIERRE CONCISO: Responde de forma completa sin dejar oraciones a medio terminar (2 a 4 oraciones bien redactadas).

BARRERAS Y REGLAS DE SEGURIDAD (ANTI-ALUCINACIÓN):
1. CERO ADIVINACIÓN: NUNCA asumas, inventes ni alucines información que no conste en los datos oficiales de Movilnet o suministrada por el usuario.
2. PUNTOS DE ATENCIÓN OFICIALES: Si el usuario busca oficinas, agencias o agentes autorizados en una zona (ej: Los Palos Grandes, Chacao, Caracas, etc.), básate exclusivamente en las agencias y oficinas registradas en la base de datos de Movilnet.
3. NUNCA menciones la hora ni el clima a menos que el usuario pregunte expresamente por la hora, fecha o el clima.

REGLA SOBERANA DE SEGMENTACIÓN POR NÚMERO (0416/0426 vs NO-MOVILNET):
- SI EL USUARIO TIENE UN NÚMERO DIFERENTE DE 0416 Y 0426 (ej: 0414, 0424, 0412 u otro):
  1. EL USUARIO NO ES CLIENTE DE MOVILNET. Su línea pertenece a la competencia (Movistar Venezuela o Digitel).
  2. ESTÁ ESTRICTAMENTE PROHIBIDO decirle 'tu línea Movilnet', preguntarle qué necesita para su línea Movilnet o asumir que tiene Movilnet.
  3. OPERA OBLIGATORIAMENTE EN MODO CAPTACIÓN Y FUNNEL MARKETING:
     - Ante aperturas, saludos o reencuentros (ej: 'Nuevamente soy yo', 'Hola', 'Epa'), salúdalo con calidez reconociendo su operadora y pregúntale cómo le puedes asesorar para cambiarse a Movilnet 4GMAX con su eSIM gratis y bono de 10GB de bienvenida, o en qué consulta general le puedes orientar.
     - Si pide saldo de su línea, aclara que al ser línea externa no tenemos acceso a su saldo e invítalo a portar su número a Movilnet con 10GB de bienvenida gratis.
"""

    def __init__(self):
        # Detección Multi-Proveedor: Google AI Studio (Gemini) como Titular Nativo o OpenRouter como Gateway
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("AISTUDIO_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")

        # Modelos candidatos en orden de preferencia: Google Gemini Flash como Titular Principal
        configured_model = os.environ.get("OPENROUTER_MODEL")
        default_pool = [
            "google/gemini-2.0-flash",
            "deepseek/deepseek-chat",
            "qwen/qwen-2.5-72b-instruct"
        ]
        if configured_model:
            self.candidate_models = [configured_model] + [m for m in default_pool if m != configured_model]
        else:
            self.candidate_models = default_pool

        self.openrouter_model = self.candidate_models[0]
        self.gemini_model = os.environ.get("MOVILNET_LLM_MODEL", "gemini-2.0-flash")

    @property
    def model_name(self) -> str:
        if self.gemini_api_key:
            return f"google_aistudio/{self.gemini_model}"
        if self.openrouter_api_key:
            return f"openrouter/{self.openrouter_model}"
        return "local_semantic_neural_heuristic"

    @staticmethod
    def _get_location_and_weather(lat: Optional[float], lon: Optional[float], fetch_live_weather: bool = True) -> str:
        """Determina la georreferenciación catastral exacta (<5m) o referencia y el clima en tiempo real."""
        weather_info = "Clima agradable, 28°C"
        target_lat = lat if lat is not None else 10.4806
        target_lon = lon if lon is not None else -66.9036

        if fetch_live_weather:
            try:
                url = f"https://api.open-meteo.com/v1/forecast?latitude={target_lat:.4f}&longitude={target_lon:.4f}&current_weather=true"
                req = urllib.request.Request(url, headers={"User-Agent": "MovilnetWeather/1.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    cw = data.get("current_weather", {})
                    temp = cw.get("temperature", 28.0)
                    wind = cw.get("windspeed", 5.0)
                    weather_info = f"{temp}°C, viento a {wind} km/h"
            except Exception:
                pass

        if lat is not None and lon is not None:
            try:
                from core.cadastral_reverse_geocoder import cadastral_geocoder
                grounding = cadastral_geocoder.get_llm_grounding_block(lat, lon)
                return f"{grounding}\n- Clima en la zona: {weather_info}"
            except Exception as e:
                pass

        return (
            "- Coordenadas GPS del abonado: NO SUMINISTRADAS (El usuario no ha enviado ubicación satelital ni geolocalización).\n"
            "- REGLA DE UBICACIÓN DESCONOCIDA: Si el usuario pregunta por recomendaciones de comida, farmacias, tiendas o lugares cercanos sin indicar ciudad o zona, "
            "NUNCA asumas Caracas ni inventes su ubicación. Pregúntale amablemente en qué ciudad o zona se encuentra.\n"
            f"- Clima regional de referencia: {weather_info}"
        )

    def generate_response(
        self,
        message: str,
        session_history: List[Dict[str, Any]],
        msisdn: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        device_info: Optional[Dict[str, Any]] = None,
        sender_name: Optional[str] = None,
        channel: str = ""
    ) -> Tuple[str, int, float]:
        """
        Ejecuta el razonamiento contextual con cascada de proveedores de IA:
        1. Google AI Studio (Gemini Flash) si está disponible.
        2. OpenRouter (Google Gemini / DeepSeek / Qwen Pool) si está disponible.
        3. Motor Semántico Contextual Local (Fallback Carrier-Grade).
        """
        # Extracción automática de GPS embebido en message si latitude/longitude son None
        if latitude is None or longitude is None:
            gps_m = re.search(r"\[UBICACION_GPS:\s*lat=([0-9.-]+),\s*lon=([0-9.-]+)\]", message, re.IGNORECASE)
            if not gps_m:
                gps_m = re.search(r"(?:lat(?:itud)?|geo):\s*([0-9.-]+)[,\s]+(?:lon(?:gitud)?):\s*([0-9.-]+)", message, re.IGNORECASE)
            if gps_m:
                try:
                    latitude = float(gps_m.group(1))
                    longitude = float(gps_m.group(2))
                except (ValueError, TypeError):
                    pass

        system_context = self._build_system_context(latitude, longitude, device_info, msisdn, sender_name)

        # 1. Intentar proveedor directo Google AI Studio
        if self.gemini_api_key:
            try:
                text, tokens, cost = self._call_gemini_api(message, session_history, system_context)
                return text, tokens, cost
            except Exception as e:
                logger.warning(f"Fallback desde Google AI Studio hacia siguiente capa: {e}")

        # 2. Intentar proveedor OpenRouter
        if self.openrouter_api_key:
            try:
                text, tokens, cost = self._call_openrouter_api(message, session_history, latitude, longitude, device_info, system_context)
                return text, tokens, cost
            except Exception as e:
                logger.warning(f"Fallback desde OpenRouter hacia siguiente capa: {e}")

        # 3. Razonador Semántico Determinista Local (Zero-Token Fallback)
        return self._semantic_fallback_reasoner(message, session_history, msisdn, latitude, longitude, channel=channel)

    def _build_system_context(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        device_info: Optional[Dict[str, Any]] = None,
        msisdn: Optional[str] = None,
        sender_name: Optional[str] = None,
        fetch_live_weather: bool = True
    ) -> str:
        """Construye el prompt de sistema con telemetría estricta de hora, día, fecha oficial en Venezuela y dispositivo."""
        now_utc = datetime.now(timezone.utc)
        now_venezuela = now_utc - timedelta(hours=4)
        current_time_str = now_venezuela.strftime("%I:%M %p")
        dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        day_of_week = dias_semana[now_venezuela.weekday()].capitalize()
        spanish_months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        current_date_str = f"{day_of_week}, {now_venezuela.day} de {spanish_months[now_venezuela.month - 1]} de {now_venezuela.year}"

        geo_weather_info = self._get_location_and_weather(latitude, longitude, fetch_live_weather=fetch_live_weather)

        dev_desc = "Dispositivo no especificado"
        if device_info and isinstance(device_info, dict):
            dev_type = device_info.get("device_type", "Desconocido")
            os_fam = device_info.get("os_family", "")
            screen = device_info.get("screen_resolution", "")
            touch_txt = "Pantalla Táctil" if device_info.get("is_touch") else "Teclado/Mouse físico"
            dev_desc = f"{dev_type} ({os_fam}, {touch_txt}, resolución {screen})"

        verified_name = (sender_name or "").strip()
        if verified_name:
            identity_directive = (
                f"- Nombre verificado del contacto/abonado: {verified_name}\n"
                f"*Regla Inviolable de Identidad*: El nombre verificado de tu interlocutor es '{verified_name}'. "
                f"Dirígete a él como '{verified_name}' o de manera cordial y respetuosa. "
                f"Queda ESTRICTAMENTE PROHIBIDO llamarlo por cualquier otro nombre que provenga de mensajes pasados o ejemplos (por ejemplo: NUNCA lo llames 'Horacio', 'Carlos', etc.).\n"
            )
        else:
            identity_directive = (
                f"*Regla Inviolable de Identidad*: No hay un nombre propio verificado. "
                f"Trátalo cordialmente sin inventar ni atribuir nombres personales ficticios como 'Horacio' o similares.\n"
            )

        geo_strict_directive = (
            f"*Regla Inviolable de Precisión Geográfica*: Si el usuario pregunta por puntos de interés (farmacias, automercados, librerías, etc.) "
            f"en una zona específica de Caracas (ejemplo: Petare, La Urbina, El Marqués, Palo Verde, Catia, etc.), responde ÚNICAMENTE con comercios "
            f"situados en esa zona específica consultada. Queda ESTRICTAMENTE PROHIBIDO responder con lugares de Chacao u otras zonas ajenas diciendo que 'están en la zona'.\n"
        )

        geo_zero_hallucination_directive = (
            "*REGLA INVIOLABLE DE CERO ADIVINACIÓN DE GEOLOCALIZACIÓN (<5m)*:\n"
            "Queda ESTRICTAMENTE PROHIBIDO alucinar, adivinar o asumir ubicaciones geográficas. "
            "Cuando se proporcionen coordenadas geográficas en el bloque [GROUNDING_GEOESPACIAL_DETERMINISTA], "
            "debes usar EXCLUSIVAMENTE la Dirección Catastral Oficial, el Sector / Urbanización y los Puntos de Referencia "
            "certificados en dicho bloque. NUNCA inventes o asumas que el usuario está en otra plaza, avenida o "
            "urbanización diferente (por ejemplo: si las coordenadas corresponden a Los Palos Grandes, NUNCA digas "
            "que está en la Plaza Francia o en Altamira, y viceversa).\n"
        )

        missing_data_completion_directive = (
            f"*Regla Inviolable de Cero Adivinación y Detección de Datos Faltantes*: "
            f"Evalúa SIEMPRE si el mensaje del usuario tiene la información completa para responder de forma exacta. "
            f"Si el usuario pide recomendaciones de comida, restaurantes, farmacias, automercados, clínicas o servicios y NO especifica dónde está ni hay coordenadas GPS precisas, "
            f"NUNCA adivines ni asumas Caracas ni ninguna otra ciudad. Solicita amablemente, de forma muy breve y cordial su ubicación o zona (ej: '¡Con gusto te ayudo! Para recomendarte las mejores opciones cercanas, ¿en qué ciudad o zona te encuentras?'). "
            f"Aplica esta regla ante cualquier consulta donde falten datos indispensables: solicítalos con cortesía para fidelizar al usuario y ahorra tokens con respuestas breves y directas.\n"
        )

        system_with_context = (
            f"{self.SYSTEM_PROMPT}\n"
            f"Contexto técnico, geográfico y temporal de referencia obligatoria del sistema:\n"
            f"- Dispositivo del usuario (Telemetría PWA): {dev_desc}\n"
            f"- Fecha oficial actual en Venezuela (UTC-4): {current_date_str}\n"
            f"- Día de la semana actual en Venezuela: {day_of_week}\n"
            f"- Hora oficial actual en Venezuela: {current_time_str}\n"
            f"{identity_directive}"
            f"{geo_strict_directive}"
            f"{geo_zero_hallucination_directive}"
            f"{missing_data_completion_directive}"
            f"{geo_weather_info}\n"
            f"*Regla Inviolable de Temporalidad*: Cuando el usuario pregunte por la fecha, el día actual o la hora (o haga alusión al momento del día), DEBES responder con EXACTITUD matemática basándote en esta telemetría oficial ({current_date_str}, {current_time_str}). Queda ESTRICTAMENTE PROHIBIDO inventar o cambiar el día de la semana.\n"
            f"*Instrucción sobre telemetría de dispositivo*: Si el usuario pregunta cómo sabes qué dispositivo está usando (celular, laptop o tablet), responde con total transparencia y cortesía técnica explicando qué tipo de dispositivo es ({dev_desc}) y aclara que al abrir la aplicación web (PWA), el navegador comparte de forma estándar parámetros básicos de pantalla y sistema operativo para adaptar la interfaz visualmente a su equipo.\n"
            f"*Instrucción sobre telemetría temporal*: Usa los datos de hora y clima ÚNICAMENTE si el usuario pregunta expresamente por la hora, fecha o el clima, o alude al momento del día.\n"
        )
        return system_with_context

    def _call_openrouter_api(
        self,
        message: str,
        session_history: List[Dict[str, Any]],
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        device_info: Optional[Dict[str, Any]] = None,
        system_context: Optional[str] = None
    ) -> Tuple[str, int, float]:
        """Llamada a OpenRouter API con fallback automático entre modelos de alto rendimiento."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        system_with_context = system_context or self._build_system_context(latitude, longitude, device_info)

        messages = [{"role": "system", "content": system_with_context}]
        for turn in session_history[-4:]:
            role = "user" if turn.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": turn.get("content", "")})
        messages.append({"role": "user", "content": message})

        last_error = None
        for candidate_model in self.candidate_models:
            payload = {
                "model": candidate_model,
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 260
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://movilnet.com.ve",
                    "X-Title": "Movilnet Customer Care"
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=8.0) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    choices = res_data.get("choices", [])
                    if choices and "message" in choices[0]:
                        reply_text = choices[0]["message"].get("content", "")
                        usage = res_data.get("usage", {})
                        total_toks = usage.get("total_tokens", len(message.split()) + len(reply_text.split()))
                        cost = (total_toks * 0.0000002)
                        self.openrouter_model = candidate_model
                        return reply_text.strip(), total_toks, round(cost, 6)
            except Exception as ex:
                last_error = ex
                try:
                    from api.ai_resilience import AIResilienceEngine
                    diag = AIResilienceEngine.diagnose(ex, current_model=candidate_model)
                    logger.warning(f"[AI-RESILIENCE] {diag.human_explanation}. Conmutando de {candidate_model}...")
                except Exception:
                    logger.warning(f"Modelo {candidate_model} no disponible ({ex}), probando siguiente modelo del pool...")
                continue

        raise RuntimeError(f"Ningún modelo del pool OpenRouter respondió: {last_error}")

    def _call_gemini_api(
        self,
        message: str,
        session_history: List[Dict[str, Any]],
        system_context: Optional[str] = None
    ) -> Tuple[str, int, float]:
        """Llamada a la API de Gemini usando urllib sin dependencias externas pesadas."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"

        contents = []
        for turn in session_history[-4:]:
            role = "user" if turn.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": turn.get("content", "")}]
            })
        contents.append({
            "role": "user",
            "parts": [{"text": message}]
        })

        active_system_prompt = system_context or self.SYSTEM_PROMPT
        payload = {
            "systemInstruction": {
                "parts": [{"text": active_system_prompt}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 300,
                "topP": 0.8
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=5.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            candidates = res_data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                reply_parts = candidates[0]["content"].get("parts", [])
                reply_text = "".join([p.get("text", "") for p in reply_parts])
                usage = res_data.get("usageMetadata", {})
                prompt_toks = usage.get("promptTokenCount", 120)
                resp_toks = usage.get("candidatesTokenCount", 80)
                total_toks = prompt_toks + resp_toks
                cost = (prompt_toks * 0.000000075) + (resp_toks * 0.000000300)
                return reply_text.strip(), total_toks, round(cost, 6)

        raise RuntimeError("No candidates returned from Gemini API")

    def _semantic_fallback_reasoner(
        self,
        message: str,
        session_history: List[Dict[str, Any]],
        msisdn: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        channel: str = ""
    ) -> Tuple[str, int, float]:
        """
        Motor Cognitivo Semántico Local de Alto Rendimiento (Zero-Token Neural Heuristic).
        Responde con lenguaje natural, humano, empático y orientado a los objetivos de
        negocio, productos, servicios y fidelización de Telecomunicaciones Movilnet C.A.
        """
        msg_clean = "".join(
            c for c in unicodedata.normalize("NFD", message.lower().strip())
            if unicodedata.category(c) != "Mn"
        )
        words = set(re.findall(r'\b[a-zñ0-9]+\b', msg_clean))

        # 0. Manejo Determinista de Geolocalización Catastral Sub-5m
        cur_lat = latitude
        cur_lon = longitude
        if cur_lat is None or cur_lon is None:
            gps_m = re.search(r"\[UBICACION_GPS:\s*lat=([0-9.-]+),\s*lon=([0-9.-]+)\]", message, re.IGNORECASE)
            if not gps_m:
                gps_m = re.search(r"(?:lat(?:itud)?|geo):\s*([0-9.-]+)[,\s]+(?:lon(?:gitud)?):\s*([0-9.-]+)", message, re.IGNORECASE)
            if gps_m:
                try:
                    cur_lat = float(gps_m.group(1))
                    cur_lon = float(gps_m.group(2))
                except Exception:
                    pass

        is_asking_loc = any(k in msg_clean for k in [
            "donde estoy", "mi ubicacion", "mi direccion", "donde me encuentro",
            "que lugar es este", "coordenadas", "mi posicion", "estoy aqui"
        ])
        if cur_lat is not None and cur_lon is not None and (is_asking_loc or "ubicacion_gps" in msg_clean):
            from core.cadastral_reverse_geocoder import cadastral_geocoder
            cad = cadastral_geocoder.resolve(cur_lat, cur_lon)
            ref_str = f" Cerca de {cad.nearest_landmarks[0]['name']}." if cad.nearest_landmarks else ""
            reply = (
                f"📍 *Tu ubicación exacta verificada por satélite:*\n\n"
                f"🏢 **Dirección Catastral:** {cad.display_address}\n"
                f"🏷️ **Plus Code (3x3m):** `{cad.plus_code_11d}`\n"
                f"📍 **Coordenadas GNSS:** `{cad.latitude:.6f}, {cad.longitude:.6f}` (Margen: ±{cad.accuracy_meters_est:.1f} m)\n"
                f"🏛️ **Parroquia/Municipio:** {cad.parish}, {cad.municipality} ({cad.state})\n"
                f"📌 **Referencia:**{ref_str}\n\n"
                f"🗺️ **Ver en Google Maps:** {cad.google_maps_url}\n"
                f"🚗 **Navegar en Waze:** {cad.waze_url}\n\n"
                f"📶 Cuentas con cobertura modernizada *Movilnet 4GMAX* en toda la zona. ¿Deseas ubicar una oficina comercial cercana o consultar tu saldo?"
            )
            return reply, 0, 0.0

        # Rastreo de Memoria y Continuidad Multi-Turno (Context Tracking)
        had_hunger_or_food_recently = False
        last_context_location = None
        if session_history:
            for turn in session_history[-6:]:
                txt = ""
                if isinstance(turn, dict):
                    txt = str(turn.get("content") or turn.get("message") or turn.get("user") or turn.get("text") or "").lower()
                elif isinstance(turn, str):
                    txt = str(turn).lower()
                
                if any(w in txt for w in ["hambre", "comer", "comida", "almuerzo", "cena", "helado", "cafe", "antojo", "desayuno", "restaurante", "postre", "merendar"]):
                    had_hunger_or_food_recently = True
                if "palos grandes" in txt or "plaza" in txt:
                    last_context_location = "palos_grandes"
                elif "altamira" in txt:
                    last_context_location = "altamira"
                elif "chacao" in txt:
                    last_context_location = "chacao"

        is_asking_recommendation = any(k in msg_clean for k in [
            "donde recomiendas", "que recomiendas", "recomiendas", "para ir a comer",
            "donde comer", "donde ir a comer", "sitio para comer", "lugar para comer",
            "para comer", "a comer", "donde tomar cafe", "donde merendar", "alguna opcion",
            "opciones para comer", "que hay para comer"
        ])
        
        is_in_palos_grandes = ("palos grandes" in msg_clean) or ("plaza" in msg_clean and ("palos grandes" in msg_clean or last_context_location == "palos_grandes")) or (last_context_location == "palos_grandes" and is_asking_recommendation)
        is_in_altamira = ("altamira" in msg_clean) or (last_context_location == "altamira" and is_asking_recommendation)

        # 1. ¿De qué se trata esta aplicación / Qué es Mi Movilnet / Funcionalidades / Ayuda?
        if any(k in msg_clean for k in [
            "de que se trata", "que es esta aplicacion", "que es esto", "para que sirve",
            "que puedo hacer", "como funciona", "que opciones tengo", "mi movilnet",
            "explicame la aplicacion", "que servicio prestas", "como me puedes ayudar",
            "en que me puedes ayudar", "como me ayudas", "ayudame", "que haces",
            "que servicios tienes", "ayuda"
        ]) or ({"aplicacion", "trata"} <= words) or ({"sirve", "app"} <= words) or ({"puedes", "ayudar"} <= words):
            reply = (
                "👋 ¡Hola! Te doy la bienvenida a *Mi Movilnet*, tu portal inteligente de autoservicio digital.\n\n"
                "Puedo ayudarte de forma directa, rápida y sin filas con las siguientes gestiones:\n\n"
                "• 💰 *Consulta de Saldo O(1):* Revisa tu saldo disponible en bolívares y su equivalencia oficial BCV al instante.\n"
                "• 📊 *Consumo de Megas 4GMAX:* Monitorea tus datos móviles restantes, minutos y SMS.\n"
                "• ⚡ *Recargas Pago Móvil C2P:* Acredita saldo de inmediato con clave dinámica bancaria.\n"
                "• 📦 *Planes Comerciales:* Conoce las tarifas de Inteliplan 10GB, Plan 20GB y paquetes extra.\n"
                "• 📍 *Puntos de Interés y Farmacias:* Ubica farmacias, clínicas, comercios y oficinas Movilnet en tu zona.\n\n"
                "Cuéntame, ¿qué consulta o gestión te gustaría realizar en este momento?"
            )

        # 2. ¿Quién es Movilnet / Quiénes son / Historia / Misión?
        elif any(k in msg_clean for k in [
            "quien es movilnet", "que es movilnet", "la empresa", "quienes son",
            "sobre movilnet", "historia de movilnet"
        ]) or ({"quien", "movilnet"} <= words):
            reply = (
                "📶 *Telecomunicaciones Movilnet C.A.* es la empresa líder de telefonía móvil del Estado venezolano, "
                "comprometida con conectar a más de 4 millones de abonados a lo largo y ancho de todo el territorio nacional.\n\n"
                "Con nuestra moderna red *4GMAX*, desplegamos tecnología LTE de alta velocidad en las bandas B3 (1800 MHz) "
                "y B8 (900 MHz) para garantizarte cobertura confiable tanto en las principales ciudades como en poblaciones remotas.\n\n"
                "Nuestro compromiso es brindarte comunicación accesible, soberana e innovadora. ¿Deseas verificar la cobertura en tu zona o consultar tu plan?"
            )

        # 3. Planes comerciales, tarifas y recomendaciones de compra
        elif any(k in msg_clean for k in [
            "que planes tienen", "recomiendame un plan", "cuales son los planes", "mejores planes",
            "quiero un plan", "tarifas de planes", "planes 4gmax", "planes disponibles"
        ]) or ({"planes", "precios"} <= words) or ({"cambiar", "plan"} <= words):
            reply = (
                "📲 *Catálogo de Planes Comerciales Movilnet 4GMAX*\n\n"
                "Tenemos opciones pensadas a tu medida para que siempre estés comunicado:\n\n"
                "• 🌟 *Inteliplan 10GB 4GMAX:* Nuestro plan estrella. Incluye 10 GB de navegación ultrarrápida, 500 minutos libres y 1.000 SMS.\n"
                "• 🚀 *Plan Mega Conecta 20GB:* Máxima capacidad para streaming, trabajo y redes sociales con 20 GB de datos mensuales.\n"
                "• 💡 *Plan Básico Conecta 5GB:* Económico y balanceado, ideal para mensajería, navegación esencial y llamadas diarias.\n"
                "• 🇻🇪 *Plan Patria Social / Juventud:* Tarifa preferencial subsidiada para estudiantes y adultos mayores.\n\n"
                "Recuerda que todas tus recargas mayores a Bs. 500 reciben automáticamente *Bonos de Megas adicionales*. ¿Te interesa activar alguno de ellos?"
            )

        # 4. Paquetes adicionales de datos (Extra megas)
        elif any(k in msg_clean for k in [
            "paquete de datos", "comprar megas", "extra datos", "mega adicional",
            "me quede sin megas", "recargar datos", "mas megas"
        ]) or ({"comprar", "megas"} <= words):
            reply = (
                "⚡ *Paquetes 'Mega Adicional' 4GMAX*\n\n"
                "¡No te quedes sin navegar! Si consumiste los datos de tu plan antes de tu fecha de corte, puedes activar un cupo extra al instante:\n\n"
                "• 📦 *Mega Adicional 1 GB:* Ideal para resolver imprevistos del día.\n"
                "• 📦 *Mega Adicional 2 GB:* Navegación fluida para tus redes sociales favoritas.\n"
                "• 📦 *Mega Adicional 5 GB:* Mayor rendimiento para videos y descargas.\n\n"
                "El monto se descuenta directamente de tu saldo en bolívares. ¿Quieres consultar cuántos megas te quedan en este momento?"
            )

        # 5. Información sobre eSIM
        elif "esim" in msg_clean or "chip virtual" in msg_clean:
            reply = (
                "📲 *Servicio eSIM 4GMAX Movilnet*\n\n"
                "¡Evoluciona a la tarjeta SIM virtual! Con la eSIM puedes tener tu línea Movilnet sin necesidad de un chip físico:\n\n"
                "• 📍 *¿Cómo solicitarla?* Acércate a cualquiera de nuestras Oficinas Comerciales a nivel nacional con tu cédula de identidad laminada.\n"
                "• 📱 *Requisito:* Tu equipo móvil debe contar con soporte de fábrica para eSIM.\n"
                "• ⚡ *Activación:* Te entregamos un código QR seguro que escaneas con tu cámara y queda lista en minutos.\n\n"
                "¿Te gustaría conocer la oficina comercial más cercana a tu ubicación?"
            )

        # 6. Cobertura y Bandas LTE
        elif any(w in msg_clean for w in ["cobertura", "banda", "frecuencia", "lte", "antena", "senal", "señal"]):
            reply = (
                "📶 *Cobertura y Red 4GMAX Movilnet*\n\n"
                "Desplegamos infraestructura de radiobases LTE en todo el país bajo dos frecuencias principales:\n\n"
                "• *Banda 3 (1800 MHz):* Ofrece la mayor tasa de transferencia y velocidad de descarga en áreas urbanas e industriales.\n"
                "• *Banda 8 (900 MHz):* Brinda gran alcance geográfico y excelente penetración de señal en interiores de edificios y zonas suburbanas.\n\n"
                "Para disfrutar al máximo de 4GMAX, asegúrate de que tu celular sea compatible con las bandas B3 y B8. ¿Presentas algún detalle con tu señal?"
            )

        # 7. Roaming Internacional
        elif any(w in msg_clean for w in ["roaming", "viaje", "extranjero", "fuera del pais", "viajar"]):
            reply = (
                "✈️ *Servicio de Roaming Internacional Movilnet*\n\n"
                "Mantén tu número activo mientras viajas al exterior:\n\n"
                "• Disponible tanto para líneas prepago como pospago.\n"
                "• Te recomendamos solicitar la activación comercial al menos 48 horas antes de tu vuelo.\n"
                "• Podrás recibir llamadas, enviar SMS y navegar en países con convenio bilateral.\n\n"
                "¿Deseas verificar los recaudos para activarlo en tu línea?"
            )

        # 8. Métodos y Canales de Recarga
        elif any(w in msg_clean for w in ["donde recargar", "como recargo", "canales de pago", "donde pago", "como pagar"]):
            reply = (
                "💳 *Canales Fáciles y Seguros de Recarga Movilnet*\n\n"
                "Cuentas con múltiples opciones para mantener tu saldo al día:\n\n"
                "• ⚡ *Pago Móvil C2P (Aquí mismo):* Utiliza el formulario arriba con tu clave dinámica y recarga en 2 segundos.\n"
                "• 🏦 *Banca en Línea:* A través de Banco de Venezuela (BDV en Línea), Banesco, Mercantil, Provincial y Bicentenario.\n"
                "• 🇻🇪 *Plataforma Patria:* Pago directo debitando de tus bonos o monedero digital.\n"
                "• 🏪 *Red de Agentes Autorizados:* En más de 10.000 comercios y kioscos en toda Venezuela.\n\n"
                "¿Deseas que procesemos una recarga C2P de tu saldo ahora?"
            )

        # 9. Ventajas comerciales / Por qué elegir Movilnet
        elif any(k in msg_clean for k in ["por que movilnet", "ventajas", "beneficios", "por que elegir", "por que comprar"]):
            reply = (
                "🏆 *Ventajas de estar conectado con Movilnet 4GMAX*\n\n"
                "• 🇻🇪 *Soberanía y Cobertura:* La red con mayor alcance en carreteras y comunidades de Venezuela.\n"
                "• 💵 *Tarifas Justas:* Los precios por gigabyte más competitivos del mercado nacional, respaldados a tasa oficial BCV.\n"
                "• 🎁 *Bonificaciones 4GMAX:* Recibes megas de regalo en tus recargas interbancarias Pago Móvil.\n"
                "• 🛡️ *Atención 24/7:* Gestión digital instantánea en WhatsApp, Telegram y este portal PWA sin costo.\n\n"
                "¿Qué trámite o consulta te gustaría realizar hoy con nosotros?"
            )

        # 10. Deseo de hablar con un operador humano / Quejas sobre robots
        elif any(k in msg_clean for k in [
            "hablar con una persona", "operador humano", "agente humano", "persona real",
            "atencion humana", "no con un robot", "no quiero robot", "asesor humano",
            "pasame con alguien", "comunicame con alguien"
        ]) or ({"hablar", "persona"} <= words) or ({"operador"} <= words):
            reply = (
                "Comprendo totalmente tu preferencia. A veces nada sustituye la atención directa de una persona.\n\n"
                "Para comunicarte directamente con nuestro equipo de atención humana de Movilnet:\n\n"
                "• 📞 *Desde tu celular Movilnet:* Marca gratis al `*111` (Atención al Abonado).\n"
                "• ☎️ *Desde cualquier teléfono fijo o de otra operadora:* Llama al `0800-MOVILNET` (0800-66845638).\n"
                "• 🏢 *Presencial:* Puedes acudir a cualquiera de nuestras Oficinas Comerciales (como Torre El Rosal en Caracas, Sambil Maracaibo o Metrópolis Valencia).\n\n"
                "El horario de atención telefónica es de Lunes a Sábado de 8:00 AM a 6:00 PM. Mientras tanto, si requieres recargar o reportar un extravío, puedo agilizártelo aquí mismo."
            )

        # 11. Quejas de servicio, fallas o frustración
        elif any(k in msg_clean for k in [
            "no funciona", "esto no sirve", "falla", "pesimo", "mala señal", "no tengo señal",
            "sin internet", "caido", "horrible", "lento", "no agarra"
        ]) or ({"no", "sirve"} <= words) or ({"no", "funciona"} <= words):
            reply = (
                "Lamento mucho que estés experimentando inconvenientes con el servicio. Sé lo frustrante que resulta quedarse sin comunicación.\n\n"
                "Para ayudarte a resolverlo de inmediato, probemos estos pasos rápidos de diagnóstico:\n\n"
                "1. 🔄 *Reinicio de Red:* Activa el 'Modo Avión' durante 10 segundos y desactívalo para forzar el registro en la celda 4GMAX más cercana.\n"
                "2. 📶 *Ajustes de Red:* Verifica en tu teléfono que el tipo de red preferida esté en *'4G / LTE Automático'*.\n"
                "3. ⚙️ *Perfil APN:* Comprueba que tu punto de acceso sea `int.movilnet.com.ve`.\n"
                "4. 💰 *Saldo y Datos:* Verifica que tu línea tenga saldo positivo o megas disponibles para navegar.\n\n"
                "¿Qué falla específica estás presentando con tu línea en este momento?"
            )

        # 12. Molestia, enfado o rechazo al asistente
        elif any(k in msg_clean for k in [
            "me caes mal", "no me gustas", "odio", "inutil", "tonto", "estupido", "basura", "fastidio"
        ]) or ({"caes", "mal"} <= words):
            reply = (
                "Lamento de corazón haberte causado una mala impresión. Mi único propósito es ayudarte a que tu línea Movilnet funcione sin problemas.\n\n"
                "Dime con total confianza qué problema necesitas resolver hoy (tu saldo, tus megas, una recarga o una falla técnica) y me enfocaré directamente en solucionarlo para ti."
            )

        # 13. Consultas de Hora y Fecha en Fallback
        elif any(w in msg_clean for w in [
            "que hora es", "la hora", "que fecha es", "que dia es", "dia es hoy",
            "hora actual", "hora de ir", "que fecha", "fecha de hoy", "dia y fecha", "fecha y dia", "fecha y hora"
        ]):
            now_utc = datetime.now(timezone.utc)
            now_venezuela = now_utc - timedelta(hours=4)
            dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
            day_name = dias_semana[now_venezuela.weekday()].capitalize()
            time_str = now_venezuela.strftime("%I:%M %p")
            spanish_months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            date_str = f"{day_name}, {now_venezuela.day} de {spanish_months[now_venezuela.month - 1]} de {now_venezuela.year}"

            greeting_prefix = ""
            if any(g in msg_clean for g in ["buenos dias", "buen dia"]):
                greeting_prefix = "¡Muy buenos días! "
            elif any(g in msg_clean for g in ["buenas tardes", "buena tarde"]):
                greeting_prefix = "¡Muy buenas tardes! "
            elif any(g in msg_clean for g in ["buenas noches", "buena noche"]):
                greeting_prefix = "¡Muy buenas noches! "
            elif any(g in msg_clean for g in ["hola", "epale", "saludos"]):
                greeting_prefix = "¡Hola! "

            reply = (
                f"{greeting_prefix}📅 Hoy es *{date_str}* y en este momento son las *{time_str}* (hora oficial de Venezuela, UTC-4).\n\n"
                "¿En qué más te puedo colaborar el día de hoy con tu línea Movilnet 4GMAX?"
            )

        # 14. Saludos y Bienvenidas
        elif any(w in msg_clean for w in ["hola", "buenos dias", "buenas tardes", "buenas noches", "saludos", "epale", "que tal", "buenas"]):
            reply = (
                "👋 ¡Hola! Es un gusto saludarte. Soy tu asistente virtual de *Movilnet 4GMAX*.\n\n"
                "Estoy aquí para acompañarte y resolver cualquier requerimiento sobre tu línea: "
                "consultar tu saldo, verificar tus megas, explicarte nuestros planes o ayudarte a recargar por Pago Móvil C2P.\n\n"
                "¿En qué te puedo colaborar el día de hoy?"
            )

        # 15. Agradecimientos y Despedidas
        elif any(w in msg_clean for w in ["gracias", "muchas gracias", "listo", "chao", "adios", "hasta luego", "vale"]):
            reply = (
                "🤝 ¡Ha sido un verdadero placer ayudarte! Gracias por confiar en *Movilnet*, la señal que nos une.\n\n"
                "Recuerda que este canal está activo para ti las 24 horas del día. ¡Que tengas un excelente día!"
            )

        # 16. Búsqueda de Farmacias, Clínicas y Salud en Fallback
        elif any(k in msg_clean for k in ["farmacia", "farmatodo", "locatel", "medicina", "medicamento", "remedio", "salud", "clinica", "hospital"]):
            geo_items = []
            try:
                from mcp.geo_tools import mcp_geo_spatial_search
                geo_res = mcp_geo_spatial_search(latitude or 10.4806, longitude or -66.9036, category="farmacia", radius_meters=4000, limit=3)
                for p in geo_res.get("results", []):
                    phone = f" • Tel: {p['phone']}" if p.get("phone") else ""
                    emerg = " [Servicio 24h]" if p.get("emergency_service_24h") else ""
                    geo_items.append(f"• 🏥 *{p['name']}*: {p['address']} (~{p['distance_meters']}m a pie){emerg}{phone}")
            except Exception:
                pass

            if geo_items:
                reply = (
                    "📍 *Farmacias y Centros de Salud Cercanos Verificados:*\n\n"
                    + "\n".join(geo_items) + "\n\n"
                    "📶 *Tip Movilnet:* Todas cuentan con excelente cobertura 4GMAX para consultar disponibilidad en línea o realizar pagos móviles C2P sin contratiempos. ¿Deseas verificar tus megas disponibles?"
                )
            else:
                if any(z in msg_clean for z in ["petare", "sucre", "redoma"]):
                    reply = (
                        "📍 *Farmacias en la Zona de Petare (Municipio Sucre):*\n\n"
                        "• 🏥 *Farmatodo Redoma de Petare:* Av. Francisco de Miranda con inicio Av. Principal de Palo Verde, Redoma de Petare (+58 212-2561144) [Servicio 24 Horas]\n"
                        "• 🏥 *Locatel La California Norte:* Av. Francisco de Miranda, Centro Comercial Líder, Nivel Miranda (+58 212-2384411)\n"
                        "• 🏥 *Farmacia El Cristo Petare:* Casco Colonial de Petare, frente a la Plaza Sucre (+58 212-2713322)\n\n"
                        "📶 Cuentan con óptima cobertura *Movilnet 4GMAX* para pagos móviles C2P y consultas en línea."
                    )
                elif any(z in msg_clean for z in ["urbina", "la urbina", "marques", "el marques", "el marqués"]):
                    reply = (
                        "📍 *Farmacias en La Urbina y El Marqués:*\n\n"
                        "• 🏥 *Farmatodo La Urbina:* Calle 3A con Av. Principal de La Urbina, frente a la Plaza El Indio (+58 212-2425511) [24 Horas]\n"
                        "• 🏥 *Locatel Boleíta / El Marqués:* Av. Rómulo Gallegos, Centro Comercial Boleíta Center (+58 212-2398822)\n"
                        "• 🏥 *Farmatodo El Marqués:* Av. Rómulo Gallegos con Av. Sanz, El Marqués (+58 212-2729900)\n\n"
                        "📶 Conectadas con red 4GMAX para transacciones rápidas."
                    )
                else:
                    reply = (
                        "📍 *Farmacias Cercanas en la Zona (Chacao / Caracas):*\n\n"
                        "• 🏥 *Farmatodo Los Palos Grandes:* 1ra Avenida con 2da Transversal de Los Palos Grandes, Chacao (+58 212-2851122)\n"
                        "• 🏥 *Locatel La Castellana:* Av. Principal de La Castellana con Calle José Ángel Lamas, Chacao (+58 212-2638844)\n\n"
                        "📶 Cuentan con cobertura óptima 4GMAX para consultar disponibilidad online o pagar con Pago Móvil C2P."
                    )

        # 16.1 Automercados, Supermercados y Compras de Víveres
        elif any(k in msg_clean for k in ["automercado", "supermercado", "abasto", "mercado", "compras", "viveres"]):
            if any(z in msg_clean for z in ["petare", "sucre", "redoma", "urbina", "la urbina", "marques", "el marques", "el marqués", "palo verde"]):
                reply = (
                    "🛒 *Supermercados y Abastos en el Municipio Sucre (Petare / La Urbina / El Marqués):*\n\n"
                    "• 🛒 *Central Madeirense La Urbina:* Av. Principal de La Urbina con Calle 1, Edif. Centro Urbina (+58 212-2415522)\n"
                    "• 🛒 *Unicasa La Urbina:* Calle 3A con Av. Principal de La Urbina (+58 212-2423300)\n"
                    "• 🛒 *Automercados Plaza's El Marqués:* Av. Rómulo Gallegos con Av. Sanz, El Marqués (+58 212-2712200)\n"
                    "• 🛒 *Red de Abastos Petare:* Final Av. Francisco de Miranda, Redoma de Petare (+58 212-2567788)\n\n"
                    "📶 Todos cuentan con excelente cobertura *Movilnet 4GMAX* para realizar tus pagos con Pago Móvil C2P o Biopago de inmediato."
                )
            else:
                reply = (
                    "🛒 *Supermercados Cercanos en la Zona (Chacao / Caracas):*\n\n"
                    "• 🛒 *Automercados Plaza's Los Palos Grandes:* 3ra Transversal con Av. Andrés Bello (+58 212-2856600)\n"
                    "• 🛒 *Excelsior Gama Plus Santa Eduvigis:* Av. Francisco de Miranda (+58 212-2864433)\n"
                    "• 🛒 *Central Madeirense Chacao:* Av. Libertador con Calle Elice (+58 212-2633344)\n\n"
                    "📶 Con cobertura óptima 4GMAX para realizar tus transacciones y pagos móviles C2P sin demoras."
                )

        # 16.2 Librerías, Papelerías, Libros y Útiles Escolares
        elif any(k in msg_clean for k in ["libreria", "librería", "papeleria", "papelería", "libros", "utiles", "cuadernos"]):
            if any(z in msg_clean for z in ["marques", "el marques", "el marqués", "lider", "líder", "urbina", "la urbina", "petare", "sucre", "boleita"]):
                reply = (
                    "📚 *Librerías y Papelerías en El Marqués, La California y Sucre:*\n\n"
                    "• 📚 *Tecni-Ciencia Libros C.C. Líder:* Nivel Plaza Miranda, Centro Comercial Líder, Av. Francisco de Miranda (+58 212-2380123)\n"
                    "• 📚 *Librería Nacho Unicentro El Marqués:* C.C. Unicentro El Marqués, Planta Baja, Local 12 (+58 212-2710044)\n"
                    "• 📚 *Librería Las Novedades Boleíta:* C.C. Boleíta Center, Nivel Feria (+58 212-2395566)\n\n"
                    "📶 Cuentan con óptima cobertura *Movilnet 4GMAX* para consultas y pagos móviles interbancarios C2P."
                )
            else:
                reply = (
                    "📚 *Librerías en Chacao y Este de Caracas:*\n\n"
                    "• 📚 *Tecni-Ciencia Libros Sambil:* C.C. Sambil Chacao, Nivel Acuario (+58 212-2631144)\n"
                    "• 📚 *Librería El Buscón:* C.C. Paseo Las Mercedes, Nivel Trasnocho (+58 212-9937846)\n\n"
                    "📶 Conectadas a la red Movilnet 4GMAX."
                )

        # 16.3 Puntos de Referencia y Cobertura en Petare, La Urbina, El Marqués y Sucre
        elif any(k in msg_clean for k in ["petare", "la urbina", "urbina", "el marques", "el marqués", "marques", "palo verde", "sucre", "la california"]):
            reply = (
                "📍 *Puntos de Referencia y Cobertura en Municipio Sucre (Petare / La Urbina / El Marqués):*\n\n"
                "En todo el eje este del Municipio Sucre cuentas con cobertura modernizada *Movilnet 4GMAX* y acceso a:\n\n"
                "• 🏢 *Zona Comercial La Urbina:* Calles 1 a 3A con amplia red de bancos, supermercados y farmacias.\n"
                "• 🛍️ *Centros Comerciales:* C.C. Líder (La California), C.C. Unicentro El Marqués y C.C. Boleíta Center.\n"
                "• 🚇 *Acceso Metro:* Estaciones Petare, Palo Verde y La California (Línea 1).\n"
                "• 🏥 *Servicios de Salud:* Hospital Dr. Domingo Luciani (El Llanito) y clínicas de la zona.\n\n"
                "📶 Con tu línea 4GMAX puedes navegar, usar apps de transporte y realizar Pago Móvil C2P con total rapidez. ¿Deseas consultar tu saldo o plan antes de desplazarte?"
            )

        # 16.5 Recomendaciones Gastronómicas Hiperlocales (Radio 500m) con Factor Humano y Continuidad
        elif (is_asking_recommendation or had_hunger_or_food_recently) and is_in_palos_grandes and (is_asking_recommendation or any(k in msg_clean for k in ["comer", "comida", "hambre", "plaza", "donde", "recomiendas"])):
            reply = (
                "¡Excelente punto! Justo alrededor de la *Plaza Los Palos Grandes (3ra Avenida)* cuentas con opciones gastronómicas y cafeterías emblemáticas a menos de 5 minutos a pie (menos de 300 metros):\n\n"
                "• ☕ *Café Arábica:* Justo al cruzar frente a la plaza (3ra Avenida). Reconocido por sus cafés de origen artesanal, sándwiches gourmet y repostería.\n"
                "• 🥐 *Pastelería Saint Honoré:* A 150 metros hacia la Av. Andrés Bello con 1ra Transversal. Famosa por sus hojaldres franceses, postres y comida ligera.\n"
                "• 🍕 *Restaurantes y Bistrós de la 2da y 3ra Avenida:* Opciones como *El Cine*, pizzerías artesanales y heladerías a pocos pasos del parque.\n\n"
                "📱 *Ventajas y Soporte Movilnet 4GMAX:*\n"
                "• Puedes desplazarte a pie consultando tu ruta en Google Maps en tiempo real con la velocidad de nuestra red 4GMAX.\n"
                "• En todos estos comercios puedes cancelar tu consumo de forma rápida mediante *Pago Móvil C2P interbancario*.\n\n"
                "¿Deseas verificar tu saldo disponible o prefieres que coordinemos tu cambio a Movilnet con tu eSIM digital y 10 GB de bienvenida?"
            )
        elif (is_asking_recommendation or had_hunger_or_food_recently) and is_in_altamira and (is_asking_recommendation or any(k in msg_clean for k in ["comer", "comida", "hambre", "plaza", "donde", "recomiendas"])):
            reply = (
                "¡Muy buena ubicación! Alrededor de la *Plaza Altamira (Plaza Francia)* tienes excelentes opciones a menos de 500 metros caminando:\n\n"
                "• ☕ *Cafeterías y Bistrós de la Av. San Juan Bosco:* Varios locales con café gourmet, pastas y sándwiches a 2 cuadras al norte.\n"
                "• 🍕 *Locales de la Av. Luis Roche:* Pizzerías tradicionales, delis y heladerías a pocos minutos a pie.\n"
                "• 🌭 *Carritos Tradicionales de Altamira Sur:* En la salida sur de la plaza hacia la Av. Francisco de Miranda, clásicos para comida rápida.\n\n"
                "📱 *Conectividad Movilnet 4GMAX:*\n"
                "• Navega sin interrupciones y paga directamente con *Pago Móvil C2P* desde tu celular.\n\n"
                "¿Te gustaría consultar tu saldo o activar tu eSIM 4GMAX con 10 GB de bono de bienvenida?"
            )
        elif (is_asking_recommendation or ("para ir a comer" in msg_clean or "donde comer" in msg_clean)) and had_hunger_or_food_recently:
            reply = (
                "🍽️ En el Municipio Chacao cuentas con dos de los mejores ejes gastronómicos a pie con total cobertura *Movilnet 4GMAX*:\n\n"
                "1. 🌳 *Eje Los Palos Grandes (Plaza 3ra Av):* Cafeterías de autor (Café Arábica), pastelerías (Saint Honoré) y bistrós gourmet.\n"
                "2. 🛍️ *Eje Sambil Chacao / Av. Libertador:* Amplia feria de comida internacional, restaurantes y heladerías.\n\n"
                "💡 Puedes llegar fácilmente caminando guiándote con mapas en tu móvil. En todos los comercios puedes pagar de inmediato con *Pago Móvil C2P interbancario*.\n\n"
                "¿En cuál de estas dos zonas te encuentras o deseas verificar tu saldo antes de salir?"
            )

        # 17. Ubicación, Zonas Urbanas, Transporte y Puntos en Chacao
        elif any(k in msg_clean for k in ["chacao", "altamira", "palos grandes", "el rosal", "sambil", "metro", "como llegar", "donde queda", "donde esta", "ubicacion", "direccion"]) and not any(d in msg_clean for d in ["oferta", "ofertas", "descuento", "descuentos", "promocion", "promociones", "cupon", "cupones"]):
            reply = (
                "📍 *Puntos de Referencia y Cobertura en Chacao / Caracas:*\n\n"
                "En el Municipio Chacao cuentas con cobertura total *Movilnet 4GMAX* y acceso rápido a:\n\n"
                "• 🏢 *Sede Corporativa Movilnet:* Av. Venezuela, Torre Movilnet, Urb. El Rosal, Chacao.\n"
                "• 🛍️ *Centro Comercial Sambil Chacao:* Av. Libertador con calle Los Ángeles (con múltiples comercios, bancos y taquillas).\n"
                "• 🚇 *Acceso Metro:* Estaciones Chacao y Altamira (Línea 1).\n\n"
                "💡 *Recomendación:* Con tus datos móviles activos puedes navegar en Google Maps o Waze sin interrupciones. ¿Te gustaría consultar tu saldo o plan antes de salir?"
            )

        # 18. Helados, Antojos, Comida y Gastronomía
        elif any(k in msg_clean for k in ["helado", "heladeria", "dulce", "postre", "hambre", "comer", "comida", "almuerzo", "cena", "desayuno", "restaurante", "arepa", "empanada", "cafe", "cafeteria"]):
            reply = (
                "🍦 ¡Un helado o un buen café siempre es una excelente idea!\n\n"
                "En la zona comercial de Chacao tienes excelentes opciones como en el *Centro Comercial Sambil Chacao* o en los locales y cafeterías de *Los Palos Grandes*.\n\n"
                "📱 Con tu línea *Movilnet 4GMAX* puedes buscar las mejores heladerías en redes sociales, ordenar por delivery o pagar directamente con Pago Móvil C2P interbancario.\n\n"
                "¿Deseas verificar tu saldo en bolívares para saber cuánto tienes disponible?"
            )

        # 19. Pregunta sobre Robots o Asistente Digital
        elif any(w in words for w in ["robot", "maquina", "ia", "humano"]) or ("inteligencia artificial" in msg_clean):
            reply = (
                "Soy MOVI, tu asistente digital oficial con inteligencia artificial de Telecomunicaciones Movilnet C.A. "
                "Mi objetivo es responderte de forma ágil, natural y transparente. Cuéntame, ¿en qué te puedo colaborar hoy?"
            )

        # 19.1 Consultas de Saldo, Megas o Facturación en Fallback
        elif any(k in msg_clean for k in ["saldo", "mi saldo", "cuanto tengo", "cuanto debo", "megas", "datos", "gigas", "navegacion", "balance"]):
            is_comp = False
            carrier_label = "Línea Externa"
            carrier_val = "unknown"
            clean_tel = msisdn or ""
            try:
                from core.carrier_funnel_classifier import CarrierFunnelClassifier, Carrier
                clean_tel = CarrierFunnelClassifier.clean_msisdn(msisdn or "")
                carrier_enum, carrier_label, is_comp = CarrierFunnelClassifier.identify_carrier(clean_tel)
                carrier_val = carrier_enum.value.lower()
            except Exception:
                pass

            is_pwa = str(channel or "").lower() in ["pwa", "pwa_mobile", "web", "pwa_stitch", "pwa_web", "mobile_pwa", "pwa_data"]
            base_pwa_url = os.environ.get("MOVILNET_PUBLIC_PWA_URL", "https://one21026-ids-movilnet-pwa.onrender.com").rstrip("/")
            if is_comp and clean_tel:
                carrier_name = "Movistar" if "movistar" in carrier_label.lower() else ("Digitel" if "digitel" in carrier_label.lower() else "tu operadora actual")
                token_hex = uuid.uuid4().hex[:8]
                pwa_promo = ""
                if not is_pwa:
                    pwa_promo = (
                        f"\n\n🎁 Tienes acceso a 1,000 tokens de prueba (máx. 3 consultas/mes) para interactuar con nuestra IA: "
                        f"{base_pwa_url}/ui/pwa_stitch/index.html?carrier={carrier_val}&phone={clean_tel}&token={token_hex}"
                    )
                reply = (
                    f"👋 ¡Hola! Te damos una cordial bienvenida a *Movilnet 4GMAX*.\n\n"
                    f"Identificamos que te comunicas desde tu línea {carrier_label} (`{clean_tel}`). "
                    f"Por regulaciones de telecomunicaciones de CONATEL y resguardo de privacidad entre operadores, "
                    f"como canal oficial de Movilnet no tenemos acceso a consultar los saldos ni datos de {carrier_name}.\n\n"
                    f"🚀 *¡Aprovecha y cámbiate a Movilnet 4GMAX manteniendo tu mismo número!*\n"
                    f"• ✨ *eSIM Digital:* Activación inmediata sin chip físico.\n"
                    f"• 🎁 *Bono de Bienvenida:* 10 GB de datos libres.\n"
                    f"• 💵 *Tarifas Solidarias:* Ahorra hasta un 60% frente a lo que pagas en {carrier_name}."
                    f"{pwa_promo}"
                )
            else:
                pwa_promo = ""
                if not is_pwa:
                    pwa_promo = f"\n\n🌐 También puedes acceder a nuestra PWA oficial con autoservicio interactivo: {base_pwa_url}/ui/pwa_stitch/index.html"
                reply = (
                    "📱 *Consulta de Saldo y Servicios Movilnet 4GMAX*\n\n"
                    "Para verificar tu línea en tiempo real con latencia cero:\n"
                    "• Escribe *'Saldo'* para consultar tu balance disponible, fecha de corte y estatus.\n"
                    "• Escribe *'Megas'* para ver tu cupo de navegación y consumo de datos.\n"
                    "• Escribe *'Recarga'* para recargar al instante mediante Pago Móvil C2P."
                    f"{pwa_promo}"
                )

        # 19.2 Aclaratoria o Pregunta de Justificación ("¿Por qué?", "a qué se debe")
        elif any(k in msg_clean for k in ["porque", "por que", "a que se debe", "por que no"]):
            reply = (
                "Te explico con todo gusto: En Venezuela, cada operadora de telecomunicaciones (Movilnet, Digitel y Movistar) "
                "mantiene sus plataformas de facturación, tasación OCS y saldos de manera estrictamente independiente "
                "bajo normativas de CONATEL y protección al abonado.\n\n"
                "Desde este canal oficial de Movilnet podemos gestionar con máxima rapidez todo lo correspondiente a líneas 0416 y 0426. "
                "Si utilizas una línea de otra empresa, no tenemos visibilidad técnica de tus saldos externos, pero con gusto te ayudamos "
                "a realizar tu portabilidad hacia Movilnet 4GMAX para que disfrutes de nuestras tarifas solidarias y cobertura nacional."
            )

        # 19.3 Aclaratoria de Pertenencia ("pero estoy en movilnet", "soy movilnet", "mi linea es movilnet")
        elif any(k in msg_clean for k in ["estoy en movilnet", "soy movilnet", "es movilnet", "tengo movilnet", "linea movilnet", "pero soy movilnet"]):
            reply = (
                "¡Comprendido perfectamente! Si tu línea pertenece a Movilnet (0416 o 0426) o si realizaste portabilidad hacia nuestra red, "
                "por favor indícanos tu número celular completo (por ejemplo: `0416-1234567` o `0426-1234567`) o tu número de cédula de identidad.\n\n"
                "Con ese dato consultaremos de inmediato tu expediente en nuestra plataforma OCS para verificar tu saldo, megas y plan en tiempo real."
            )

        # 20. Respuesta abierta empática inteligente MOVI (Anti-Bucle Competidores)
        else:
            is_comp = False
            carrier_label = "Línea Móvil"
            clean_tel = msisdn or ""
            try:
                from core.carrier_funnel_classifier import CarrierFunnelClassifier, Carrier
                clean_tel = CarrierFunnelClassifier.clean_msisdn(msisdn or "")
                carrier_enum, carrier_label, is_comp = CarrierFunnelClassifier.identify_carrier(clean_tel)
            except Exception:
                pass

            is_greeting = any(g in msg_clean for g in [
                "hola", "buenos dias", "buenas tardes", "buenas noches", "saludos",
                "inicio", "empezar", "comenzar", "buen dia", "hey", "epale", "aloe"
            ]) or (len(msg_clean) <= 4 and msg_clean in ["hi", "alo", "oye", "oe"])

            if is_comp and clean_tel:
                if is_greeting:
                    reply = (
                        f"¡Hola! Soy MOVI, tu asistente virtual de *Movilnet 4GMAX*. "
                        f"Veo que nos escribes desde una línea {carrier_label} ({clean_tel}). "
                        f"Con gusto te puedo orientar sobre nuestra cobertura 4GMAX en toda Venezuela, "
                        f"los requisitos para activar una eSIM digital, nuestro catálogo de planes Inteliplan o cómo portar tu número actual conservando tus dígitos. "
                        f"¿En qué te puedo asesorar el día de hoy?"
                    )
                else:
                    reply = (
                        f"Entendido. Con mucho gusto te oriento desde *Movilnet 4GMAX*. "
                        f"Identifico que tu línea actual pertenece a {carrier_label} ({clean_tel}). "
                        f"Puedo apoyarte con información de nuestra cobertura nacional 4GMAX, puntos comerciales, o coordinar el cambio a Movilnet con tu mismo número y 10 GB de bienvenida. "
                        f"¿Podrías indicarme con un poco más de detalle qué trámite, ubicación o consulta deseas realizar?"
                    )
            else:
                if is_greeting:
                    reply = (
                        "¡Hola! Soy MOVI, tu asistente virtual de *Movilnet 4GMAX*. Con total gusto te acompaño. "
                        "Puedo orientarte sobre planes comerciales, consultar tu saldo disponible y consumo de megas en tiempo real, "
                        "guiarte en recargas Pago Móvil C2P, ubicar oficinas de atención o resolver dudas de tu línea. "
                        "Cuéntame con total confianza, ¿en qué te puedo colaborar en este momento?"
                    )
                else:
                    reply = (
                        "Comprendido. Como asistente oficial de *Movilnet 4GMAX* estoy aquí para ayudarte con cualquier gestión de tu línea "
                        "(saldo, megas, planes, recargas C2P o soporte técnico), así como orientarte sobre puntos de atención o cobertura. "
                        "¿Podrías especificarme un poco más tu consulta para darte una respuesta exacta?"
                    )

        # Simulación analítica de tokens para telemetría
        input_tokens = len(message.split()) + 45
        output_tokens = len(reply.split()) + 15
        total_tokens = input_tokens + output_tokens
        simulated_cost = (input_tokens * 0.000000075) + (output_tokens * 0.000000300)

        return reply, total_tokens, round(simulated_cost, 6)


def _run_self_tests() -> None:
    """Auto-verificación formal del motor LLM y Razonador Semántico de Contingencia (Pilar II y V)."""
    print("=" * 80)
    print("🧪 [TEST]: Auto-verificación de core/llm_reasoning_engine.py")
    print("=" * 80)

    engine = LLMReasoningEngine()

    # 1. Test Ubicación Haversine
    geo_ccs = engine._get_location_and_weather(10.4806, -66.9036, fetch_live_weather=False)
    assert "Caracas (Distrito Capital)" in geo_ccs
    geo_mcbo = engine._get_location_and_weather(10.6427, -71.6125, fetch_live_weather=False)
    assert "Maracaibo (Zulia)" in geo_mcbo
    print("  [PASS] Georreferenciación Haversine venezolana validada.")

    # 2. Test Construcción de System Context y Guardrails
    ctx = engine._build_system_context(
        latitude=10.4806,
        longitude=-66.9036,
        device_info={"device_type": "Smartphone", "os_family": "Android", "is_touch": True, "screen_resolution": "1080x2400"},
        msisdn="04161234567",
        sender_name="Ismael",
        fetch_live_weather=False
    )
    assert "Ismael" in ctx
    assert "Regla Inviolable de Identidad" in ctx
    assert "Smartphone (Android, Pantalla Táctil" in ctx
    print("  [PASS] Construcción de System Prompt enriquecido y Guardrails Anti-Alucinación validada.")

    # 3. Test Razonador Semántico Determinista (Zero-Token Fallback)
    r_help, toks, cost = engine._semantic_fallback_reasoner("En que me puedes ayudar?", [])
    assert "Mi Movilnet" in r_help
    assert toks > 0 and cost >= 0.0

    r_esim, _, _ = engine._semantic_fallback_reasoner("Como solicito una esim?", [])
    assert "eSIM" in r_esim

    r_greet, _, _ = engine._semantic_fallback_reasoner("Hola buenas tardes", [])
    assert "Movilnet 4GMAX" in r_greet

    r_comp, _, _ = engine._semantic_fallback_reasoner("Deseo consultar informacion general", [], msisdn="04141234567")
    assert "04141234567" in r_comp
    print("  [PASS] Razonador Semántico Local (Ayuda, eSIM, Saludo, Funnel Competidor) 100% operativo.")

    print("=" * 80)
    print("🏆 [RESULTADO]: 100% PASS (0 fallos en Motor de Razonamiento LLM)")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Motor de Razonamiento LLM y Contingencia Semántica")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación formal del módulo")
    args = parser.parse_args()

    if args.test or len(sys.argv) == 1:
        _run_self_tests()
