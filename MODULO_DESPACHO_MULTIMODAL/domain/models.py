"""
Módulo Autónomo de Despacho Multimodal — Capa de Dominio: Modelos Tipados
Gobernanza: Universal Best Practices Engineering Rule (Pilar III: Type Safety)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid

from domain.enums import MediaType, MediaDirection, VaultStatus, ProcessingStatus, AnalysisIntent


@dataclass
class UserVault:
    vault_id: str
    msisdn_hash: str
    phone_display: str
    vault_directory: str
    quota_limit_bytes: int = 52428800  # 50 MB
    quota_used_bytes: int = 0
    status: VaultStatus = VaultStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_interaction: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def available_bytes(self) -> int:
        return max(0, self.quota_limit_bytes - self.quota_used_bytes)

    @property
    def usage_percentage(self) -> float:
        if self.quota_limit_bytes == 0:
            return 100.0
        return round((self.quota_used_bytes / self.quota_limit_bytes) * 100, 2)

    def can_store(self, file_size: int) -> bool:
        return (self.quota_used_bytes + file_size) <= self.quota_limit_bytes and self.status == VaultStatus.ACTIVE


@dataclass
class MediaAsset:
    asset_id: str
    vault_id: str
    direction: MediaDirection
    media_type: MediaType
    mime_type: str
    original_filename: str
    stored_filename: str
    file_size_bytes: int
    sha256_checksum: str
    file_rel_path: str
    expires_at: str
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    transcription_text: Optional[str] = None
    analysis_metadata: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class MultimodalMessage:
    message_id: str
    phone_number: str
    direction: MediaDirection
    media_type: MediaType
    file_bytes: bytes
    filename: str
    mime_type: Optional[str] = None
    caption: Optional[str] = None
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    duration_seconds: float
    engine: str = "whisper"


@dataclass
class AnalysisResult:
    intent: AnalysisIntent
    extracted_entities: Dict[str, Any]
    summary: str
    confidence: float


@dataclass
class RichResponse:
    text: str
    pwa_link_appended: bool
    attached_asset_id: Optional[str] = None
    attached_asset_url: Optional[str] = None
    attached_media_type: Optional[MediaType] = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
