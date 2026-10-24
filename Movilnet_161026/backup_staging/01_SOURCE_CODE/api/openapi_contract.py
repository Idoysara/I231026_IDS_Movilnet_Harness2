#!/usr/bin/env python3
"""
api/openapi_contract.py — Contrato OpenAPI 3.1.0 Externalizado (Lectura Bajo Demanda)
====================================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilares I, II, III, IV, V)
Capítulo: 216 — Refactorización Hexagonal de api/service.py (Fase 1)

Problema resuelto:
    El diccionario OpenAPI (~1.246 líneas) vivía embebido en `service.py` y permanecía
    residente en el AST/RAM del proceso durante toda su vida útil.

Solución:
    La especificación es ahora un ARCHIVO ESTÁTICO (`api/openapi.json`, fuente de verdad)
    que se lee únicamente cuando alguien consulta `/openapi.json` o `/docs`.
    RAM residente del contrato en reposo: 0 bytes (no hay caché en proceso).

Contratos preservados (compatibilidad 100% hacia atrás):
    - get_openapi_specification() -> Dict[str, Any]   (objeto fresco en cada llamada)
    - export_openapi_json(file_path=None) -> Path
    - OPENAPI_SPEC_PATH (re-exportado desde service_constants)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.service_constants import OPENAPI_SPEC_PATH, SERVICE_VERSION

logger = logging.getLogger("MovilnetAPIService.openapi")


class OpenAPIContractError(RuntimeError):
    """Violación de invariante del contrato OpenAPI (archivo ausente, corrupto o inválido)."""


def _validate_contract(spec: Any, source: Path) -> Dict[str, Any]:
    """Guarda de invariantes en la frontera: rechaza un contrato malformado de inmediato."""
    if not isinstance(spec, dict):
        raise OpenAPIContractError(f"Contrato inválido en {source}: la raíz debe ser un objeto JSON.")
    version = spec.get("openapi")
    if not isinstance(version, str) or not version.startswith("3.1"):
        raise OpenAPIContractError(f"Contrato inválido en {source}: 'openapi' debe ser 3.1.x (recibido: {version!r}).")
    info = spec.get("info")
    if not isinstance(info, dict):
        raise OpenAPIContractError(f"Contrato inválido en {source}: falta el objeto 'info'.")
    paths = spec.get("paths")
    if not isinstance(paths, dict) or not paths:
        raise OpenAPIContractError(f"Contrato inválido en {source}: 'paths' debe ser un objeto no vacío.")
    return spec


def get_openapi_specification(contract_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Retorna la especificación OpenAPI 3.1.0 leyéndola de disco bajo demanda.

    Cada llamada devuelve un objeto NUEVO (semántica idéntica a la función embebida original),
    por lo que el llamante puede mutarlo sin contaminar otras peticiones.
    `info.version` se inyecta desde SERVICE_VERSION para mantener una única fuente de verdad.
    """
    path = contract_path or OPENAPI_SPEC_PATH
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        logger.error("Contrato OpenAPI ausente: %s", path)
        raise OpenAPIContractError(f"Contrato OpenAPI no encontrado: {path}") from exc
    except OSError as exc:
        logger.error("Error de E/S leyendo contrato OpenAPI %s: %s", path, exc)
        raise OpenAPIContractError(f"No se pudo leer el contrato OpenAPI {path}: {exc}") from exc

    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Contrato OpenAPI corrupto en %s: %s", path, exc)
        raise OpenAPIContractError(f"Contrato OpenAPI corrupto en {path}: {exc}") from exc

    _validate_contract(spec, path)
    spec["info"]["version"] = SERVICE_VERSION
    return spec


def export_openapi_json(file_path: Optional[Path] = None) -> Path:
    """
    Serializa la especificación OpenAPI 3.1.0 a un archivo JSON en disco (escritura ATÓMICA).

    - Si el destino es el propio contrato fuente: valida y retorna sin reescribir (idempotente,
      evita corromper el archivo que otros hilos pueden estar leyendo).
    - Si el destino es otro archivo: escribe a un temporal y lo renombra atómicamente.
    """
    target = file_path or OPENAPI_SPEC_PATH
    spec = get_openapi_specification()

    try:
        if target.exists() and target.resolve() == OPENAPI_SPEC_PATH.resolve():
            return target
    except OSError as exc:
        logger.warning("No se pudo resolver la ruta de exportación %s: %s", target, exc)

    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=".openapi_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        os.replace(tmp_name, target)
    except OSError as exc:
        logger.error("Fallo exportando contrato OpenAPI a %s: %s", target, exc)
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise OpenAPIContractError(f"No se pudo exportar el contrato a {target}: {exc}") from exc
    return target


