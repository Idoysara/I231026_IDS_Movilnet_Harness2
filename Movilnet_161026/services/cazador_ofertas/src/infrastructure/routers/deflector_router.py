"""
Router para Webhooks de Deflexión Conversacional (WhatsApp / SMS SMPP) y Validación de Magic Links Zero-Rating.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Response, status

from ..dependencies import get_deflector_service
from ..deflector.magic_link_service import MagicLinkService
from ..dtos.deflector_dtos import (
    MensajeEntranteDTO,
    DeflectorResponseDTO,
    VerificarLinkResponseDTO
)

router = APIRouter(prefix="/api/deflector", tags=["Deflector de Conectividad & Zero-Rating"])

@router.post("/whatsapp", response_model=DeflectorResponseDTO)
def deflector_webhook_whatsapp(
    payload: MensajeEntranteDTO,
    deflector: MagicLinkService = Depends(get_deflector_service)
) -> DeflectorResponseDTO:
    """
    Webhook receptor para conversaciones de WhatsApp.
    Interpreta el mensaje o ubicación compartida, busca ofertas verificadas (Grounding B2C Cero Alucinación)
    y responde con un mensaje enriquecido con Magic Link Zero-Rating.
    """
    resultado = deflector.procesar_deflexion_whatsapp(
        remitente=payload.remitente,
        mensaje=payload.mensaje,
        lat=payload.ubicacion_lat,
        lon=payload.ubicacion_lon
    )
    return DeflectorResponseDTO(**resultado)

@router.post("/sms-smpp", response_model=DeflectorResponseDTO)
def deflector_webhook_sms_smpp(
    payload: MensajeEntranteDTO,
    deflector: MagicLinkService = Depends(get_deflector_service)
) -> DeflectorResponseDTO:
    """
    Webhook receptor para pasarelas SMS SMPP.
    Genera un SMS conciso (<160 car.) con Magic Link Zero-Rating para desviar al usuario a la PWA.
    """
    resultado = deflector.procesar_deflexion_sms(
        remitente=payload.remitente,
        mensaje=payload.mensaje
    )
    return DeflectorResponseDTO(**resultado)

@router.post("/telegram", response_model=DeflectorResponseDTO)
def deflector_webhook_telegram(
    payload: MensajeEntranteDTO,
    deflector: MagicLinkService = Depends(get_deflector_service)
) -> DeflectorResponseDTO:
    """
    Webhook receptor para bots de Telegram.
    Soporta ubicación compartida, palabras clave de ofertas y botón WebApp Zero-Rating.
    """
    resultado = deflector.procesar_deflexion_telegram(
        remitente=payload.remitente,
        mensaje=payload.mensaje,
        lat=payload.ubicacion_lat,
        lon=payload.ubicacion_lon
    )
    return DeflectorResponseDTO(**resultado)

@router.post("/pwa", response_model=DeflectorResponseDTO)
def deflector_webhook_pwa(
    payload: MensajeEntranteDTO,
    deflector: MagicLinkService = Depends(get_deflector_service)
) -> DeflectorResponseDTO:
    """
    Endpoint para eventos y consultas directas desde la PWA Mobile-First.
    """
    resultado = deflector.procesar_deflexion_pwa(
        remitente=payload.remitente,
        mensaje=payload.mensaje,
        lat=payload.ubicacion_lat,
        lon=payload.ubicacion_lon
    )
    return DeflectorResponseDTO(**resultado)

@router.post("/n8n", response_model=DeflectorResponseDTO)
def deflector_webhook_n8n_gateway(
    payload: MensajeEntranteDTO,
    deflector: MagicLinkService = Depends(get_deflector_service)
) -> DeflectorResponseDTO:
    """
    Gateway Unificado Omnicanal para n8n Workflow Automation.
    Procesa solicitudes de WhatsApp, Telegram, SMS o PWA despachadas por n8n.
    """
    resultado = deflector.procesar_deflexion_omnicanal(
        canal=payload.canal,
        remitente=payload.remitente,
        mensaje=payload.mensaje,
        lat=payload.ubicacion_lat,
        lon=payload.ubicacion_lon
    )
    return DeflectorResponseDTO(**resultado)

@router.get("/verificar-link", response_model=VerificarLinkResponseDTO)
def verificar_magic_link(
    response: Response,
    msisdn: str = Query(..., description="Número del suscriptor Movilnet"),
    exp: int = Query(..., description="Timestamp de expiración Unix"),
    sig: str = Query(..., description="Firma criptográfica HMAC"),
    oferta: Optional[str] = Query(None, description="ID de la oferta asociada opcional"),
    deflector: MagicLinkService = Depends(get_deflector_service)
) -> VerificarLinkResponseDTO:
    """
    Valida la vigencia y autenticidad del Magic Link firmado e inyecta las cabeceras HTTP de Zero-Rating.
    """
    valido, motivo = deflector.verificar_magic_link(
        msisdn=msisdn,
        exp_timestamp=exp,
        firma=sig,
        oferta_id=oferta
    )

    # Inyectar cabeceras oficiales Zero-Rating de Movilnet
    if valido:
        headers_zr = deflector.obtener_headers_zero_rating(msisdn)
        for k, v in headers_zr.items():
            response.headers[k] = v
        header_summary = "X-Movilnet-Zero-Rating: active"
    else:
        response.status_code = status.HTTP_403_FORBIDDEN
        header_summary = "X-Movilnet-Zero-Rating: rejected"

    return VerificarLinkResponseDTO(
        valido=valido,
        msisdn=msisdn,
        oferta_id=oferta,
        zero_rating_header=header_summary,
        mensaje=motivo
    )
