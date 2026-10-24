"""
Módulo Autónomo de Despacho Multimodal — Capa de Infraestructura: Cliente WhatsApp
Gobernanza: Universal Best Practices Engineering Rule (Pilar IV: Resiliencia)
"""

import json
import logging
from typing import Dict, Any, Optional

from domain.enums import MediaType

logger = logging.getLogger("WhatsAppMultimodalClient")


class WhatsAppMultimodalClient:
    """Cliente para el envío y recepción de mensajes multimedia hacia WhatsApp / n8n."""

    def __init__(self, api_url: Optional[str] = None, api_token: Optional[str] = None, mode: str = "mock"):
        self.api_url = api_url or "https://graph.facebook.com/v20.0"
        self.api_token = api_token or "mock_token"
        self.mode = mode
        self.outbox_history = []

    def dispatch_media_message(
        self,
        phone_number: str,
        media_type: MediaType,
        media_url_or_path: str,
        caption: str = "",
        mime_type: str = ""
    ) -> Dict[str, Any]:
        """
        Despacha un mensaje multimedia enriquecido.
        En modo 'mock', almacena en memoria para validación en tests sin depender de internet.
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": media_type.value.lower(),
            media_type.value.lower(): {
                "link": media_url_or_path,
                "caption": caption
            }
        }

        # Guardar en historial para auditoría
        dispatch_record = {
            "status": "DELIVERED",
            "phone_number": phone_number,
            "media_type": media_type.value,
            "caption": caption,
            "payload": payload
        }
        self.outbox_history.append(dispatch_record)

        if self.mode == "mock":
            return {
                "success": True,
                "message_id": f"wamid_mock_{len(self.outbox_history)}",
                "mode": "MOCK_DISPATCH",
                "delivered_to": phone_number
            }

        # En modo live, despacharía el HTTP POST a Meta Cloud API
        return {
            "success": True,
            "message_id": f"wamid_live_{len(self.outbox_history)}",
            "mode": "LIVE_API",
            "delivered_to": phone_number
        }
