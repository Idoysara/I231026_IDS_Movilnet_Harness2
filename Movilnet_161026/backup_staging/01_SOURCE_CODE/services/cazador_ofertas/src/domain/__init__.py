"""
Paquete de Dominio Puro para Cazador de Ofertas Movilnet.
"""
from .entities import (
    Comercio,
    Oferta,
    Cupon,
    TransaccionBilling,
    EstadoCupon,
    TierComercio,
    NivelUsuario
)
from .fsm import CouponFSM, IllegalCouponStateTransitionError
from .invariants import CazadorInvariants, DomainInvariantViolationError

__all__ = [
    "Comercio",
    "Oferta",
    "Cupon",
    "TransaccionBilling",
    "EstadoCupon",
    "TierComercio",
    "NivelUsuario",
    "CouponFSM",
    "IllegalCouponStateTransitionError",
    "CazadorInvariants",
    "DomainInvariantViolationError",
]
