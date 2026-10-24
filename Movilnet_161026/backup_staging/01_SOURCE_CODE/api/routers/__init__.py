#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api.routers — Capa de Enrutamiento de Dominio Desacoplada y Modular
=============================================================================
Telecomunicaciones Movilnet C.A. — Core ODA / PWA 4GMAX
"""

from api.routers.base_router import (
    BaseDomainRouter,
    RouteResult,
    cors_headers,
    error_response,
    json_response,
    parse_json_body,
)
from api.routers.core_router import CoreRouter
from api.routers.telco_router import TelcoRouter
from api.routers.fintech_router import FintechRouter
from api.routers.agents_router import AgentsRouter
from api.routers.webhooks_router import WebhooksRouter
from api.routers.noc_router import NocRouter
from api.routers.cazador_router import CazadorRouter

__all__ = [
    "BaseDomainRouter",
    "RouteResult",
    "cors_headers",
    "error_response",
    "json_response",
    "parse_json_body",
    "CoreRouter",
    "TelcoRouter",
    "FintechRouter",
    "AgentsRouter",
    "WebhooksRouter",
    "NocRouter",
    "CazadorRouter",
]
