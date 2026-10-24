"""
Módulo Autónomo de Despacho Multimodal — Capa de Aplicación: Procesador Unificado de Medios
Gobernanza: Universal Best Practices Engineering Rule (Pilares I, III y IV)
"""

from typing import Dict, Any, Optional

from domain.models import MediaAsset
from domain.enums import MediaType, MediaDirection, ProcessingStatus
from application.vault_service import VaultService
from application.transcription_engine import TranscriptionEngine
from infrastructure.repository import MultimodalRepository


class MediaProcessor:
    """Pipeline de Ingesta, Almacenamiento Seguro y Extracción de Medios."""

    def __init__(
        self,
        vault_service: VaultService,
        repository: MultimodalRepository,
        transcription_engine: Optional[TranscriptionEngine] = None
    ):
        self.vault_service = vault_service
        self.repo = repository
        self.engine = transcription_engine or TranscriptionEngine()

    def ingest_and_process(
        self,
        phone_number: str,
        filename: str,
        file_bytes: bytes,
        direction: MediaDirection = MediaDirection.INBOUND
    ) -> MediaAsset:
        """
        Flujo Completo:
        1. Almacena en la bóveda privada del abonado.
        2. Dispara el motor correspondiente (STT para audio, OCR para fotos).
        3. Persiste los resultados de análisis en base de datos.
        """
        # 1. Almacenamiento seguro en bóveda privada con validación de cuotas
        asset = self.vault_service.store_user_asset(
            phone_number=phone_number,
            filename=filename,
            file_bytes=file_bytes,
            direction=direction
        )

        # 2. Extracción de inteligencia según tipo de medio
        transcription = None
        analysis_metadata = None

        if asset.media_type == MediaType.AUDIO:
            stt_result = self.engine.transcribe_audio(file_bytes, filename)
            transcription = stt_result.text
            analysis_metadata = {
                "confidence": stt_result.confidence,
                "duration_seconds": stt_result.duration_seconds,
                "engine": stt_result.engine
            }

        elif asset.media_type == MediaType.IMAGE:
            ocr_result = self.engine.extract_image_ocr(file_bytes, filename)
            transcription = ocr_result.summary
            analysis_metadata = ocr_result.extracted_entities

        elif asset.media_type == MediaType.DOCUMENT:
            transcription = f"Documento recibido: {filename}"
            analysis_metadata = {"type": "PDF_DOCUMENT", "pages": 1}

        # 3. Actualizar metadatos del activo
        self.repo.update_asset_processing(
            asset_id=asset.asset_id,
            status=ProcessingStatus.PROCESSED,
            transcription_text=transcription,
            analysis_metadata=analysis_metadata
        )

        asset.transcription_text = transcription
        asset.analysis_metadata = analysis_metadata
        asset.processing_status = ProcessingStatus.PROCESSED

        return asset
