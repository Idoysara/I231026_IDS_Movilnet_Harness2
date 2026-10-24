"""
Máquina de Estados Finitos (FSM) para el Ciclo de Vida del Cupón en Cazador de Ofertas.
Garantiza que ningún cupón pueda canjearse dos veces ni transicionar ilegalmente.
"""
from typing import Dict, Set
from enum import Enum

class EstadoCupon(str, Enum):
    """Estados finitos del ciclo de vida de un cupón."""
    EMITIDO = "EMITIDO"
    RESERVADO = "RESERVADO"
    CANJEADO = "CANJEADO"
    EXPIRADO = "EXPIRADO"

class IllegalCouponStateTransitionError(Exception):
    """Lanzada cuando se intenta una transición prohibida en la FSM."""
    pass

class CouponFSM:
    TRANSICIONES_LEGALES: Dict[EstadoCupon, Set[EstadoCupon]] = {
        EstadoCupon.EMITIDO: {EstadoCupon.RESERVADO, EstadoCupon.EXPIRADO, EstadoCupon.CANJEADO},
        EstadoCupon.RESERVADO: {EstadoCupon.CANJEADO, EstadoCupon.EXPIRADO},
        EstadoCupon.CANJEADO: set(),  # Estado final inmutable
        EstadoCupon.EXPIRADO: set()   # Estado final inmutable
    }

    @classmethod
    def validar_transicion(cls, estado_actual: EstadoCupon, nuevo_estado: EstadoCupon) -> bool:
        if nuevo_estado not in cls.TRANSICIONES_LEGALES.get(estado_actual, set()):
            raise IllegalCouponStateTransitionError(
                f"Transición prohibida en FSM: No se puede pasar de {estado_actual.value} a {nuevo_estado.value}."
            )
        return True
