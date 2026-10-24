"""
Módulo Autónomo de Despacho Multimodal — Subagente Especialista en Audio (Voice STT)
Gobernanza: Universal Best Practices Engineering Rule (Pilar I)
"""

from domain.models import TranscriptionResult
from application.transcription_engine import TranscriptionEngine


class VoiceSTTSubAgent:
    """Subagente especialista en transcripción fonética de notas de voz."""

    def __init__(self, engine: TranscriptionEngine = None):
        self.engine = engine or TranscriptionEngine()

    def process_voice_note(self, audio_bytes: bytes, filename: str) -> TranscriptionResult:
        """Procesa una nota de voz entrante y retorna el texto normalizado."""
        return self.engine.transcribe_audio(audio_bytes, filename)
