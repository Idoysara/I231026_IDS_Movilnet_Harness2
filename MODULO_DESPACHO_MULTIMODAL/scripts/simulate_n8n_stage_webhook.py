"""
Módulo Autónomo de Despacho Multimodal — Script Autónomo: Simulador de Webhook n8n Stage
Gobernanza: Universal Best Practices Engineering Rule (Pilares II y V)
"""

import argparse
import base64
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from typing import Dict, Any

# Bootstrap de ruta para ejecución autónoma (Pilar II)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(CURRENT_DIR)
if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)

from domain.enums import MediaType
from domain.invariants import normalize_phone_number

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SimulateN8NStageWebhook")

DEFAULT_STAGE_URL = os.environ.get(
    "MULTIMODAL_API_URL",
    "http://127.0.0.1:8025/api/v1/multimodal/process"
)


def create_mock_c2p_voucher_bytes(bank_code: str = "0102", ref_num: str = "84729104", amount: str = "250.00") -> bytes:
    """Genera bytes de prueba con estructura de comprobante de pago móvil C2P."""
    voucher_text = (
        f"--- COMPROBANTE DE PAGO MOVIL C2P ---\n"
        f"Banco Emisor: 0102 Banco de Venezuela\n"
        f"Referencia: {ref_num}\n"
        f"Monto: Bs. {amount}\n"
        f"Fecha: 18/10/2026\n"
        f"Beneficiario: Movilnet Recargas\n"
        f"--------------------------------------"
    )
    # Header simulado de imagen JPEG/PNG con el texto incrustado
    return b"\x89PNG\r\n\x1a\n" + voucher_text.encode("utf-8")


def create_mock_voice_note_bytes(phrase: str = "Hola Movilnet, quiero recargar mi saldo") -> bytes:
    """Genera bytes de prueba con header OGG y texto para transcripción."""
    return b"OggS\x00\x02\x00\x00\x00\x00" + phrase.encode("utf-8")


def create_mock_video_bytes() -> bytes:
    """Genera bytes de prueba con header ISO Base Media (MP4)."""
    return b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00isommp42" + b"\x00" * 64


def build_n8n_stage_payload(
    phone_number: str,
    media_type: str,
    custom_bytes: bytes = None,
    filename: str = None
) -> Dict[str, Any]:
    norm_phone = normalize_phone_number(phone_number)

    if media_type == "IMAGE":
        name = filename or "voucher_c2p_bdv.png"
        content_bytes = custom_bytes or create_mock_c2p_voucher_bytes()
    elif media_type == "AUDIO":
        name = filename or "nota_voz_cliente.ogg"
        content_bytes = custom_bytes or create_mock_voice_note_bytes()
    elif media_type == "VIDEO":
        name = filename or "video_soporte.mp4"
        content_bytes = custom_bytes or create_mock_video_bytes()
    else:
        name = filename or "documento.pdf"
        content_bytes = b"%PDF-1.4\n%EOF"

    return {
        "phone_number": phone_number,
        "filename": name,
        "file_base64": base64.b64encode(content_bytes).decode("ascii"),
        "text_simulation": ""
    }


def send_payload_to_stage_endpoint(payload: Dict[str, Any], url: str = DEFAULT_STAGE_URL, timeout: float = 15.0) -> Dict[str, Any]:
    """Envía el payload HTTP POST al servidor de staging (:8025)."""
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "N8N_DEV_STAGE_SIMULATOR/1.0"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        resp_bytes = response.read()
        return json.loads(resp_bytes.decode("utf-8"))


def run_contract_test():
    """Ejecuta auto-verificación formal del generador de payloads de n8n."""
    print("Iniciando auto-verificación formal de simulate_n8n_stage_webhook.py...")

    phone = "+584166251587"
    p_img = build_n8n_stage_payload(phone, "IMAGE")
    assert p_img["phone_number"] == phone
    assert p_img["filename"].endswith(".png")
    assert len(p_img["file_base64"]) > 0

    p_aud = build_n8n_stage_payload(phone, "AUDIO")
    assert p_aud["filename"].endswith(".ogg")

    p_vid = build_n8n_stage_payload(phone, "VIDEO")
    assert p_vid["filename"].endswith(".mp4")

    # Validar decodificación base64 íntegra
    decoded_vid = base64.b64decode(p_vid["file_base64"])
    assert b"ftypmp42" in decoded_vid

    print("✅ Todas las verificaciones del contrato de simulate_n8n_stage_webhook pasaron al 100%.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de Webhook n8n [DEV_STAGE] para Despacho Multimodal")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación formal del contrato")
    parser.add_argument("--voucher", action="store_true", help="Simular envío de comprobante de pago C2P")
    parser.add_argument("--audio", action="store_true", help="Simular envío de nota de voz OGG")
    parser.add_argument("--video", action="store_true", help="Simular envío de video MP4")
    parser.add_argument("--phone", type=str, default="+584166251587", help="MSISDN del cliente (default: +584166251587)")
    parser.add_argument("--url", type=str, default=DEFAULT_STAGE_URL, help=f"URL del endpoint (default: {DEFAULT_STAGE_URL})")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar payload JSON sin enviar petición de red")
    args = parser.parse_args()

    if args.test:
        run_contract_test()
        sys.exit(0)

    media_selected = "IMAGE"
    if args.audio:
        media_selected = "AUDIO"
    elif args.video:
        media_selected = "VIDEO"

    payload = build_n8n_stage_payload(args.phone, media_selected)

    if args.dry_run:
        print("=" * 60)
        print("  PAYLOAD DE N8N SANDBOX DEV_STAGE (DRY-RUN)")
        print("=" * 60)
        # Mostrar versión truncada del base64 para legibilidad
        display_payload = dict(payload)
        display_payload["file_base64"] = display_payload["file_base64"][:40] + "... [TRUNCATED]"
        print(json.dumps(display_payload, indent=2))
        print("=" * 60)
        sys.exit(0)

    print(f"🚀 Enviando payload multimodal {media_selected} hacia {args.url}...")
    try:
        res = send_payload_to_stage_endpoint(payload, args.url)
        print("=" * 60)
        print("  RESPUESTA DEL SERVIDOR MULTIMODAL (:8025)")
        print("=" * 60)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        print("=" * 60)
    except urllib.error.URLError as e:
        logger.error(f"No se pudo conectar a {args.url}: {e.reason}")
        logger.info("Asegúrese de que el servidor esté activo ejecutando: python3 service/server.py --port 8025")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error inesperado al despachar petición: {e}")
        sys.exit(1)
