#!/usr/bin/env python3
"""
api/service_constants.py — Constantes Compartidas del Microservicio (Dominio Puro)
=================================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilar I: Dominio sin dependencias)
Capítulo: 216 — Refactorización Hexagonal de api/service.py (Fase 1)

Responsabilidad ÚNICA: ser la fuente de verdad de las constantes del servicio para que
`service.py`, `openapi_contract.py` y los routers las importen SIN dependencias circulares.
No importa ningún módulo del proyecto (cero acoplamiento).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

SERVICE_NAME: Final[str] = "Movilnet Telco & FinTech API Service"
SERVICE_VERSION: Final[str] = "1.0.0"
BCV_OFFICIAL_RATE_DEFAULT: Final[float] = 36.85
OPENAPI_SPEC_PATH: Final[Path] = Path(__file__).resolve().parent / "openapi.json"


def _self_test() -> bool:
    """Auto-verificación de invariantes de las constantes."""
    assert isinstance(SERVICE_NAME, str) and SERVICE_NAME.strip(), "SERVICE_NAME vacío"
    assert SERVICE_NAME == "Movilnet Telco & FinTech API Service", "SERVICE_NAME alterado"
    assert SERVICE_VERSION.count(".") == 2, "SERVICE_VERSION debe ser semver X.Y.Z"
    assert all(p.isdigit() for p in SERVICE_VERSION.split(".")), "SERVICE_VERSION no numérico"
    assert BCV_OFFICIAL_RATE_DEFAULT > 0.0, "Tasa BCV debe ser positiva"
    assert OPENAPI_SPEC_PATH.name == "openapi.json", "Ruta de contrato inesperada"
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Constantes compartidas del microservicio Movilnet")
    parser.add_argument("--test", action="store_true", help="Auto-verificación de invariantes")
    args = parser.parse_args()
    if args.test:
        _self_test()
        print("✅ [TEST PASS] service_constants: todos los invariantes aprobados (100%).")
        sys.exit(0)
    print(f"{SERVICE_NAME} v{SERVICE_VERSION} | BCV={BCV_OFFICIAL_RATE_DEFAULT} | contrato={OPENAPI_SPEC_PATH}")
