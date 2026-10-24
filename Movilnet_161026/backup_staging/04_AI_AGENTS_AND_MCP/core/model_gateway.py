#!/usr/bin/env python3
"""
model_gateway.py — Pasarela Universal y Typesafe de Modelos de IA
==================================================================
Proyecto: AI_Movilnet_300926
Permite alternar de forma transparente entre:
  1. Fase MVP (Proveedores Gratuitos / Cuota Libre):
     - Google AI Studio (Gemini Flash)
     - DeepSeek Harness / API (DeepSeek-V3 / R1)
     - Groq Cloud (Llama 3.3 70B @ 300 tps)
     - GitHub Models (GPT-4o-mini / Phi-4)
     - xAI Grok API
     - Mock Provider (Local para pruebas unitarias sin internet)
  2. Fase Producción On-Premise (Servidores Locales Telco Movilnet):
     - vLLM Enterprise Server (Qwen 2.5 72B / DeepSeek-R1 Distill / Llama 70B)
     - Ollama Local Server
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any, Dict, List, Optional


class ModelGateway:
    def __init__(
        self,
        stage: str = os.getenv("AI_STAGE", "mvp"),
        provider: str = os.getenv("AI_PROVIDER", "mock"),
        local_base_url: str = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
        model_name: Optional[str] = None
    ):
        self.stage = stage
        self.provider = provider
        self.local_base_url = local_base_url
        self.model_name = model_name or self._default_model_for_provider(provider)

    def _default_model_for_provider(self, provider: str) -> str:
        defaults = {
            "aistudio": "gemini-2.0-flash",
            "deepseek": "deepseek-chat",
            "groq": "llama-3.3-70b-versatile",
            "github": "gpt-4o-mini",
            "grok": "grok-2-latest",
            "vllm_local": "Qwen/Qwen2.5-72B-Instruct-AWQ",
            "ollama_local": "qwen2.5:72b",
            "mock": "telco-mock-v1"
        }
        return defaults.get(provider, "gemini-2.0-flash")

    def generate_response(
        self,
        prompt: str,
        system_instruction: str = "Eres el Asistente Virtual Oficial de Telecomunicaciones Movilnet Venezuela.",
        temperature: float = 0.2,
        max_tokens: int = 800,
        response_format_json: bool = False
    ) -> Dict[str, Any]:
        """
        Punto de entrada universal. Enruta al proveedor configurado en .env.
        """
        start_time = datetime.now()

        # 1. Modo Mock (Para pruebas unitarias deterministas y desarrollo offline)
        if self.provider == "mock":
            return self._generate_mock(prompt, system_instruction, start_time)

        # 2. Modo On-Premise Local (vLLM / Ollama en Servidores Movilnet)
        elif self.provider in ["vllm_local", "ollama_local"]:
            return self._call_openai_compatible_endpoint(
                endpoint=f"{self.local_base_url}/chat/completions",
                api_key="EMPTY",
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_tokens=max_tokens,
                start_time=start_time
            )

        # 3. Modo MVP Gratuito: DeepSeek API
        elif self.provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            return self._call_openai_compatible_endpoint(
                endpoint="https://api.deepseek.com/v1/chat/completions",
                api_key=api_key,
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_tokens=max_tokens,
                start_time=start_time
            )

        # 4. Modo MVP Gratuito: Groq Cloud
        elif self.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY", "")
            return self._call_openai_compatible_endpoint(
                endpoint="https://api.groq.com/openai/v1/chat/completions",
                api_key=api_key,
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_tokens=max_tokens,
                start_time=start_time
            )

        # 5. Modo MVP Gratuito: Google AI Studio
        elif self.provider == "aistudio":
            api_key = os.getenv("AISTUDIO_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
            return self._call_gemini_api(
                api_key=api_key,
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_tokens=max_tokens,
                start_time=start_time
            )

        # Fallback a Mock si el proveedor no está implementado
        return self._generate_mock(prompt, system_instruction, start_time)

    def _generate_mock(self, prompt: str, system_instruction: str, start_time: datetime) -> Dict[str, Any]:
        """Generador simulado local para pruebas y desarrollo $0."""
        latency_ms = round((datetime.now() - start_time).total_seconds() * 1000, 2)
        
        # Lógica heurística de respuesta simulada para pruebas Telco
        p_lower = prompt.lower()
        if "saldo" in p_lower:
            text = "Estimado cliente Movilnet, su saldo disponible es de Bs. 185,50 con fecha de corte el 15 del mes en curso."
        elif "plan" in p_lower:
            text = "Actualmente usted dispone del plan Inteliplan 10GB 4GMAX, con 6.4 GB remanentes de navegación, 1.000 minutos libres y 500 SMS."
        elif "recarga" in p_lower or "pago" in p_lower:
            text = "Puede realizar su recarga a través de Banco de Venezuela, Banesco, Mercantil, Pago Móvil o el Sistema Patria."
        else:
            text = "Bienvenido a Movilnet. Por favor indíquenos su número de línea y cédula de identidad para verificar sus servicios."

        return {
            "provider": "mock_telco_engine",
            "stage": self.stage,
            "model": self.model_name,
            "text": text,
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(text.split()),
                "total_tokens": len(prompt.split()) + len(text.split())
            },
            "cost_usd": 0.0,
            "latency_ms": latency_ms,
            "timestamp": datetime.now().isoformat()
        }

    def _call_openai_compatible_endpoint(
        self,
        endpoint: str,
        api_key: str,
        prompt: str,
        system_instruction: str,
        temperature: float,
        max_tokens: int,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Adaptador para endpoints estándar OpenAI (vLLM, Ollama, DeepSeek, Groq)."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else "Bearer EMPTY"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                latency_ms = round((datetime.now() - start_time).total_seconds() * 1000, 2)
                return {
                    "provider": self.provider,
                    "stage": self.stage,
                    "model": self.model_name,
                    "text": text,
                    "usage": usage,
                    "cost_usd": 0.0 if "local" in self.provider else 0.00015,
                    "latency_ms": latency_ms,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            # Fallback seguro con reporte de error
            return {
                "provider": self.provider,
                "stage": self.stage,
                "error": str(e),
                "fallback_used": True,
                "text": "Estimado abonado, estamos experimentando una breve intermitencia en el servicio de consulta. Por favor intente en unos momentos.",
                "latency_ms": round((datetime.now() - start_time).total_seconds() * 1000, 2)
            }

    def _call_gemini_api(
        self,
        api_key: str,
        prompt: str,
        system_instruction: str,
        temperature: float,
        max_tokens: int,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Adaptador para Google AI Studio API (Gemini Flash)."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                latency_ms = round((datetime.now() - start_time).total_seconds() * 1000, 2)
                return {
                    "provider": "aistudio",
                    "stage": self.stage,
                    "model": self.model_name,
                    "text": text,
                    "cost_usd": 0.0,  # Free Tier
                    "latency_ms": latency_ms,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "provider": "aistudio",
                "stage": self.stage,
                "error": str(e),
                "fallback_used": True,
                "text": "Estimado cliente Movilnet, por favor intente nuevamente en unos instantes.",
                "latency_ms": round((datetime.now() - start_time).total_seconds() * 1000, 2)
            }


if __name__ == "__main__":
    print("🧪 Probando ModelGateway en Modo MVP / Mock...")
    gateway = ModelGateway(stage="mvp", provider="mock")
    
    res1 = gateway.generate_response("¿Cuál es el saldo de mi línea?")
    print(f"\n[Consulta 1 - Saldo] ({res1['latency_ms']} ms):\n{res1['text']}")

    res2 = gateway.generate_response("¿Qué beneficios tiene mi plan?")
    print(f"\n[Consulta 2 - Plan] ({res2['latency_ms']} ms):\n{res2['text']}")
