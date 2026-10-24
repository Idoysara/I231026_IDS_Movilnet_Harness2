"""
Módulo Autónomo de Despacho Multimodal — Capa de Infraestructura: Repositorio Tipado
Gobernanza: Universal Best Practices Engineering Rule (Pilares I y III)
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from domain.models import UserVault, MediaAsset
from domain.enums import MediaType, MediaDirection, VaultStatus, ProcessingStatus


class MultimodalRepository:
    """Repositorio tipado para la persistencia de bóvedas y activos multimedia."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_or_create_vault(
        self,
        msisdn_hash: str,
        phone_display: str,
        vault_directory: str,
        quota_limit_bytes: int = 52428800
    ) -> UserVault:
        """Obtiene una bóveda existente o crea una nueva de forma atómica."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM user_multimodal_vault WHERE msisdn_hash = ?",
            (msisdn_hash,)
        )
        row = cursor.fetchone()
        now = datetime.utcnow().isoformat()

        if row:
            return UserVault(
                vault_id=row["vault_id"],
                msisdn_hash=row["msisdn_hash"],
                phone_display=row["phone_display"],
                vault_directory=row["vault_directory"],
                quota_limit_bytes=row["quota_limit_bytes"],
                quota_used_bytes=row["quota_used_bytes"],
                status=VaultStatus(row["status"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                last_interaction=row["last_interaction"]
            )

        vault_id = f"vlt-{uuid.uuid4()}"
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO user_multimodal_vault (
                    vault_id, msisdn_hash, phone_display, vault_directory,
                    quota_limit_bytes, quota_used_bytes, status,
                    created_at, updated_at, last_interaction
                ) VALUES (?, ?, ?, ?, ?, 0, 'ACTIVE', ?, ?, ?)
                """,
                (vault_id, msisdn_hash, phone_display, vault_directory, quota_limit_bytes, now, now, now)
            )

        return UserVault(
            vault_id=vault_id,
            msisdn_hash=msisdn_hash,
            phone_display=phone_display,
            vault_directory=vault_directory,
            quota_limit_bytes=quota_limit_bytes,
            quota_used_bytes=0,
            status=VaultStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            last_interaction=now
        )

    def get_vault_by_hash(self, msisdn_hash: str) -> Optional[UserVault]:
        """Busca una bóveda por su hash ciego O(1)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM user_multimodal_vault WHERE msisdn_hash = ?", (msisdn_hash,))
        row = cursor.fetchone()
        if not row:
            return None
        return UserVault(
            vault_id=row["vault_id"],
            msisdn_hash=row["msisdn_hash"],
            phone_display=row["phone_display"],
            vault_directory=row["vault_directory"],
            quota_limit_bytes=row["quota_limit_bytes"],
            quota_used_bytes=row["quota_used_bytes"],
            status=VaultStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_interaction=row["last_interaction"]
        )

    def update_vault_usage(self, vault_id: str, delta_bytes: int) -> None:
        """Actualiza el consumo de cuota de la bóveda de forma atómica."""
        now = datetime.utcnow().isoformat()
        with self.conn:
            self.conn.execute(
                """
                UPDATE user_multimodal_vault 
                SET quota_used_bytes = MAX(0, quota_used_bytes + ?),
                    updated_at = ?,
                    last_interaction = ?,
                    status = CASE 
                        WHEN quota_used_bytes + ? > quota_limit_bytes THEN 'EXCEEDED' 
                        ELSE 'ACTIVE' 
                    END
                WHERE vault_id = ?
                """,
                (delta_bytes, now, now, delta_bytes, vault_id)
            )

    def record_asset(self, asset: MediaAsset) -> None:
        """Inserta los metadatos de un archivo multimedia recién almacenado."""
        meta_str = json.dumps(asset.analysis_metadata) if asset.analysis_metadata else None
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO multimodal_media_asset (
                    asset_id, vault_id, direction, media_type, mime_type,
                    original_filename, stored_filename, file_size_bytes,
                    sha256_checksum, file_rel_path, processing_status,
                    transcription_text, analysis_metadata, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset.asset_id, asset.vault_id, asset.direction.value, asset.media_type.value,
                    asset.mime_type, asset.original_filename, asset.stored_filename,
                    asset.file_size_bytes, asset.sha256_checksum, asset.file_rel_path,
                    asset.processing_status.value, asset.transcription_text, meta_str,
                    asset.expires_at, asset.created_at
                )
            )

    def get_asset_by_id(self, asset_id: str) -> Optional[MediaAsset]:
        """Recupera un activo multimedia por su ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM multimodal_media_asset WHERE asset_id = ?", (asset_id,))
        row = cursor.fetchone()
        if not row:
            return None
        meta = json.loads(row["analysis_metadata"]) if row["analysis_metadata"] else None
        return MediaAsset(
            asset_id=row["asset_id"],
            vault_id=row["vault_id"],
            direction=MediaDirection(row["direction"]),
            media_type=MediaType(row["media_type"]),
            mime_type=row["mime_type"],
            original_filename=row["original_filename"],
            stored_filename=row["stored_filename"],
            file_size_bytes=row["file_size_bytes"],
            sha256_checksum=row["sha256_checksum"],
            file_rel_path=row["file_rel_path"],
            processing_status=ProcessingStatus(row["processing_status"]),
            transcription_text=row["transcription_text"],
            analysis_metadata=meta,
            expires_at=row["expires_at"],
            created_at=row["created_at"]
        )

    def list_assets_by_vault(self, vault_id: str, limit: int = 50) -> List[MediaAsset]:
        """Lista los activos vivos de una bóveda."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM multimodal_media_asset WHERE vault_id = ? ORDER BY created_at DESC LIMIT ?",
            (vault_id, limit)
        )
        assets = []
        for row in cursor.fetchall():
            meta = json.loads(row["analysis_metadata"]) if row["analysis_metadata"] else None
            assets.append(MediaAsset(
                asset_id=row["asset_id"],
                vault_id=row["vault_id"],
                direction=MediaDirection(row["direction"]),
                media_type=MediaType(row["media_type"]),
                mime_type=row["mime_type"],
                original_filename=row["original_filename"],
                stored_filename=row["stored_filename"],
                file_size_bytes=row["file_size_bytes"],
                sha256_checksum=row["sha256_checksum"],
                file_rel_path=row["file_rel_path"],
                processing_status=ProcessingStatus(row["processing_status"]),
                transcription_text=row["transcription_text"],
                analysis_metadata=meta,
                expires_at=row["expires_at"],
                created_at=row["created_at"]
            ))
        return assets

    def update_asset_processing(
        self,
        asset_id: str,
        status: ProcessingStatus,
        transcription_text: Optional[str] = None,
        analysis_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Actualiza el estado de análisis e inteligencia de un activo."""
        meta_str = json.dumps(analysis_metadata) if analysis_metadata else None
        with self.conn:
            self.conn.execute(
                """
                UPDATE multimodal_media_asset
                SET processing_status = ?,
                    transcription_text = COALESCE(?, transcription_text),
                    analysis_metadata = COALESCE(?, analysis_metadata)
                WHERE asset_id = ?
                """,
                (status.value, transcription_text, meta_str, asset_id)
            )

    def purge_expired_assets(self, current_iso: str = None) -> List[Dict[str, Any]]:
        """Identifica y elimina activos cuya política de retención expiró (>30 días)."""
        now = current_iso or datetime.utcnow().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT asset_id, vault_id, file_rel_path, file_size_bytes FROM multimodal_media_asset WHERE expires_at <= ?",
            (now,)
        )
        expired = [dict(r) for r in cursor.fetchall()]
        
        if expired:
            with self.conn:
                for item in expired:
                    self.conn.execute(
                        "DELETE FROM multimodal_media_asset WHERE asset_id = ?",
                        (item["asset_id"],)
                    )
                    self.conn.execute(
                        "UPDATE user_multimodal_vault SET quota_used_bytes = MAX(0, quota_used_bytes - ?) WHERE vault_id = ?",
                        (item["file_size_bytes"], item["vault_id"])
                    )
        return expired
