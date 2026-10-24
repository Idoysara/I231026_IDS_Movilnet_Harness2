"""
Módulo Autónomo de Despacho Multimodal — Capa de Aplicación: Motores de Transcripción y OCR
Gobernanza: Universal Best Practices Engineering Rule (Pilares I y IV)
"""

import logging
import re
from typing import Dict, Any, Optional

from domain.models import TranscriptionResult, AnalysisResult
from domain.enums import AnalysisIntent
from application.voucher_parser import parse_voucher_text
from infrastructure.ocr_backends import OcrBackend, OcrUnavailableError, build_ocr_backend
from infrastructure.stt_backends import SttBackend, SttUnavailableError, build_stt_backend

logger = logging.getLogger("TranscriptionEngine")


class TranscriptionEngine:
    """Motor desacoplado para transcripción de audio (Whisper/Gemini) y extracción visual (OCR)."""

    def __init__(
        self,
        mode: str = "auto",
        ocr_backend: Optional[OcrBackend] = None,
        stt_backend: Optional[SttBackend] = None
    ):
        self.mode = mode
        self.ocr_backend: OcrBackend = ocr_backend or build_ocr_backend()
        self.stt_backend: SttBackend = stt_backend or build_stt_backend()

    def transcribe_audio(
        self,
        file_bytes: bytes,
        filename: str = "",
        mime_type: str = "audio/ogg"
    ) -> TranscriptionResult:
        """
        Transcribe una nota de voz a texto fonético exacto.
        Falla cerrado: si el backend no está disponible o falla, devuelve TranscriptionResult
        con text="" y confidence=0.0 (marcando el activo como FAILED); JAMÁS inventa texto simulado.
        """
        try:
            res = self.stt_backend.audio_to_text(file_bytes, filename=filename, mime_type=mime_type)
            return TranscriptionResult(
                text=res.text,
                confidence=res.confidence,
                language=res.language,
                duration_seconds=res.duration_seconds,
                engine=res.engine
            )
        except SttUnavailableError as exc:
            logger.warning("STT no disponible o falló para '%s': %s", filename, exc)
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language="es",
                duration_seconds=0.0,
                engine=self.stt_backend.name
            )

    def extract_image_ocr(self, file_bytes: bytes, filename: str = "") -> AnalysisResult:
        """
        Extrae datos transaccionales REALES de una imagen (comprobante bancario / voucher C2P).
        Flujo: backend OCR (imagen -> texto) -> parser puro (texto -> entidades validadas).
        Falla cerrado: si no hay OCR o la imagen no contiene un comprobante legible, devuelve
        `is_valid_voucher=False` con el motivo en `ocr_status`; JAMÁS datos inventados.
        """
        try:
            text = self.ocr_backend.image_to_text(file_bytes)
        except OcrUnavailableError as exc:
            logger.warning("OCR no disponible para '%s': %s", filename, exc)
            return AnalysisResult(
                intent=AnalysisIntent.DESCONOCIDO,
                extracted_entities={"is_valid_voucher": False, "ocr_status": "OCR_UNAVAILABLE", "ocr_error": str(exc)},
                summary="No fue posible leer la imagen en este momento.",
                confidence=0.0,
            )

        parsed = parse_voucher_text(text)
        entities: Dict[str, Any] = parsed.to_entities()
        entities["ocr_status"] = "OK"
        entities["ocr_engine"] = self.ocr_backend.name

        if not parsed.is_valid_voucher:
            return AnalysisResult(
                intent=AnalysisIntent.DESCONOCIDO,
                extracted_entities=entities,
                summary="La imagen no contiene un comprobante legible (falta referencia o monto).",
                confidence=parsed.confidence,
            )

        bank = f" ({parsed.bank_name})" if parsed.bank_name else ""
        return AnalysisResult(
            intent=AnalysisIntent.PAGO_C2P,
            extracted_entities=entities,
            summary=(
                f"Comprobante de Pago Móvil C2P detectado: Bs. {parsed.amount_ves:.2f} "
                f"Ref: {parsed.reference_number}{bank}"
            ),
            confidence=parsed.confidence,
        )

