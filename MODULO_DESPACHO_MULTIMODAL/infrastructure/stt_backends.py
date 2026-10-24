"""
Módulo Autónomo de Despacho Multimodal — Capa de Infraestructura: Backends de STT (Speech-to-Text)
Gobernanza: Universal Best Practices Engineering Rule (Pilares I, II, III, IV y VI)

Los backends convierten BYTES de audio (notas de voz OGG/Opus, WAV, MP3) en texto fonético literal.
Zero Hard Dependencies: opera con la librería estándar de Python 3 (urllib.request, json).
Falla cerrado: si no hay motor disponible o la API no responde, se lanza SttUnavailableError.
JAMÁS se devuelven textos inventados ni simulaciones silenciosas en modo productivo.

Selección por variable de entorno WHISPER_ENGINE_TYPE o STT_ENGINE_TYPE:
    auto        -> Gemini si GEMINI_API_KEY existe, si no OpenAI/Groq, si no local, si no 'none'
    gemini      -> GeminiAudioBackend (REST API nativa, zero pip deps)
    openai      -> OpenAIWhisperBackend
    local       -> LocalWhisperCliBackend (binario 'whisper')
    none        -> UnavailableSttBackend (falla cerrado explícitamente)

Ejecución autónoma:
    python3 infrastructure/stt_backends.py --status
    python3 infrastructure/stt_backends.py --test
"""

import argparse
import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional, Protocol

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("SttBackends")

STT_TIMEOUT_SECONDS = 25
STT_MAX_AUDIO_BYTES = 16 * 1024 * 1024  # 16 MB límite Carrier-Grade WhatsApp PTT


class SttUnavailableError(RuntimeError):
    """El motor STT no está disponible o falló; el llamador debe fallar cerrado."""


@dataclass
class SttResult:
    text: str
    confidence: float
    language: str
    duration_seconds: float
    engine: str


