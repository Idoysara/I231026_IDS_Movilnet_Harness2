"""
Módulo Autónomo de Despacho Multimodal — Capa de Agentes: Agente Multimodal Principal
Gobernanza: Universal Best Practices Engineering Rule (Pilares I y II)
"""

from typing import Dict, Any, Optional

from application.multimodal_orchestrator import MultimodalOrchestrator
from domain.enums import MediaType


class MultimodalMasterAgent:
    """Agente Principal del Enjambre para Gestión y Orquestación Multimodal."""

    def __init__(self, orchestrator: MultimodalOrchestrator):
        self.orchestrator = orchestrator

    def process_incoming_file(
        self,
        phone_number: str,
        filename: str,
        file_bytes: bytes,
        channel: str = "WHATSAPP"
    ) -> Dict[str, Any]:
        """Punto de entrada para la atención de mensajes con adjuntos multimedia."""
        return self.orchestrator.handle_inbound_media(
            phone_number=phone_number,
            filename=filename,
            file_bytes=file_bytes,
            channel=channel
        )

    def generate_and_dispatch_receipt(
        self,
        phone_number: str,
        transaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Genera un comprobante oficial y lo despacha al abonado."""
        pdf_bytes = self.orchestrator.response_builder.generate_pdf_receipt_bytes(
            phone_number=phone_number,
            data=transaction_data
        )
        asset = self.orchestrator.vault_service.store_user_asset(
            phone_number=phone_number,
            filename=f"recibo_{transaction_data.get('reference', 'c2p')}.pdf",
            file_bytes=pdf_bytes,
            direction=MediaType.DOCUMENT
        )
        reply_text = self.orchestrator.response_builder.format_text_reply(
            f"📄 Comprobante Oficial emitido con éxito para la referencia {transaction_data.get('reference')}."
        )
        dispatch = self.orchestrator.whatsapp_client.dispatch_media_message(
            phone_number=phone_number,
            media_type=MediaType.DOCUMENT,
            media_url_or_path=asset.file_rel_path,
            caption=reply_text
        )
        return {
            "status": "DISPATCHED",
            "asset_id": asset.asset_id,
            "dispatch": dispatch
        }
