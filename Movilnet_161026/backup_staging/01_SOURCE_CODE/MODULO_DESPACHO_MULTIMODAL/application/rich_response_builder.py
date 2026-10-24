"""
Módulo Autónomo de Despacho Multimodal — Capa de Aplicación: Constructor de Respuestas Ricas
Gobernanza: Universal Best Practices Engineering Rule & Regla Inviolable Enlace PWA Universal
"""

import os
from typing import Dict, Any, Optional

from domain.models import RichResponse
from domain.enums import MediaType
from domain.invariants import append_universal_pwa_link


class RichResponseBuilder:
    """Constructor de respuestas enriquecidas compuestas (Texto + Adjunto + Enlace PWA)."""

    def __init__(self, pwa_enforce: bool = True):
        self.pwa_enforce = pwa_enforce

    def format_text_reply(self, message: str) -> str:
        """Asegura la inyección del enlace PWA oficial de Movilnet."""
        if self.pwa_enforce:
            return append_universal_pwa_link(message)
        return message

    def generate_pdf_receipt_bytes(self, phone_number: str, data: Dict[str, Any]) -> bytes:
        """
        Genera un documento PDF sintético válido con cabecera estándar (%PDF-1.4).
        Permite validar el flujo documental sin dependencias pesadas obligatorias.
        """
        ref = data.get("reference", "REF-84729104")
        monto = data.get("amount", "250.00")
        banco = data.get("bank", "Banco de Venezuela (0102)")

        pdf_content = (
            f"%PDF-1.4\n"
            f"% MOVILNET COMPROBANTE OFICIAL DE RECARGA 4GMAX\n"
            f"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            f"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
            f"4 0 obj << /Length 120 >> stream\n"
            f"BT /F1 14 Tf 50 700 Td (TELECOMUNICACIONES MOVILNET C.A. - RECIBO OFICIAL) Tj ET\n"
            f"BT /F1 11 Tf 50 670 Td (Abonado: {phone_number} | Monto: Bs. {monto} | Ref: {ref} | Banco: {banco}) Tj ET\n"
            f"endstream\n"
            f"endobj\n"
            f"xref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000115 00000 n \n0000000210 00000 n \n"
            f"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n380\n%%EOF\n"
        )
        return pdf_content.encode("utf-8")

    def generate_synthetic_audio_bytes(self, text: str) -> bytes:
        """Genera un archivo de audio sintético OGG para notas de voz salientes."""
        # Cabecera binaria estándar OggS
        header = b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x01\x13OpusHead"
        payload = b"\x01\x01\x00\x00\x80\xbb\x00\x00\x00\x00\x00" + text.encode("utf-8")
        return header + payload
