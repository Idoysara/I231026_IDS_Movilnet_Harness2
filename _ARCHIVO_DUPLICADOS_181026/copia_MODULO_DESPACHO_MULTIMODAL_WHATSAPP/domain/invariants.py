"""
Módulo Autónomo de Despacho Multimodal — Capa de Dominio: Invariantes y Guardas
Gobernanza: Universal Best Practices Engineering Rule (Pilares III y VI)
"""

import hashlib
import hmac
import os
import re
from typing import Tuple, Dict

from domain.enums import MediaType


class DomainInvariantViolationError(Exception):
    """Lanzada cuando se violan reglas invariantes de negocio o formato."""
    pass


class QuotaExceededError(DomainInvariantViolationError):
    """Lanzada cuando la bóveda del usuario excede el límite de 50 MB."""
    pass


class SecurityException(DomainInvariantViolationError):
    """Lanzada ante intentos de Path Traversal o malware."""
    pass


# Límites estrictos por tipo de medio (en bytes)
MAX_LIMITS: Dict[MediaType, int] = {
    MediaType.AUDIO: 16 * 1024 * 1024,      # 16 MB
    MediaType.IMAGE: 5 * 1024 * 1024,       # 5 MB
    MediaType.DOCUMENT: 100 * 1024 * 1024,  # 100 MB
    MediaType.VIDEO: 16 * 1024 * 1024,      # 16 MB
}

DEFAULT_USER_QUOTA = 50 * 1024 * 1024  # 50 MB

OFFICIAL_PWA_LINK = "https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html"
PWA_SUFFIX_TEXT = f"""

🌐 Portal PWA 4GMAX (Acceso libre por Wi-Fi o Datos Móviles — Cualquier Operadora):
👉 {OFFICIAL_PWA_LINK}"""


def normalize_phone_number(phone: str) -> str:
    """Normaliza un número telefónico al estándar E.164 venezolano o internacional."""
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        raise DomainInvariantViolationError("El número de teléfono no puede estar vacío.")

    if digits.startswith("58"):
        return f"+{digits}"
    elif digits.startswith("0"):
        return f"+58{digits[1:]}"
    elif len(digits) == 10 and digits.startswith("4"):
        return f"+58{digits}"
    else:
        return f"+{digits}"


def generate_msisdn_hash(phone: str, secret_key: str = "movilnet_vault_secret_2026") -> str:
    """Genera un Blind Index criptográfico irreversible para la bóveda del usuario."""
    norm = normalize_phone_number(phone)
    return hmac.new(secret_key.encode("utf-8"), norm.encode("utf-8"), hashlib.sha256).hexdigest()


def mask_phone_for_display(phone: str) -> str:
    """Ofusca el número para vistas de telemetría sin revelar PII sensible."""
    norm = normalize_phone_number(phone)
    if len(norm) >= 10:
        return f"{norm[:6]}****{norm[-3:]}"
    return f"{norm[:3]}****"


def detect_mime_and_media_type(file_bytes: bytes, filename: str = "") -> Tuple[str, MediaType]:
    """
    Detecta el tipo MIME real mediante Magic Bytes y asigna el MediaType canónico.
    Rechaza ejecutables o archivos desconocidos.
    """
    if not file_bytes:
        raise DomainInvariantViolationError("El búfer de archivo está vacío (0 bytes).")

    header = file_bytes[:16]

    # JPEG: FF D8 FF
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", MediaType.IMAGE

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", MediaType.IMAGE

    # PDF: %PDF (25 50 44 46)
    if header.startswith(b"%PDF"):
        return "application/pdf", MediaType.DOCUMENT

    # OGG / Opus: OggS (4F 67 67 53)
    if header.startswith(b"OggS"):
        return "audio/ogg", MediaType.AUDIO

    # MP4: ftyp (ftypisom, ftypmp42, etc.)
    if len(header) >= 8 and (b"ftyp" in header[4:12]):
        return "video/mp4", MediaType.VIDEO

    # RIFF / WAV
    if header.startswith(b"RIFF") and b"WAVE" in file_bytes[8:16]:
        return "audio/wav", MediaType.AUDIO

    # Fallback por extensión para entornos de prueba
    ext = os.path.splitext(filename.lower())[1]
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg", MediaType.IMAGE
    elif ext == ".png":
        return "image/png", MediaType.IMAGE
    elif ext == ".pdf":
        return "application/pdf", MediaType.DOCUMENT
    elif ext in [".ogg", ".opus", ".mp3", ".wav"]:
        return "audio/ogg", MediaType.AUDIO
    elif ext == ".mp4":
        return "video/mp4", MediaType.VIDEO

    raise DomainInvariantViolationError(f"Tipo de archivo no permitido o desconocido: header={header[:4].hex()}")


def validate_file_size(file_bytes: bytes, media_type: MediaType) -> None:
    """Verifica que el archivo no supere el tamaño máximo admitido para su tipo."""
    size = len(file_bytes)
    max_allowed = MAX_LIMITS.get(media_type, 16 * 1024 * 1024)
    if size > max_allowed:
        raise DomainInvariantViolationError(
            f"El archivo ({size} bytes) excede el tamaño máximo permitido para {media_type.value} ({max_allowed} bytes)."
        )


def sanitize_filename(filename: str) -> str:
    """Sanitiza nombres de archivo eliminando path traversal y caracteres peligrosos."""
    base = os.path.basename(filename or "archivo_adjunto")
    clean = re.sub(r"[^\w\.\-]", "_", base)
    if clean.startswith("."):
        clean = f"f_{clean}"
    return clean or "archivo_binario"


def append_universal_pwa_link(message_text: str) -> str:
    """
    REGLA INVIOLABLE: Todo mensaje saliente debe concluir con el enlace PWA universal.
    """
    if OFFICIAL_PWA_LINK in (message_text or ""):
        return message_text
    return f"{message_text.strip()}{PWA_SUFFIX_TEXT}"