# ==============================================================================
# CLI Y AUTO-VERIFICACIÓN FORMAL (Pilar II: Autonomía de Módulos)
# ==============================================================================

def _self_test() -> bool:
    """Suite de auto-verificación del contrato externalizado."""
    # 1. Carga real y paridad estructural con el contrato certificado (25 rutas / 31 esquemas)
    spec = get_openapi_specification()
    assert spec["openapi"].startswith("3.1"), "Versión OpenAPI inesperada"
    assert len(spec["paths"]) == 25, f"Rutas esperadas 25, recibidas {len(spec['paths'])}"
    assert len(spec["components"]["schemas"]) == 31, "Esquemas esperados 31"
    assert spec["info"]["version"] == SERVICE_VERSION, "Versión no inyectada"
    for required in ("/health", "/openapi.json", "/api/v1/status", "/api/v1/payments/c2p"):
        assert required in spec["paths"], f"Ruta obligatoria ausente: {required}"

    # 2. Semántica de objeto fresco: mutar una copia no contamina la siguiente lectura
    spec["paths"].clear()
    assert len(get_openapi_specification()["paths"]) == 25, "La especificación no es un objeto fresco"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # 3. Archivo ausente -> error tipado
        try:
            get_openapi_specification(tmp_dir / "no_existe.json")
            raise AssertionError("Debió fallar por archivo ausente")
        except OpenAPIContractError:
            pass

        # 4. JSON corrupto (payload malformado) -> error tipado
        bad = tmp_dir / "corrupto.json"
        bad.write_text("{ esto no es json", encoding="utf-8")
        try:
            get_openapi_specification(bad)
            raise AssertionError("Debió fallar por JSON corrupto")
        except OpenAPIContractError:
            pass

        # 5. Invariantes de dominio: versión incorrecta, sin paths, raíz no objeto
        for label, payload in (
            ("version 2.0", {"openapi": "2.0", "info": {}, "paths": {"/x": {}}}),
            ("sin paths", {"openapi": "3.1.0", "info": {}, "paths": {}}),
            ("sin info", {"openapi": "3.1.0", "paths": {"/x": {}}}),
            ("raiz lista", [1, 2, 3]),
        ):
            p = tmp_dir / "inv.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            try:
                get_openapi_specification(p)
                raise AssertionError(f"Debió rechazar contrato inválido: {label}")
            except OpenAPIContractError:
                pass

        # 6. Exportación atómica a otro destino: round-trip idéntico y sin temporales residuales
        out = export_openapi_json(tmp_dir / "export" / "copia.json")
        assert json.loads(out.read_text(encoding="utf-8")) == get_openapi_specification(), "Exportación difiere"
        assert not list(out.parent.glob(".openapi_*.tmp")), "Quedaron archivos temporales"

    # 7. Exportar sobre el propio contrato es idempotente (no altera el archivo fuente)
    before = OPENAPI_SPEC_PATH.read_bytes()
    export_openapi_json()
    assert OPENAPI_SPEC_PATH.read_bytes() == before, "Exportar alteró el contrato fuente"
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Contrato OpenAPI 3.1.0 externalizado (Movilnet Core)")
    parser.add_argument("--test", action="store_true", help="Auto-verificación formal con aserciones")
    parser.add_argument("--stats", action="store_true", help="Muestra estadísticas del contrato")
    args = parser.parse_args()

    if args.test:
        _self_test()
        print("✅ [TEST PASS] openapi_contract: 7 grupos de invariantes aprobados (100%).")
        sys.exit(0)
    if args.stats:
        s = get_openapi_specification()
        print(f"OpenAPI {s['openapi']} | rutas={len(s['paths'])} | esquemas={len(s['components']['schemas'])} "
              f"| bytes={OPENAPI_SPEC_PATH.stat().st_size}")
        sys.exit(0)
    parser.print_help()
