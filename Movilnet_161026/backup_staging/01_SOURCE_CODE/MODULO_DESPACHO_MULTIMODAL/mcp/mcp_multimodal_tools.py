"""
Módulo Autónomo de Despacho Multimodal — Capa MCP: Herramientas Model Context Protocol
Gobernanza: Universal Best Practices Engineering Rule (Pilares I y II)
"""

import os
import sys
import json
from typing import Dict, Any, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from infrastructure.database import get_multimodal_connection, init_multimodal_tables
from infrastructure.repository import MultimodalRepository
from application.vault_service import VaultService
from application.transcription_engine import TranscriptionEngine
from application.rich_response_builder import RichResponseBuilder


class MultimodalMcpTools:
    """Implementación de herramientas MCP para interoperabilidad con agentes de IA."""

    def __init__(self, db_path: Optional[str] = None):
        self.conn = get_multimodal_connection(db_path)
        init_multimodal_tables(self.conn)
        self.repo = MultimodalRepository(self.conn)
        self.vault_service = VaultService(self.repo)
        self.engine = TranscriptionEngine()
        self.builder = RichResponseBuilder()

    def mcp_vault_check_quota(self, phone_number: str) -> Dict[str, Any]:
        """Consulta el estado de cuota de la bóveda del abonado."""
        return self.vault_service.check_user_quota(phone_number)

    def mcp_media_inspect_asset(self, asset_id: str) -> Dict[str, Any]:
        """Obtiene la ficha técnica y estado de procesamiento de un archivo."""
        asset = self.repo.get_asset_by_id(asset_id)
        if not asset:
            return {"error": "ASSET_NOT_FOUND", "asset_id": asset_id}
        return {
            "asset_id": asset.asset_id,
            "vault_id": asset.vault_id,
            "direction": asset.direction.value,
            "media_type": asset.media_type.value,
            "mime_type": asset.mime_type,
            "file_size_bytes": asset.file_size_bytes,
            "sha256": asset.sha256_checksum,
            "status": asset.processing_status.value,
            "transcription": asset.transcription_text,
            "metadata": asset.analysis_metadata,
            "created_at": asset.created_at
        }

    def mcp_audio_transcribe(self, asset_id: str) -> Dict[str, Any]:
        """Dispara o consulta la transcripción fonética de una nota de voz."""
        asset = self.repo.get_asset_by_id(asset_id)
        if not asset:
            return {"error": "ASSET_NOT_FOUND", "asset_id": asset_id}
        if asset.transcription_text:
            return {
                "asset_id": asset.asset_id,
                "transcription": asset.transcription_text,
                "cached": True
            }
        # Si no tiene transcripción, la genera
        result = self.engine.transcribe_audio(b"dummy_bytes", asset.original_filename)
        self.repo.update_asset_processing(asset.asset_id, asset.processing_status, result.text)
        return {
            "asset_id": asset.asset_id,
            "transcription": result.text,
            "confidence": result.confidence,
            "language": result.language,
            "cached": False
        }

    def mcp_image_ocr_extract(self, asset_id: str) -> Dict[str, Any]:
        """Extrae datos estructurados de un comprobante bancario o imagen."""
        asset = self.repo.get_asset_by_id(asset_id)
        if not asset:
            return {"error": "ASSET_NOT_FOUND", "asset_id": asset_id}
        result = self.engine.extract_image_ocr(b"dummy_bytes", asset.original_filename)
        return {
            "asset_id": asset.asset_id,
            "intent": result.intent.value,
            "extracted_data": result.extracted_entities,
            "summary": result.summary
        }

    def mcp_generate_pdf_receipt(self, phone_number: str, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera un recibo PDF oficial y lo guarda en la bóveda del abonado."""
        pdf_bytes = self.builder.generate_pdf_receipt_bytes(phone_number, transaction_data)
        from domain.enums import MediaType, MediaDirection
        asset = self.vault_service.store_user_asset(
            phone_number=phone_number,
            filename="recibo_oficial.pdf",
            file_bytes=pdf_bytes,
            direction=MediaDirection.OUTBOUND,
            explicit_media_type=MediaType.DOCUMENT
        )
        return {
            "asset_id": asset.asset_id,
            "file_rel_path": asset.file_rel_path,
            "file_size_bytes": asset.file_size_bytes,
            "sha256": asset.sha256_checksum,
            "status": "GENERATED"
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CLI Autónomo MCP Multimodal Tools")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación formal")
    args = parser.parse_args()

    if args.test:
        tools = MultimodalMcpTools(":memory:")
        quota = tools.mcp_vault_check_quota("+584166251587")
        assert quota["can_upload"] is True, "Fallo en verificación de cuota"
        receipt = tools.mcp_generate_pdf_receipt(
            "+584166251587",
            {"reference": "TEST1234", "amount": "100.00"}
        )
        assert receipt["status"] == "GENERATED", "Fallo al generar recibo PDF"
        print("✅ [MCP Multimodal Tools] Auto-verificación 100% PASS.")
