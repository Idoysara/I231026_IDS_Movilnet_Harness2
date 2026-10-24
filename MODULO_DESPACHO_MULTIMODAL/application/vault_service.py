"""
Módulo Autónomo de Despacho Multimodal — Capa de Aplicación: Gestor de Bóvedas Privadas ($1 <-> N)
Gobernanza: Universal Best Practices Engineering Rule (Pilares I y III)
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from domain.models import UserVault, MediaAsset
from domain.enums import MediaType, MediaDirection, VaultStatus
from domain.invariants import (
    generate_msisdn_hash,
    mask_phone_for_display,
    detect_mime_and_media_type,
    validate_file_size,
    QuotaExceededError,
    DEFAULT_USER_QUOTA
)
from infrastructure.repository import MultimodalRepository
from infrastructure.storage_engine import StorageEngine


class VaultService:
    """Caso de Uso: Gestión del Espacio Privado y Bóvedas de Abonados ($1 <-> N)."""

    def __init__(
        self,
        repository: MultimodalRepository,
        storage_engine: StorageEngine = None,
        secret_key: str = "movilnet_vault_secret_2026",
        default_quota_bytes: int = DEFAULT_USER_QUOTA
    ):
        self.repo = repository
        self.storage = storage_engine or StorageEngine()
        self.secret_key = secret_key
        self.default_quota = default_quota_bytes

    def get_or_create_user_vault(self, phone_number: str) -> UserVault:
        """Obtiene o inicializa de forma atómica la bóveda de un abonado."""
        msisdn_hash = generate_msisdn_hash(phone_number, self.secret_key)
        phone_display = mask_phone_for_display(phone_number)
        vault_dir = f"vaults/usr_{msisdn_hash}"
        
        # Asegurar directorios físicos en disco
        self.storage.get_user_vault_path(msisdn_hash)

        return self.repo.get_or_create_vault(
            msisdn_hash=msisdn_hash,
            phone_display=phone_display,
            vault_directory=vault_dir,
            quota_limit_bytes=self.default_quota
        )

    def check_user_quota(self, phone_number: str) -> Dict[str, Any]:
        """Consulta el estado de cuota y disponibilidad de un abonado."""
        vault = self.get_or_create_user_vault(phone_number)
        return {
            "vault_id": vault.vault_id,
            "msisdn_hash": vault.msisdn_hash,
            "quota_limit_bytes": vault.quota_limit_bytes,
            "quota_used_bytes": vault.quota_used_bytes,
            "available_bytes": vault.available_bytes,
            "usage_percentage": vault.usage_percentage,
            "status": vault.status.value,
            "can_upload": vault.status == VaultStatus.ACTIVE and vault.available_bytes > 0
        }

    def store_user_asset(
        self,
        phone_number: str,
        filename: str,
        file_bytes: bytes,
        direction: MediaDirection = MediaDirection.INBOUND,
        explicit_media_type: Optional[MediaType] = None,
        retention_days: int = 30
    ) -> MediaAsset:
        """
        Valida cuotas e invariantes y almacena el archivo en la bóveda privada.
        """
        # 1. Detección y validación de invariantes
        detected_mime, detected_type = detect_mime_and_media_type(file_bytes, filename)
        media_type = explicit_media_type or detected_type
        validate_file_size(file_bytes, media_type)

        # 2. Comprobación estricta de cuota de bóveda
        vault = self.get_or_create_user_vault(phone_number)
        file_size = len(file_bytes)

        if not vault.can_store(file_size):
            raise QuotaExceededError(
                f"Cuota de almacenamiento excedida ({vault.quota_used_bytes}/{vault.quota_limit_bytes} bytes). "
                f"No se puede almacenar archivo de {file_size} bytes."
            )

        # 3. Guardado físico en disco
        asset_id = f"ast-{uuid.uuid4()}"
        rel_path, stored_filename, sha256_checksum = self.storage.store_file(
            msisdn_hash=vault.msisdn_hash,
            media_type=media_type,
            filename=filename,
            file_bytes=file_bytes,
            asset_id=asset_id
        )

        # 4. Cálculo de fecha de expiración Zero-PII
        expires_at = (datetime.now(timezone.utc) + timedelta(days=retention_days)).isoformat()

        # 5. Registro en Base de Datos y actualización de cuota
        asset = MediaAsset(
            asset_id=asset_id,
            vault_id=vault.vault_id,
            direction=direction,
            media_type=media_type,
            mime_type=detected_mime,
            original_filename=filename,
            stored_filename=stored_filename,
            file_size_bytes=file_size,
            sha256_checksum=sha256_checksum,
            file_rel_path=rel_path,
            expires_at=expires_at
        )

        self.repo.record_asset(asset)
        self.repo.update_vault_usage(vault.vault_id, file_size)

        return asset

    def list_user_assets(self, phone_number: str, limit: int = 50) -> List[MediaAsset]:
        """Lista los archivos multimedia existentes en la bóveda de un abonado."""
        vault = self.get_or_create_user_vault(phone_number)
        return self.repo.list_assets_by_vault(vault.vault_id, limit)

    def cleanup_expired_assets(self) -> int:
        """Purga archivos expirados de la base de datos y del disco."""
        expired = self.repo.purge_expired_assets()
        deleted_count = 0
        for item in expired:
            if self.storage.delete_file(item["file_rel_path"]):
                deleted_count += 1
        return deleted_count
