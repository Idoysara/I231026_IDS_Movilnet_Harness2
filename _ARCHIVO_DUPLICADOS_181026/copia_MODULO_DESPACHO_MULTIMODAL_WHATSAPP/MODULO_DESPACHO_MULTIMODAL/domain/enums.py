"""
Módulo Autónomo de Despacho Multimodal — Capa de Dominio: Enums
Gobernanza: Universal Best Practices Engineering Rule (Pilares I y III)
"""

from enum import Enum


class MediaType(str, Enum):
    AUDIO = "AUDIO"
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"
    VIDEO = "VIDEO"


class MediaDirection(str, Enum):
    INBOUND = "INBOUND"    # Recibido desde el abonado
    OUTBOUND = "OUTBOUND"  # Despachado por el asistente


class VaultStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXCEEDED = "EXCEEDED"
    SUSPENDED = "SUSPENDED"


class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class AnalysisIntent(str, Enum):
    CONSULTA_SALDO = "CONSULTA_SALDO"
    PAGO_C2P = "PAGO_C2P"
    REPORTE_FALLA = "REPORTE_FALLA"
    PORTABILIDAD = "PORTABILIDAD"
    SOPORTE_GENERAL = "SOPORTE_GENERAL"
    DESCONOCIDO = "DESCONOCIDO"
