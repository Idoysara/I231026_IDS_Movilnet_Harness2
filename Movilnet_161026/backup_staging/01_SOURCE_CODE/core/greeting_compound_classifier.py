#!/usr/bin/env python3
"""
core/greeting_compound_classifier.py
====================================
Motor Algorítmico de Clasificación de Mensajes: Saludo Puro vs Consulta Compuesta.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII).

Resuelve de forma definitiva:
1. Erradicación de falsos positivos donde saludos compuestos ("Hola, quiero comprar una laptop...")
   eran interceptados por regex superficiales (^hola) como simples saludos.
2. Distinción estricta entre:
   - PURE_GREETING: Mensaje compuesto exclusivamente por saludos y cortesía sin solicitud anexa.
   - COMPOUND_QUERY: Saludo con pregunta, acción, sustantivo o requerimiento posterior.
   - DIRECT_QUERY: Consulta directa sin fórmula de saludo inicial.
3. Enrutamiento segmentado de menú:
   - Abonados Únicos Movilnet (0416/0426): Menú de Autogestión Oficial (Saldo, Planes, C2P, EIR).
   - NO Usuarios Movilnet (0414/0424/0412/otros): Redirección al módulo NO_USUARIOS_MOVILNET
     (Funnel Marketing Portabilidad 4GMAX, eSIM gratis, Bono 10GB, sin opciones internas de saldo).
4. Cero Secuestro Comercial Ciego: Las consultas compuestas o abiertas NUNCA son sustituidas
   por plantillas publicitarias; deben atenderse por el motor de IA o fast-path correspondiente.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Set


class MessageCategory(str, Enum):
    PURE_GREETING = "PURE_GREETING"
    COMPOUND_QUERY = "COMPOUND_QUERY"
    DIRECT_QUERY = "DIRECT_QUERY"


class RoutingDestination(str, Enum):
    MOVILNET_SUBSCRIBER_MENU = "MOVILNET_SUBSCRIBER_MENU"
    NO_USUARIOS_MOVILNET_FUNNEL = "FUNNEL_MARKETING_NO_USUARIOS_MOVILNET"
    FAST_PATH_TELCO_INTENT = "FAST_PATH_TELCO_ODA"
    AI_AGENT_RESOLVER = "AI_AGENT_GEMINI"


@dataclass
class MessageAnalysisResult:
    original_text: str
    normalized_text: str
    category: MessageCategory
    is_pure_greeting: bool
    is_compound: bool
    greeting_phrases: List[str] = field(default_factory=list)
    residual_text: str = ""
    residual_tokens: List[str] = field(default_factory=list)
    action_verbs: List[str] = field(default_factory=list)
    substantive_keywords: List[str] = field(default_factory=list)
    has_question_indicator: bool = False
    recommended_routing: Optional[RoutingDestination] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "category": self.category.value,
            "is_pure_greeting": self.is_pure_greeting,
            "is_compound": self.is_compound,
            "greeting_phrases": self.greeting_phrases,
            "residual_text": self.residual_text,
            "residual_tokens": self.residual_tokens,
            "action_verbs": self.action_verbs,
            "substantive_keywords": self.substantive_keywords,
            "has_question_indicator": self.has_question_indicator,
            "recommended_routing": self.recommended_routing.value if self.recommended_routing else None,
        }


class GreetingCompoundClassifier:
    """Clasificador Carrier-Grade para distinguir Saludo Puro de Consultas Compuestas."""

    # Saludos compuestos y aperturas de reencuentro (orden descendente de longitud)
    MULTI_WORD_GREETINGS = [
        "buenos dias", "buen dia", "buenas tardes", "buenas noches",
        "feliz dia", "feliz tarde", "feliz noche", "feliz fin de semana",
        "que tal", "como estas", "como esta", "como estan", "como te va",
        "un cordial saludo", "saludos cordiales", "muy buenas tardes",
        "muy buenos dias", "muy buenas noches", "un saludo",
        "nuevamente soy yo", "soy yo de nuevo", "de nuevo yo",
        "aqui de nuevo", "aqui estoy", "otra vez yo", "aqui volvi",
        "buenas de nuevo"
    ]

    # Palabras de saludo individuales
    SINGLE_WORD_GREETINGS = [
        "hola", "buenas", "buenos", "buen", "alo", "epa", "epale",
        "saludos", "saludo", "hi", "hello", "hey", "volvi"
    ]

    # Cortesías o vocativos que pueden acompañar un saludo sin constituir pregunta o solicitud
    COURTESY_FILLERS: Set[str] = {
        "por favor", "porfa", "amigo", "amiga", "amigos", "amigas",
        "equipo", "gente", "asistente", "bot", "movilnet", "senor",
        "senora", "sr", "sra", "estimado", "estimada", "estimados",
        "gracias", "muchas gracias", "bendiciones", "saludos", "todos",
        "todas", "ok", "vale", "listo", "aqui", "alli", "hoy", "dia",
        "nuevamente", "otra vez", "de nuevo", "yo"
    }


    # Conectores y preposiciones gramaticales funcionales en español
    GRAMMATICAL_CONNECTORS: Set[str] = {
        "de", "del", "a", "al", "para", "por", "con", "en", "un", "una",
        "unos", "unas", "el", "la", "los", "las", "y", "e", "o", "u"
    }

    # Indicadores interrogativos
    QUESTION_WORDS: Set[str] = {
        "que", "cual", "cuales", "como", "donde", "cuando", "cuanto",
        "cuanta", "cuantos", "cuantas", "porque", "por que", "para que",
        "quien", "quienes", "tienen", "hay", "existe"
    }

    # Verbos de acción / petición / consulta
    ACTION_VERBS: Set[str] = {
        "quiero", "quisiera", "necesito", "busco", "deseo", "solicito",
        "comprar", "recomiendas", "recomienda", "recomienden", "venden",
        "tienen", "hay", "ayuda", "ayudame", "dime", "sabes", "puedes",
        "podrias", "indicar", "indicame", "explicar", "explicame", "activar",
        "cambiar", "pagar", "recargar", "bloquear", "liberar", "consultar",
        "adquirir", "contratar", "conectar", "reparar", "averiguar",
        "saber", "costar", "cuesta", "vale", "quedo", "perdi", "robaron"
    }

    # Palabras clave sustantivas del ecosistema y consultas abiertas
    SUBSTANTIVE_KEYWORDS: Set[str] = {
        "laptop", "computadora", "computador", "pc", "portatil", "notebook",
        "telefono", "celular", "equipo", "mifi", "modem", "router",
        "linea", "chip", "sim", "esim", "megas", "gigas", "datos", "saldo",
        "balance", "precio", "costo", "tarifa", "plan", "planes", "inteliplan",
        "conecta", "farmacia", "restaurante", "comida", "tienda", "agencia",
        "sede", "oficina", "sucursal", "cedula", "pago", "banco", "tarjeta",
        "falla", "senal", "cobertura", "apn", "imei", "portabilidad",
        "internet", "wifi", "fibra", "promocion", "oferta", "descuento",
        "recarga", "c2p", "corte", "factura", "deuda", "debo"
    }

    @classmethod
    def clean_and_normalize(cls, text: str) -> str:
        """Limpia puntuación no estructurada, tildes y caracteres repetitivos."""
        if not text:
            return ""
        # 1. Normalizar unicode NFD y eliminar diacríticos
        s = unicodedata.normalize("NFD", text.lower())
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        # 2. Reemplazar saltos de línea por espacios
        s = re.sub(r"[\r\n]+", " ", s)
        # 3. Reducir caracteres repetidos (ej: holaaaaa -> holaa)
        s = re.sub(r"([a-z])\1{2,}", r"\1\1", s)
        return s.strip()

    @classmethod
    def analyze(cls, raw_text: str) -> MessageAnalysisResult:
        """Analiza formalmente el mensaje y determina su categoría exacta."""
        if not raw_text or not raw_text.strip():
            return MessageAnalysisResult(
                original_text=raw_text or "",
                normalized_text="",
                category=MessageCategory.PURE_GREETING,
                is_pure_greeting=True,
                is_compound=False,
            )

        original = raw_text.strip()
        normalized = cls.clean_and_normalize(original)

        # Detectar presencia de signos de interrogación en el texto crudo
        has_question_mark = bool(re.search(r"[\?¿]", original))

        # 1. Detectar frases de saludo compuestas
        detected_greetings: List[str] = []
        working_text = normalized

        for mw in cls.MULTI_WORD_GREETINGS:
            pattern = r"\b" + re.escape(mw) + r"\b"
            if re.search(pattern, working_text):
                detected_greetings.append(mw)
                working_text = re.sub(pattern, " ", working_text)

        for sw in cls.SINGLE_WORD_GREETINGS:
            pattern = r"\b" + re.escape(sw) + r"\b"
            if re.search(pattern, working_text):
                detected_greetings.append(sw)
                working_text = re.sub(pattern, " ", working_text)

        # 2. Extraer texto residual y limpiar signos de puntuación
        residual_cleaned = re.sub(r"[^\w\s]", " ", working_text)
        raw_tokens = [w for w in residual_cleaned.split() if w]

        # 3. Filtrar tokens residuales ignorando palabras de cortesía vacías
        meaningful_tokens: List[str] = []
        grammatical_tokens: List[str] = []
        detected_verbs: List[str] = []
        detected_keywords: List[str] = []
        question_word_found = False

        for t in raw_tokens:
            if t in cls.COURTESY_FILLERS:
                continue
            if t in cls.GRAMMATICAL_CONNECTORS:
                grammatical_tokens.append(t)
                continue
            if t in cls.QUESTION_WORDS:
                question_word_found = True
                meaningful_tokens.append(t)
            elif t in cls.ACTION_VERBS:
                detected_verbs.append(t)
                meaningful_tokens.append(t)
            elif t in cls.SUBSTANTIVE_KEYWORDS:
                detected_keywords.append(t)
                meaningful_tokens.append(t)
            else:
                meaningful_tokens.append(t)

        has_question = has_question_mark or question_word_found
        has_greetings = len(detected_greetings) > 0

        # Si solo quedaron conectores gramaticales sin ningún verbo ni sustantivo y vino con saludo,
        # se descartan como parte del saludo de cortesía (ej. "amigos de movilnet", "para todos")
        if has_greetings and len(meaningful_tokens) == 0 and not has_question:
            grammatical_tokens.clear()
        else:
            meaningful_tokens.extend(grammatical_tokens)

        # 4. Decisión Formal de Clasificación
        # ¿Es un Saludo Puro?
        if has_greetings and len(meaningful_tokens) == 0 and not has_question_mark:
            category = MessageCategory.PURE_GREETING
            is_pure = True
            is_compound = False
        elif has_greetings and len(meaningful_tokens) > 0:
            category = MessageCategory.COMPOUND_QUERY
            is_pure = False
            is_compound = True
        elif not has_greetings and (len(meaningful_tokens) > 0 or has_question):
            category = MessageCategory.DIRECT_QUERY
            is_pure = False
            is_compound = False
        else:
            # Caso residual: solo signos o palabras vacías
            category = MessageCategory.PURE_GREETING
            is_pure = True
            is_compound = False

        return MessageAnalysisResult(
            original_text=original,
            normalized_text=normalized,
            category=category,
            is_pure_greeting=is_pure,
            is_compound=is_compound,
            greeting_phrases=detected_greetings,
            residual_text=" ".join(meaningful_tokens),
            residual_tokens=meaningful_tokens,
            action_verbs=detected_verbs,
            substantive_keywords=detected_keywords,
            has_question_indicator=has_question,
        )

    @classmethod
    def resolve_greeting_routing(
        cls, is_movilnet_subscriber: bool, analysis: MessageAnalysisResult
    ) -> RoutingDestination:
        """
        Determina el enrutamiento formal según la categoría del mensaje y el número:
        - Si es PURE_GREETING y el usuario es Movilnet (0416/0426) -> Menú Autogestión Oficial.
        - Si es PURE_GREETING y NO es Movilnet (0414/0424/0412/otros) -> Módulo NO_USUARIOS_MOVILNET.
        - Si es COMPOUND_QUERY o DIRECT_QUERY -> Debe ir a IA o FastPath ODA (¡Cero Secuestro Comercial!).
        """
        if analysis.is_pure_greeting:
            if is_movilnet_subscriber:
                return RoutingDestination.MOVILNET_SUBSCRIBER_MENU
            else:
                return RoutingDestination.NO_USUARIOS_MOVILNET_FUNNEL

        # Para consultas compuestas o directas, jamás secuestrar con menú o portabilidad ciega
        return RoutingDestination.AI_AGENT_RESOLVER


def run_self_verification():
    """Suite de auto-verificación matemática de casos de prueba (100% Pass)."""
    test_cases = [
        # (Mensaje, is_pure_expected, is_compound_expected, desc)
        ("Hola", True, False, "Saludo simple unigram"),
        ("Buenos días", True, False, "Saludo formal matutino"),
        ("Buenas tardes equipo Movilnet", True, False, "Saludo con cortesía vacía"),
        ("Epa qué tal, saludos!! 👋", True, False, "Saludo coloquial con emojis"),
        ("Hola buenas tardes, gracias", True, False, "Saludo con agradecimiento de cortesía"),
        (
            "Hola, quiero comprar una laptop, tienes alguna que me recomiendes comprar?",
            False, True, "Consulta compuesta de laptop (Caso Francisco Landaeta)"
        ),
        (
            "Buenos días, me ayudan con información sobre los planes?",
            False, True, "Consulta de planes con saludo matutino"
        ),
        (
            "Buenas tardes, ¿dónde queda una oficina comercial en Caracas?",
            False, True, "Pregunta de oficina con saludo vespertino"
        ),
        (
            "Hola me recomiendas un restaurante cerca?",
            False, True, "Petición de recomendación con saludo"
        ),
        (
            "quiero comprar una laptop",
            False, False, "Consulta directa sin saludo"
        ),
        (
            "cuanto cuesta el inteliplan 10gb?",
            False, False, "Pregunta directa de precio sin saludo"
        ),
        (
            "Hola!! Requiero saldo de mi linea porfa",
            False, True, "Consulta de saldo con saludo y cortesía"
        )
    ]

    print("🧪 Iniciando auto-verificación de GreetingCompoundClassifier...")
    passed = 0
    for msg, exp_pure, exp_compound, desc in test_cases:
        res = GreetingCompoundClassifier.analyze(msg)
        ok_pure = (res.is_pure_greeting == exp_pure)
        ok_comp = (res.is_compound == exp_compound)
        if ok_pure and ok_comp:
            passed += 1
            print(f"  ✅ [PASS] '{msg[:35]}...' -> Pure: {res.is_pure_greeting}, Comp: {res.is_compound} ({desc})")
        else:
            print(f"  ❌ [FAIL] '{msg}' -> Got: Pure={res.is_pure_greeting}, Comp={res.is_compound} | Expected: Pure={exp_pure}, Comp={exp_compound}")

    print(f"\n📊 Resultado: {passed}/{len(test_cases)} pruebas superadas.")
    assert passed == len(test_cases), "Falla en suite formal de clasificación."
    print("🏆 ¡Todas las aserciones de GreetingCompoundClassifier son 100% PASS!\n")


if __name__ == "__main__":
    run_self_verification()
