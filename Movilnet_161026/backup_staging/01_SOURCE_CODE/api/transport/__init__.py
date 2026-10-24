#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api.transport — Capa de Infraestructura de Transporte y Streaming HTTP
=============================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
"""

from api.transport.static_streamer import (
    CHUNK_SIZE_BYTES,
    DEFAULT_UI_ROOT,
    MIME_MAP,
    get_mime_type,
    read_file_buffered,
    serve_static_file,
    stream_file_chunks,
)
from api.transport.threaded_server import (
    MovilnetHTTPRequestHandler,
    StandaloneServerRunner,
    _ThreadedHTTPServer,
)

__all__ = [
    "CHUNK_SIZE_BYTES",
    "DEFAULT_UI_ROOT",
    "MIME_MAP",
    "get_mime_type",
    "read_file_buffered",
    "serve_static_file",
    "stream_file_chunks",
    "_ThreadedHTTPServer",
    "MovilnetHTTPRequestHandler",
    "StandaloneServerRunner",
]
