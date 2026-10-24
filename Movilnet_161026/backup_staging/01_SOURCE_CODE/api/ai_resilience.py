"""
Módulo de Resiliencia, Diagnóstico y Auto-Recuperación de Modelos de Inteligencia Artificial
Telecomunicaciones Movilnet C.A. — Architecture Carrier-Grade
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("MovilnetAIResilience")


class AIIncidentType(str, Enum):
    HTTP_429_RATE_LIMIT = "HTTP_429_RATE_LIMIT"
    HTTP_401_AUTH_EXPIRED = "HTTP_401_AUTH_EXPIRED"
    HTTP_403_FORBIDDEN = "HTTP_403_FORBIDDEN"
    HTTP_500_SERVER_ERROR = "HTTP_500_SERVER_ERROR"
    HTTP_503_SERVICE_UNAVAILABLE = "HTTP_503_SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    PARSE_ERROR = "PARSE_ERROR"
    REPETITIVE_ROBOT_LOOP = "REPETITIVE_ROBOT_LOOP"
    UNKNOWN = "UNKNOWN"


class ResolutionAction(str, Enum):
    ROTATE_MODEL = "ROTATE_MODEL"
    SWITCH_PROVIDER = "SWITCH_PROVIDER"
    DYNAMIC_SEMANTIC_REASONER = "DYNAMIC_SEMANTIC_REASONER"
    EXPONENTIAL_BACKOFF = "EXPONENTIAL_BACKOFF"
    RETRY_WITH_TOKEN_PRUNING = "RETRY_WITH_TOKEN_PRUNING"


@dataclass
class IncidentDiagnosis:
    incident_type: AIIncidentType
    error_message: str
    failed_model: Optional[str]
    failed_provider: Optional[str]
    recommended_action: ResolutionAction
    alternative_models: List[str]
    human_explanation: str
    remediation_metadata: Dict[str, Any] = field(default_factory=dict)


class AIResilienceEngine:
    """
    Catálogo y Motor Diagnóstico Inmediato de Fallas en LLMs / APIs Cognitivas.
    Mapea causas raíz a soluciones ejecutables en tiempo real sin caer en bucles repetitivos.
    """

    KNOWLEDGE_BASE = {
        AIIncidentType.HTTP_429_RATE_LIMIT: {
            "root_cause": "Saturación de peticiones por minuto (RPM) o tokens por minuto (TPM) en upstream pool.",
            "recommended_action": ResolutionAction.ROTATE_MODEL,
            "solution": "Conmutar de inmediato al siguiente modelo del pool resiliente sin esperar y registrar cooldown de 60s para el modelo saturado.",
            "models_priority": [
                "google/gemini-2.0-flash",
                "deepseek/deepseek-chat",
                "qwen/qwen-2.5-72b-instruct"
            ]
        },
        AIIncidentType.REPETITIVE_ROBOT_LOOP: {
            "root_cause": "Activación de plantilla fija o fallback determinista estático que ignora la semántica del usuario.",
            "recommended_action": ResolutionAction.DYNAMIC_SEMANTIC_REASONER,
            "solution": "Ejecutar síntesis semántica adaptativa con variables de contexto (hora, clima, coordenadas) y respuesta empática abierta sin viñetas de menú rígido.",
            "models_priority": []
        },
        AIIncidentType.TIMEOUT: {
            "root_cause": "Latencia de inferencia excedió umbral SLA (ej. > 8s por congestión de cola en LLM).",
            "recommended_action": ResolutionAction.ROTATE_MODEL,
            "solution": "Abortar socket e invocar modelo ultra-rápido de baja latencia (Flash/Turbo).",
            "models_priority": [
                "google/gemini-2.0-flash-001",
                "meta-llama/llama-3.1-8b-instruct"
            ]
        },
        AIIncidentType.HTTP_401_AUTH_EXPIRED: {
            "root_cause": "Credencial API Key expirada, inválida o revocada.",
            "recommended_action": ResolutionAction.SWITCH_PROVIDER,
            "solution": "Conmutar al proveedor secundario configurado (ej. de OpenRouter a Google AI Studio o Anthropic).",
            "models_priority": []
        },
        AIIncidentType.HTTP_503_SERVICE_UNAVAILABLE: {
            "root_cause": "Caída del clúster de inferencia o mantenimiento no programado.",
            "recommended_action": ResolutionAction.SWITCH_PROVIDER,
            "solution": "Cambiar de clúster/proveedor y reintentar.",
            "models_priority": [
                "meta-llama/llama-3.3-70b-instruct",
                "google/gemini-2.0-flash-001"
            ]
        }
    }

    @classmethod
    def diagnose(cls, error_obj: Any, current_model: Optional[str] = None, current_provider: Optional[str] = "openrouter") -> IncidentDiagnosis:
        """
        Analiza cualquier excepción, código HTTP o mensaje de error y retorna
        la diagnosis formal, modelo sugerido y acción inmediata.
        """
        err_str = str(error_obj).lower()

        if "429" in err_str or "rate limit" in err_str or "too many requests" in err_str or "rate-limited" in err_str:
            inc_type = AIIncidentType.HTTP_429_RATE_LIMIT
        elif "timed out" in err_str or "timeout" in err_str:
            inc_type = AIIncidentType.TIMEOUT
        elif "401" in err_str or "unauthorized" in err_str or "invalid api key" in err_str:
            inc_type = AIIncidentType.HTTP_401_AUTH_EXPIRED
        elif "403" in err_str or "forbidden" in err_str:
            inc_type = AIIncidentType.HTTP_403_FORBIDDEN
        elif "503" in err_str or "service unavailable" in err_str or "overloaded" in err_str:
            inc_type = AIIncidentType.HTTP_503_SERVICE_UNAVAILABLE
        elif "500" in err_str or "internal server" in err_str:
            inc_type = AIIncidentType.HTTP_500_SERVER_ERROR
        elif "repetitivo" in err_str or "robot" in err_str or "menu" in err_str:
            inc_type = AIIncidentType.REPETITIVE_ROBOT_LOOP
        else:
            inc_type = AIIncidentType.UNKNOWN

        meta = cls.KNOWLEDGE_BASE.get(inc_type, {
            "root_cause": "Error inesperado no clasificado.",
            "recommended_action": ResolutionAction.ROTATE_MODEL,
            "solution": "Reintentar con el siguiente modelo del pool seguro.",
            "models_priority": ["meta-llama/llama-3.3-70b-instruct", "qwen/qwen-2.5-72b-instruct"]
        })

        # Generar lista de alternativas excluyendo el modelo que acaba de fallar
        raw_alts = meta.get("models_priority", [
            "meta-llama/llama-3.3-70b-instruct",
            "qwen/qwen-2.5-72b-instruct",
            "google/gemini-2.0-flash-001"
        ])
        alternatives = [m for m in raw_alts if m != current_model]
        if not alternatives and raw_alts:
            alternatives = raw_alts

        human_msg = (
            f"Detectado incidente {inc_type.value}: {meta['root_cause']} "
            f"Solución aplicada: {meta['solution']}"
        )

        return IncidentDiagnosis(
            incident_type=inc_type,
            error_message=str(error_obj),
            failed_model=current_model,
            failed_provider=current_provider,
            recommended_action=meta["recommended_action"],
            alternative_models=alternatives,
            human_explanation=human_msg,
            remediation_metadata={
                "timestamp": time.time(),
                "cooldown_seconds": 60 if inc_type == AIIncidentType.HTTP_429_RATE_LIMIT else 10
            }
        )

    @classmethod
    def execute_resilient_call(cls, execute_fn, candidate_models: List[str], max_retries: int = 3) -> Tuple[Any, Optional[IncidentDiagnosis]]:
        """
        Ejecutor de orden superior con tolerancia a fallas y autorecuperación inmediata.
        """
        last_diagnosis = None
        for model in candidate_models[:max_retries]:
            try:
                result = execute_fn(model)
                return result, last_diagnosis
            except Exception as e:
                diag = cls.diagnose(e, current_model=model)
                last_diagnosis = diag
                logger.warning(f"[AI-RESILIENCE] {diag.human_explanation}. Conmutando de {model}...")
                continue

        raise RuntimeError(f"Fallo en todos los modelos del pool. Último diagnóstico: {last_diagnosis}")
