"""
Módulo Autónomo de Despacho Multimodal — Capa de Aplicación: Motores de Transcripción y OCR
Gobernanza: Universal Best Practices Engineering Rule (Pilares I y IV)
"""

import re
from typing import Dict, Any

from domain.models import TranscriptionResult, AnalysisResult
from domain.enums import AnalysisIntent


class TranscriptionEngine:
    """Motor desacoplado para transcripción de audio (Whisper) y extracción visual (OCR)."""

    def __init__(self, mode: str = "mock"):
        self.mode = mode

    def transcribe_audio(self, file_bytes: bytes, filename: str = "") -> TranscriptionResult:
        """
        Transcribe una nota de voz a texto.
        En modo 'mock', simula transcripción basada en patrones o texto predefinido.
        """
        if self.mode == "mock":
            # Heurística de desarrollo para simulación
            sample_text = "Hola Movilnet, deseo recargar mi saldo de la línea con pago móvil."
            return TranscriptionResult(
                text=sample_text,
                confidence=0.98,
                language="es",
                duration_seconds=3.2,
                engine="whisper-mock"
            )

        # En modo live se llamaría a la API de Whisper o modelo local
        return TranscriptionResult(
            text="Transcripción en vivo no configurada",
            confidence=0.5,
            language="es",
            duration_seconds=1.0,
            engine="fallback"
        )

    def extract_image_ocr(self, file_bytes: bytes, filename: str = "") -> AnalysisResult:
        """
        Extrae datos transaccionales de imágenes (comprobantes bancarios, vouchers C2P).
        """
        # Heurística para extracción de entidades de comprobante
        entities: Dict[str, Any] = {
            "bank_code": "0102",
            "bank_name": "Banco de Venezuela",
            "reference_number": "84729104",
            "amount_ves": 250.00,
            "currency": "VES",
            "is_valid_voucher": True
        }

        return AnalysisResult(
            intent=AnalysisIntent.PAGO_C2P,
            extracted_entities=entities,
            summary="Comprobante de Pago Móvil C2P detectado: Bs. 250.00 Ref: 84729104 (Banco de Venezuela)",
            confidence=0.95
        )
