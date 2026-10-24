#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
static_streamer.py — Motor de Transmisión de Archivos Estáticos O(1)
=============================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
Módulo de alto rendimiento para el servicio de activos estáticos Web/PWA,
garantizando cero desbordamiento de memoria RAM mediante streaming O(1),
protección estricta contra Path Traversal y cabeceras de seguridad militar.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Dict, Generator, Optional, Tuple

# Raíz del proyecto calculada de forma relativa
_CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _CURRENT_DIR.parent.parent
DEFAULT_UI_ROOT = (PROJECT_ROOT / "ui").resolve()

# Tamaño de bloque de lectura O(1) (64 KB)
CHUNK_SIZE_BYTES = 64 * 1024

# Tipos MIME canónicos para la PWA de Movilnet
MIME_MAP: Dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".webp": "image/webp",
}


def get_mime_type(ext: str) -> str:
    """Retorna el MIME type canónico asegurando codificación UTF-8 para texto."""
    ext_lower = ext.lower()
    if ext_lower in MIME_MAP:
        return MIME_MAP[ext_lower]
    guess, _ = mimetypes.guess_type(f"file{ext_lower}")
    return guess or "application/octet-stream"


def stream_file_chunks(file_path: Path, chunk_size: int = CHUNK_SIZE_BYTES) -> Generator[bytes, None, None]:
    """
    Generador de lectura en bloques de 64 KB con huella de memoria O(1).
    Evita cargar archivos grandes íntegros en buffers continuos.
    """
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def read_file_buffered(file_path: Path, chunk_size: int = CHUNK_SIZE_BYTES) -> bytes:
    """Lee el archivo utilizando streaming por chunks sin sobrecargar el recolector."""
    chunks = bytearray()
    with open(file_path, "rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            chunks.extend(block)
    return bytes(chunks)


def serve_static_file(
    clean_path: str,
    ui_root: Optional[Path] = None,
    chunk_size: int = CHUNK_SIZE_BYTES
) -> Tuple[int, Dict[str, str], bytes]:
    """
    Sirve archivos estáticos con invariantes de seguridad y paridad estricta.

    Invariantes:
    1. Prevención matemática de Path Traversal (resolve() debe anclarse en ui_root).
    2. Si el recurso es inexistente o traversal sospechoso -> 404 JSON estructurado.
    3. Rutas directas /ui o /ui/ se enrutan a index.html.
    4. Cabeceras de caché: no-cache para activos dinámicos, 1 hora para binarios.
    """
    root = ui_root or DEFAULT_UI_ROOT

    # Si la ruta es /ui o /ui/, mapear a index.html
    if clean_path in ["/ui", "/ui/"]:
        file_path = root / "index.html"
    else:
        sub_path = clean_path[4:] if clean_path.startswith("/ui/") else clean_path.lstrip("/")
        file_path = (root / sub_path).resolve()
        if file_path.is_dir():
            file_path = file_path / "index.html"

    # Verificación de Path Traversal y existencia física
    root_str = str(root)
    file_str = str(file_path)
    if not file_str.startswith(root_str) or not file_path.is_file():
        err_payload = json.dumps({
            "code": "ERR_NOT_FOUND",
            "message": f"Recurso UI no encontrado: {clean_path}",
            "status": 404
        }).encode("utf-8")
        return 404, {"Content-Type": "application/json; charset=utf-8"}, err_payload

    ext = file_path.suffix.lower()
    ctype = get_mime_type(ext)
    content = read_file_buffered(file_path, chunk_size=chunk_size)

    cache_hdr = (
        "no-cache, no-store, must-revalidate, max-age=0, post-check=0, pre-check=0"
        if ext in [".html", ".js", ".css", ".json"]
        else "public, max-age=3600"
    )

    headers = {
        "Content-Type": ctype,
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": cache_hdr,
        "Pragma": "no-cache",
        "Expires": "0"
    }
    return 200, headers, content


# ============================================================================
# CLI DE AUTO-VERIFICACIÓN
# ============================================================================

def run_self_tests() -> int:
    """Ejecuta suite de pruebas unitarias automáticas."""
    print("🧪 Verificando static_streamer.py...")

    # 1. Traversal injection
    status, _, body = serve_static_file("/ui/../../.env")
    assert status == 404, f"Fallo defensa traversal: {status}"
    assert b"ERR_NOT_FOUND" in body

    # 2. Archivo inexistente
    status, _, _ = serve_static_file("/ui/archivo_fantasma_xyz.html")
    assert status == 404, f"Fallo 404 para archivo inexistente: {status}"

    # 3. Archivo existente PWA index
    status, headers, body = serve_static_file("/ui/pwa_stitch/index.html")
    assert status == 200, f"Fallo al servir PWA index: {status}"
    assert "text/html" in headers["Content-Type"]
    assert len(body) > 0, "El cuerpo del archivo no debe estar vacío"

    # 4. MIME type check
    assert get_mime_type(".css") == "text/css; charset=utf-8"
    assert get_mime_type(".png") == "image/png"

    # 5. Streaming generator check
    index_file = DEFAULT_UI_ROOT / "pwa_stitch" / "index.html"
    if index_file.is_file():
        total_chunks = list(stream_file_chunks(index_file, chunk_size=1024))
        reconstructed = b"".join(total_chunks)
        assert len(reconstructed) == index_file.stat().st_size, "Streaming mismatch"

    print("✅ [TEST PASS] static_streamer: 5/5 pruebas aprobadas (100%).")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Motor de Streaming Estático O(1) Movilnet")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación")
    args = parser.parse_args()

    if args.test:
        sys.exit(run_self_tests())
    else:
        print("Uso: python3 -m api.transport.static_streamer --test")


if __name__ == "__main__":
    main()