class SttBackend(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def audio_to_text(self, audio_bytes: bytes, filename: str = "", mime_type: str = "audio/ogg") -> SttResult: ...


class GeminiAudioBackend:
    """Transcripción fonética multimodal usando la API de Gemini via REST pura (urllib)."""

    name = "gemini_audio"

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def audio_to_text(self, audio_bytes: bytes, filename: str = "", mime_type: str = "audio/ogg") -> SttResult:
        if not self.is_available():
            raise SttUnavailableError("GEMINI_API_KEY no configurada para GeminiAudioBackend")
        if not audio_bytes or len(audio_bytes) > STT_MAX_AUDIO_BYTES:
            raise SttUnavailableError("Buffer de audio vacío o excede el límite de 16 MB")

        # Inferencia de MIME type si no viene especificado
        if not mime_type or mime_type == "application/octet-stream":
            if audio_bytes.startswith(b"OggS"):
                mime_type = "audio/ogg"
            elif audio_bytes.startswith(b"RIFF"):
                mime_type = "audio/wav"
            elif audio_bytes.startswith(b"ID3") or audio_bytes[:2] in (b"\xff\xfb", b"\xff\xf3"):
                mime_type = "audio/mp3"
            else:
                mime_type = "audio/ogg"

        b64_audio = base64.b64encode(audio_bytes).decode("ascii")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_audio
                        }
                    },
                    {
                        "text": (
                            "Transcribe este audio de manera exacta, literal y fiel en idioma español. "
                            "Devuelve única y exclusivamente el texto transcrito de la voz, sin comentarios, "
                            "sin etiquetas, sin saludos y sin explicaciones adicionales. "
                            "Si el audio contiene silencio o no hay voz inteligible, devuelve exactamente: [SILENCIO]"
                        )
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 1024
            }
        }

        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=STT_TIMEOUT_SECONDS) as resp:
                resp_bytes = resp.read()
                data = json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")[:300]
            logger.error("Gemini API error HTTP %s: %s", exc.code, err_body)
            raise SttUnavailableError(f"Error de API Gemini STT (HTTP {exc.code}): {err_body}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            logger.error("Error de conexión con Gemini STT: %s", exc)
            raise SttUnavailableError(f"Timeout o fallo de conexión en Gemini STT: {exc}") from exc
        except Exception as exc:
            logger.error("Excepción inesperada en Gemini STT: %s", exc)
            raise SttUnavailableError(f"Fallo inesperado en Gemini STT: {exc}") from exc

        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise SttUnavailableError("Respuesta de Gemini STT sin candidatos generados")
            parts = candidates[0].get("content", {}).get("parts", [])
            transcription = "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError) as exc:
            raise SttUnavailableError(f"Respuesta de Gemini STT malformada: {exc}") from exc

        if not transcription or transcription == "[SILENCIO]":
            return SttResult(
                text="",
                confidence=0.1,
                language="es",
                duration_seconds=0.0,
                engine=self.name
            )

        return SttResult(
            text=transcription,
            confidence=0.95,
            language="es",
            duration_seconds=0.0,
            engine=self.name
        )


class LocalWhisperCliBackend:
    """Transcripción local usando el binario 'whisper' en el sistema si está instalado."""

    name = "local_whisper_cli"

    def __init__(self, binary: Optional[str] = None):
        self.binary = binary or shutil.which("whisper")

    def is_available(self) -> bool:
        return bool(self.binary)

    def audio_to_text(self, audio_bytes: bytes, filename: str = "", mime_type: str = "audio/ogg") -> SttResult:
        if not self.is_available():
            raise SttUnavailableError("Binario 'whisper' no disponible en el sistema")
        if not audio_bytes or len(audio_bytes) > STT_MAX_AUDIO_BYTES:
            raise SttUnavailableError("Buffer de audio vacío o excede el límite de 16 MB")

        # Escritura temporal protegida
        import tempfile
        ext = os.path.splitext(filename)[1] or ".ogg"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        out_dir = tempfile.mkdtemp()
        try:
            proc = subprocess.run(
                [self.binary, tmp_path, "--language", "Spanish", "--model", "base", "--output_dir", out_dir, "--output_format", "txt"],
                capture_output=True,
                timeout=STT_TIMEOUT_SECONDS,
                check=False
            )
            if proc.returncode != 0:
                err = proc.stderr.decode("utf-8", errors="replace").strip()[:300]
                raise SttUnavailableError(f"Whisper CLI falló (código {proc.returncode}): {err}")
            txt_file = os.path.join(out_dir, os.path.splitext(os.path.basename(tmp_path))[0] + ".txt")
            if os.path.isfile(txt_file):
                with open(txt_file, "r", encoding="utf-8") as f:
                    text = f.read().strip()
            else:
                text = ""
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            shutil.rmtree(out_dir, ignore_errors=True)

        return SttResult(
            text=text,
            confidence=0.90,
            language="es",
            duration_seconds=0.0,
            engine=self.name
        )


class UnavailableSttBackend:
    """Backend explícito de 'sin STT': siempre falla cerrado sin inventar datos."""

    name = "none"

    def is_available(self) -> bool:
        return False

    def audio_to_text(self, audio_bytes: bytes, filename: str = "", mime_type: str = "audio/ogg") -> SttResult:
        raise SttUnavailableError("STT deshabilitado o no configurado (WHISPER_ENGINE_TYPE=none)")


def build_stt_backend(engine_type: Optional[str] = None) -> SttBackend:
    """
    Fábrica según WHISPER_ENGINE_TYPE / STT_ENGINE_TYPE (por defecto 'auto').
      auto    -> GeminiAudioBackend si GEMINI_API_KEY existe, si no LocalWhisper, si no 'none'
      gemini  -> GeminiAudioBackend
      local   -> LocalWhisperCliBackend
      none    -> UnavailableSttBackend
    Valores desconocidos fallan cerrado.
    """
    kind = (engine_type or os.environ.get("WHISPER_ENGINE_TYPE", os.environ.get("STT_ENGINE_TYPE", "auto"))).strip().lower()
    
    if kind == "auto":
        gemini = GeminiAudioBackend()
        if gemini.is_available():
            return gemini
        local = LocalWhisperCliBackend()
        if local.is_available():
            return local
        return UnavailableSttBackend()

    if kind in ("gemini", "gemini_audio"):
        return GeminiAudioBackend()
    if kind in ("local", "local_whisper"):
        return LocalWhisperCliBackend()
    if kind == "none":
        return UnavailableSttBackend()

    logger.warning("STT engine '%s' desconocido; se usa backend no disponible (falla cerrado)", kind)
    return UnavailableSttBackend()


def _self_test() -> None:
    assert isinstance(build_stt_backend("none"), UnavailableSttBackend)
    assert isinstance(build_stt_backend("invalido_xyz"), UnavailableSttBackend)
    try:
        UnavailableSttBackend().audio_to_text(b"audio")
        raise AssertionError("debió lanzar SttUnavailableError")
    except SttUnavailableError:
        pass
    print("stt_backends: auto-verificación OK")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description="Backends STT autónomos (Voice to Text)")
    cli.add_argument("--status", action="store_true", help="Muestra el backend STT activo y su disponibilidad")
    cli.add_argument("--test", action="store_true", help="Auto-verificación")
    args = cli.parse_args()
    if args.test:
        _self_test()
    else:
        be = build_stt_backend()
        print(f"backend={be.name} disponible={be.is_available()}")
