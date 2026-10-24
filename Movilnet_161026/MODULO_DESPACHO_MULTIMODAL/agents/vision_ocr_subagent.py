"""
Módulo Autónomo de Despacho Multimodal — Subagente Especialista en Visión y OCR
Gobernanza: Universal Best Practices Engineering Rule (Pilar I)
"""

from domain.models import AnalysisResult
from application.transcription_engine import TranscriptionEngine


class VisionOCRSubAgent:
    """Subagente especialista en procesamiento visual y extracción de comprobantes."""

    def __init__(self, engine: TranscriptionEngine = None):
        self.engine = engine or TranscriptionEngine()

    def process_image(self, image_bytes: bytes, filename: str) -> AnalysisResult:
        """Analiza una imagen o captura de pantalla extrayendo entidades bancarias."""
        return self.engine.extract_image_ocr(image_bytes, filename)
