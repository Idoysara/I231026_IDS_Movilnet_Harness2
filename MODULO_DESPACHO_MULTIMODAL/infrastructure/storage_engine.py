"""
Módulo Autónomo de Despacho Multimodal — Capa de Infraestructura: Motor de Almacenamiento Seguro
Gobernanza: Universal Best Practices Engineering Rule (Pilares I y VI)
"""

import hashlib
import os
import shutil
from typing import Tuple

from domain.enums import MediaType
from domain.invariants import SecurityException, sanitize_filename


class StorageEngine:
    """Motor de gestión de sistema de archivos físico con defensas contra Path Traversal."""

    def __init__(self, base_vault_path: str = None):
        env_vault_path = os.environ.get("MULTIMODAL_VAULT_ROOT")
        if base_vault_path:
            self.base_path = os.path.abspath(base_vault_path)
        elif env_vault_path:
            self.base_path = os.path.abspath(env_vault_path)
        else:
            self.base_path = os.path.abspath(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "vaults")
            )
        os.makedirs(self.base_path, exist_ok=True)

    def _is_safe_path(self, target_path: str) -> bool:
        """Valida que la ruta absoluta resida estrictamente dentro de base_path (evita bypass de startswith)."""
        try:
            return os.path.commonpath([self.base_path, os.path.abspath(target_path)]) == self.base_path
        except ValueError:
            return False

    def get_user_vault_path(self, msisdn_hash: str) -> str:
        """Obtiene y asegura el directorio raíz de la bóveda del abonado."""
        safe_hash = sanitize_filename(msisdn_hash)
        user_dir = os.path.abspath(os.path.join(self.base_path, f"usr_{safe_hash}"))
        
        # Guarda contra Path Traversal (Pilar VI)
        if not self._is_safe_path(user_dir):
            raise SecurityException(f"Violación de seguridad: Ruta no permitida {user_dir}")

        for sub in ["audio", "images", "documents", "video"]:
            os.makedirs(os.path.join(user_dir, sub), exist_ok=True)

        return user_dir

    def store_file(
        self,
        msisdn_hash: str,
        media_type: MediaType,
        filename: str,
        file_bytes: bytes,
        asset_id: str
    ) -> Tuple[str, str, str]:
        """
        Almacena un archivo binario de forma atómica en la subcarpeta correspondiente.
        Retorna: (file_rel_path, stored_filename, sha256_checksum)
        """
        user_dir = self.get_user_vault_path(msisdn_hash)
        subfolder = {
            MediaType.AUDIO: "audio",
            MediaType.IMAGE: "images",
            MediaType.DOCUMENT: "documents",
            MediaType.VIDEO: "video"
        }.get(media_type, "documents")

        target_dir = os.path.join(user_dir, subfolder)
        clean_name = sanitize_filename(filename)
        ext = os.path.splitext(clean_name)[1].lower() or ".bin"
        stored_name = f"{asset_id}{ext}"
        
        full_dest_path = os.path.abspath(os.path.join(target_dir, stored_name))
        if not self._is_safe_path(full_dest_path):
            raise SecurityException(f"Path Traversal evadido en: {full_dest_path}")

        # Escritura atómica
        tmp_dest = f"{full_dest_path}.tmp"
        with open(tmp_dest, "wb") as f:
            f.write(file_bytes)
        os.replace(tmp_dest, full_dest_path)

        # Cálculo de checksum SHA-256
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        rel_path = os.path.relpath(full_dest_path, self.base_path)

        return rel_path, stored_name, sha256

    def delete_file(self, rel_path: str) -> bool:
        """Elimina un archivo físico en disco de forma segura."""
        full_path = os.path.abspath(os.path.join(self.base_path, rel_path))
        if not self._is_safe_path(full_path):
            return False
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                return True
            except OSError:
                return False
        return False

    def read_file(self, rel_path: str) -> bytes:
        """
        Lee los bytes de un archivo almacenado en la bóveda (ruta relativa a la raíz de bóvedas).
        Lanza SecurityException si la ruta escapa de la raíz y FileNotFoundError si no existe.
        """
        full_path = os.path.abspath(os.path.join(self.base_path, rel_path))
        if not self._is_safe_path(full_path):
            raise SecurityException(f"Lectura fuera de la bóveda no permitida: {rel_path}")
        with open(full_path, "rb") as f:
            return f.read()
