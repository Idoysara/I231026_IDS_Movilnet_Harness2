"""
Módulo Autónomo de Despacho Multimodal — Capa de Infraestructura: Backends de OCR
Gobernanza: Universal Best Practices Engineering Rule (Pilares I, II, IV y VI)

Los backends convierten BYTES de imagen en TEXTO. Nunca interpretan ni inventan datos
(eso es responsabilidad de application/voucher_parser.py). Zero-PII: la imagen se pasa por
tubería (stdin) al proceso OCR; no se escribe en disco.

Selección por variable de entorno OCR_ENGINE_TYPE:
    tesseract (por defecto) -> TesseractBackend (requiere el binario `tesseract` instalado)
    none                    -> UnavailableBackend (falla cerrado de forma explícita)

Ejecución autónoma:
    python3 infrastructure/ocr_backends.py --status
    python3 infrastructure/ocr_backends.py --image ruta/voucher.jpg
    python3 infrastructure/ocr_backends.py --test
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from typing import Optional, Protocol

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("OcrBackends")

OCR_TIMEOUT_SECONDS = 20
OCR_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB: protección ante payloads abusivos


class OcrUnavailableError(RuntimeError):
    """El motor OCR no está disponible o falló; el llamador debe fallar cerrado (sin inventar datos)."""


class OcrBackend(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def image_to_text(self, image_bytes: bytes) -> str: ...


class TesseractBackend:
    """OCR local con el binario Tesseract vía subprocess (sin dependencias Python)."""

    name = "tesseract"

    def __init__(self, languages: str = "spa+eng", binary: Optional[str] = None):
        self.languages = languages
        self.binary = binary or shutil.which("tesseract")

    def is_available(self) -> bool:
        return bool(self.binary)

    def image_to_text(self, image_bytes: bytes) -> str:
        if not self.is_available():
            raise OcrUnavailableError("Tesseract no está instalado (brew install tesseract tesseract-lang)")
        if not image_bytes or len(image_bytes) > OCR_MAX_IMAGE_BYTES:
            raise OcrUnavailableError("Imagen vacía o excede el tamaño máximo permitido")
        try:
            proc = subprocess.run(
                [self.binary, "stdin", "stdout", "-l", self.languages, "--psm", "6"],
                input=image_bytes,
                capture_output=True,
                timeout=OCR_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            logger.error("Tesseract excedió %ss", OCR_TIMEOUT_SECONDS)
            raise OcrUnavailableError("Tesseract excedió el tiempo límite") from exc
        except OSError as exc:
            logger.error("No se pudo ejecutar Tesseract: %s", exc)
            raise OcrUnavailableError(f"No se pudo ejecutar Tesseract: {exc}") from exc
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace").strip()[:300]
            logger.warning("Tesseract terminó con código %s: %s", proc.returncode, err)
            raise OcrUnavailableError(f"Tesseract falló (código {proc.returncode}): {err}")
        return proc.stdout.decode("utf-8", errors="replace")


class AppleVisionBackend:
    """
    OCR nativo de macOS (framework Vision) mediante un helper Swift compilado bajo demanda.
    No requiere instalar nada: solo las herramientas de línea de comandos de Xcode (swiftc).
    """

    name = "apple_vision"

    _SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apple_vision_ocr.swift")
    _BINARY = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache", "apple_vision_ocr"
    )
    COMPILE_TIMEOUT_SECONDS = 300

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path or self._BINARY

    def is_available(self) -> bool:
        if sys.platform != "darwin":
            return False
        return os.path.isfile(self.binary_path) or (
            os.path.isfile(self._SOURCE) and shutil.which("swiftc") is not None
        )

    def _ensure_binary(self) -> str:
        """Compila el helper una sola vez (escritura atómica) y devuelve su ruta."""
        if os.path.isfile(self.binary_path):
            return self.binary_path
        swiftc = shutil.which("swiftc")
        if sys.platform != "darwin" or not swiftc or not os.path.isfile(self._SOURCE):
            raise OcrUnavailableError("Apple Vision no disponible (requiere macOS con swiftc)")
        os.makedirs(os.path.dirname(self.binary_path), exist_ok=True)
        tmp_out = f"{self.binary_path}.{os.getpid()}.tmp"
        try:
            proc = subprocess.run(
                [swiftc, "-O", self._SOURCE, "-o", tmp_out],
                capture_output=True, timeout=self.COMPILE_TIMEOUT_SECONDS, check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise OcrUnavailableError(f"No se pudo compilar el helper de Apple Vision: {exc}") from exc
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace").strip()[:300]
            raise OcrUnavailableError(f"Compilación del helper de Apple Vision falló: {err}")
        os.replace(tmp_out, self.binary_path)
        return self.binary_path

    def image_to_text(self, image_bytes: bytes) -> str:
        if not image_bytes or len(image_bytes) > OCR_MAX_IMAGE_BYTES:
            raise OcrUnavailableError("Imagen vacía o excede el tamaño máximo permitido")
        binary = self._ensure_binary()
        try:
            proc = subprocess.run(
                [binary], input=image_bytes, capture_output=True, timeout=OCR_TIMEOUT_SECONDS, check=False
            )
        except subprocess.TimeoutExpired as exc:
            logger.error("Apple Vision excedió %ss", OCR_TIMEOUT_SECONDS)
            raise OcrUnavailableError("Apple Vision excedió el tiempo límite") from exc
        except OSError as exc:
            raise OcrUnavailableError(f"No se pudo ejecutar el helper de Apple Vision: {exc}") from exc
        if proc.returncode == 2:
            raise OcrUnavailableError("La imagen es inválida o su formato no es soportado")
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace").strip()[:300]
            logger.warning("Apple Vision terminó con código %s: %s", proc.returncode, err)
            raise OcrUnavailableError(f"Apple Vision falló (código {proc.returncode}): {err}")
        return proc.stdout.decode("utf-8", errors="replace")


class UnavailableBackend:
    """Backend explícito de 'sin OCR': siempre falla cerrado."""

    name = "none"

    def is_available(self) -> bool:
        return False

    def image_to_text(self, image_bytes: bytes) -> str:
        raise OcrUnavailableError("OCR deshabilitado (OCR_ENGINE_TYPE=none)")


def build_ocr_backend(engine_type: Optional[str] = None) -> OcrBackend:
    """
    Fábrica según OCR_ENGINE_TYPE (por defecto 'auto').
      auto         -> Tesseract si está instalado, si no Apple Vision (macOS), si no 'none'
      tesseract | apple_vision | none
    Valores desconocidos fallan cerrado, nunca a un mock silencioso.
    """
    kind = (engine_type or os.environ.get("OCR_ENGINE_TYPE", "auto")).strip().lower()
    if kind == "auto":
        for candidate in (TesseractBackend(), AppleVisionBackend()):
            if candidate.is_available():
                return candidate
        return UnavailableBackend()
    if kind == "tesseract":
        return TesseractBackend()
    if kind == "apple_vision":
        return AppleVisionBackend()
    if kind == "none":
        return UnavailableBackend()
    logger.warning("OCR_ENGINE_TYPE='%s' desconocido; se usa backend no disponible (falla cerrado)", kind)
    return UnavailableBackend()


def _self_test() -> None:
    assert isinstance(build_ocr_backend("none"), UnavailableBackend)
    assert isinstance(build_ocr_backend("tesseract"), TesseractBackend)
    assert isinstance(build_ocr_backend("valor_raro"), UnavailableBackend)  # falla cerrado
    try:
        UnavailableBackend().image_to_text(b"x")
        raise AssertionError("debió lanzar OcrUnavailableError")
    except OcrUnavailableError:
        pass
    try:
        TesseractBackend(binary="").image_to_text(b"x")  # binario ausente
        raise AssertionError("debió lanzar OcrUnavailableError")
    except OcrUnavailableError:
        pass
    print("ocr_backends: auto-verificación OK")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description="Backends OCR autónomos")
    cli.add_argument("--status", action="store_true", help="Muestra el backend activo y su disponibilidad")
    cli.add_argument("--image", type=str, help="Ruta de imagen a procesar con el backend activo")
    cli.add_argument("--test", action="store_true", help="Auto-verificación")
    args = cli.parse_args()
    if args.test:
        _self_test()
    elif args.image:
        with open(args.image, "rb") as fh:
            print(build_ocr_backend().image_to_text(fh.read()))
    else:
        be = build_ocr_backend()
        print(f"backend={be.name} disponible={be.is_available()}")
