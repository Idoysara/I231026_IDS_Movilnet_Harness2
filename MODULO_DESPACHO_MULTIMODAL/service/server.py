"""
Módulo Autónomo de Despacho Multimodal — Capa de Servicio: Servidor HTTP Autónomo (:8025)
Gobernanza: Universal Best Practices Engineering Rule (Pilar II: Autonomía de Módulos)
"""

import base64
import json
import logging
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional

# Agregar directorio raíz del módulo al path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(CURRENT_DIR)
if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)

from infrastructure.database import get_multimodal_connection, init_multimodal_tables
from infrastructure.repository import MultimodalRepository
from infrastructure.storage_engine import StorageEngine
from infrastructure.whatsapp_client import WhatsAppMultimodalClient
from application.vault_service import VaultService
from application.media_processor import MediaProcessor
from application.rich_response_builder import RichResponseBuilder
from application.multimodal_orchestrator import MultimodalOrchestrator
from domain.invariants import DomainInvariantViolationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MultimodalServer")

PORT = int(os.environ.get("MULTIMODAL_PORT", 8025))


class MultimodalRequestHandler(BaseHTTPRequestHandler):
    """Manejador HTTP REST autónomo sin dependencias pesadas externas."""

    # Inyección de dependencias compartidas
    conn = None
    repo = None
    vault_service = None
    orchestrator = None

    @classmethod
    def setup_services(cls, db_path: str = None, engine: Optional[Any] = None, vault_root: Optional[str] = None):
        cls.conn = get_multimodal_connection(db_path)
        init_multimodal_tables(cls.conn)
        cls.repo = MultimodalRepository(cls.conn)
        storage = StorageEngine(vault_root)
        cls.vault_service = VaultService(cls.repo, storage)
        processor = MediaProcessor(cls.vault_service, cls.repo, transcription_engine=engine)
        builder = RichResponseBuilder()
        wa_client = WhatsAppMultimodalClient()
        cls.orchestrator = MultimodalOrchestrator(
            cls.vault_service, processor, builder, wa_client, cls.repo
        )

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        response_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        """Soporte CORS pre-flight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # 1. Health check
        if path == "/health" or path == "/api/v1/health":
            self._send_json(200, {
                "status": "healthy",
                "service": "Módulo Autónomo de Despacho Multimodal",
                "port": PORT,
                "version": "1.0.0",
                "database": "CONNECTED_WAL"
            })
            return

        # 2. Consultar cuota de usuario
        if path == "/api/v1/vault/quota":
            phone = params.get("phone", [""])[0]
            if not phone:
                self._send_json(400, {"error": "Falta parámetro 'phone'"})
                return
            try:
                quota = self.vault_service.check_user_quota(phone)
                self._send_json(200, quota)
            except Exception as e:
                self._send_json(400, {"error": str(e)})
            return

        # 3. Listar archivos de la bóveda
        if path == "/api/v1/vault/assets":
            phone = params.get("phone", [""])[0]
            if not phone:
                self._send_json(400, {"error": "Falta parámetro 'phone'"})
                return
            try:
                assets = self.vault_service.list_user_assets(phone)
                self._send_json(200, {
                    "phone": phone,
                    "total_assets": len(assets),
                    "assets": [
                        {
                            "asset_id": a.asset_id,
                            "media_type": a.media_type.value,
                            "direction": a.direction.value,
                            "file_size": a.file_size_bytes,
                            "created_at": a.created_at,
                            "transcription": a.transcription_text
                        } for a in assets
                    ]
                })
            except Exception as e:
                self._send_json(400, {"error": str(e)})
            return

        self._send_json(404, {"error": "Ruta no encontrada", "path": path})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            self._send_json(400, {"error": "Payload JSON malformado"})
            return

        # 1. Inicializar Bóveda
        if path == "/api/v1/vault/init":
            phone = body.get("phone_number")
            if not phone:
                self._send_json(400, {"error": "Campo 'phone_number' es requerido"})
                return
            try:
                vault = self.vault_service.get_or_create_user_vault(phone)
                self._send_json(200, {
                    "vault_id": vault.vault_id,
                    "msisdn_hash": vault.msisdn_hash,
                    "phone_display": vault.phone_display,
                    "quota_limit_bytes": vault.quota_limit_bytes,
                    "quota_used_bytes": vault.quota_used_bytes,
                    "status": vault.status.value
                })
            except Exception as e:
                self._send_json(400, {"error": str(e)})
            return

        # 2. Ingesta Multimodal Completa (Base64 o URL mock)
        if path == "/api/v1/multimodal/process":
            phone = body.get("phone_number")
            filename = body.get("filename", "audio_note.ogg")
            b64_content = body.get("file_base64")
            raw_text = body.get("text_simulation", "")

            if not phone:
                self._send_json(400, {"error": "Campo 'phone_number' es requerido"})
                return

            if b64_content:
                file_bytes = base64.b64decode(b64_content)
            elif raw_text:
                file_bytes = b"OggS\x00\x02\x00\x00\x00\x00" + raw_text.encode("utf-8")
            else:
                file_bytes = b"OggS\x00\x02\x00\x00\x00\x00NOTA_DE_VOZ_DEFAULT"

            try:
                result = self.orchestrator.handle_inbound_media(
                    phone_number=phone,
                    filename=filename,
                    file_bytes=file_bytes
                )
                self._send_json(200, result)
            except DomainInvariantViolationError as e:
                self._send_json(422, {"code": "INVARIANT_VIOLATION", "error": str(e)})
            except Exception as e:
                self._send_json(500, {"code": "INTERNAL_ERROR", "error": str(e)})
            return

        self._send_json(404, {"error": "Endpoint POST no encontrado", "path": path})


def run_server(port: int = PORT, db_path: str = None):
    """Inicia el servidor HTTP en el puerto indicado."""
    MultimodalRequestHandler.setup_services(db_path)
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, MultimodalRequestHandler)
    logger.info(f"🚀 [Módulo Multimodal] Servidor activo en http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Deteniendo servidor multimodal...")
        httpd.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Servidor Autónomo Multimodal")
    parser.add_argument("--port", type=int, default=PORT, help="Puerto de escucha (default: 8025)")
    parser.add_argument("--db-path", type=str, default=None, help="Ruta de la base de datos")
    args = parser.parse_args()
    run_server(args.port, args.db_path)
