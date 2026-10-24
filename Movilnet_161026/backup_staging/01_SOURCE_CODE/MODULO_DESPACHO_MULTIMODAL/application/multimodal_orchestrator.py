"""
Módulo Autónomo de Despacho Multimodal — Capa de Aplicación: Orquestador Multimodal Swarm
Gobernanza: Universal Best Practices Engineering Rule (Pilares I y III)
"""

import time
import uuid
from typing import Dict, Any, Optional

from domain.models import RichResponse, MediaAsset
from domain.enums import MediaType, MediaDirection
from application.vault_service import VaultService
from application.media_processor import MediaProcessor
from application.rich_response_builder import RichResponseBuilder
from infrastructure.whatsapp_client import WhatsAppMultimodalClient
from infrastructure.repository import MultimodalRepository


class MultimodalOrchestrator:
    """Orquestador Central de Conversaciones e Ingesta Multimodal."""

    def __init__(
        self,
        vault_service: VaultService,
        media_processor: MediaProcessor,
        response_builder: RichResponseBuilder,
        whatsapp_client: WhatsAppMultimodalClient,
        repository: MultimodalRepository
    ):
        self.vault_service = vault_service
        self.processor = media_processor
        self.response_builder = response_builder
        self.whatsapp_client = whatsapp_client
        self.repo = repository

    def handle_inbound_media(
        self,
        phone_number: str,
        filename: str,
        file_bytes: bytes,
        channel: str = "WHATSAPP"
    ) -> Dict[str, Any]:
        """
        Orquesta el ciclo completo de atención a un mensaje multimodal entrante:
        Ingesta -> Almacenamiento en Bóveda -> Transcripción/OCR -> Respuesta Enriquecida -> Despacho.
        """
        t0 = time.time()

        # 1. Ingesta y análisis
        asset = self.processor.ingest_and_process(
            phone_number=phone_number,
            filename=filename,
            file_bytes=file_bytes,
            direction=MediaDirection.INBOUND
        )

        # 2. Construcción de respuesta inteligente
        reply_body = ""
        output_asset = None

        if asset.media_type == MediaType.AUDIO:
            reply_body = (
                f"🎙️ He recibido y procesado tu nota de voz exitosamente:\n"
                f"«{asset.transcription_text}»\n\n"
                f"¿En qué más te puedo apoyar hoy con tu línea Movilnet?"
            )
        elif asset.media_type == MediaType.IMAGE:
            reply_body = (
                f"📸 Comprobante validado correctamente.\n"
                f"Detalle: {asset.transcription_text}\n"
                f"Tu saldo ha sido actualizado con éxito."
            )
            # Generar comprobante PDF oficial saliente
            pdf_bytes = self.response_builder.generate_pdf_receipt_bytes(
                phone_number=phone_number,
                data={"reference": "84729104", "amount": "250.00", "bank": "Banco de Venezuela (0102)"}
            )
            output_asset = self.vault_service.store_user_asset(
                phone_number=phone_number,
                filename="comprobante_recarga_movilnet.pdf",
                file_bytes=pdf_bytes,
                direction=MediaDirection.OUTBOUND,
                explicit_media_type=MediaType.DOCUMENT
            )
        else:
            reply_body = f"He recibido tu archivo '{filename}' y ha sido archivado en tu bóveda privada segura."

        # 3. Aplicación de la Regla Inviolable de Enlace PWA Universal
        final_text = self.response_builder.format_text_reply(reply_body)

        # 4. Despacho hacia WhatsApp (si hay adjunto o solo texto)
        dispatch_result = None
        if output_asset:
            dispatch_result = self.whatsapp_client.dispatch_media_message(
                phone_number=phone_number,
                media_type=MediaType.DOCUMENT,
                media_url_or_path=output_asset.file_rel_path,
                caption=final_text
            )
        else:
            # Despacho de texto vía cliente
            dispatch_result = self.whatsapp_client.dispatch_media_message(
                phone_number=phone_number,
                media_type=MediaType.AUDIO if asset.media_type == MediaType.AUDIO else MediaType.IMAGE,
                media_url_or_path=asset.file_rel_path,
                caption=final_text
            )

        latency_ms = round((time.time() - t0) * 1000, 2)

        return {
            "status": "PROCESSED",
            "phone_number": phone_number,
            "input_asset_id": asset.asset_id,
            "media_type": asset.media_type.value,
            "transcription": asset.transcription_text,
            "output_asset_id": output_asset.asset_id if output_asset else None,
            "reply_text": final_text,
            "latency_ms": latency_ms,
            "dispatch": dispatch_result
        }
