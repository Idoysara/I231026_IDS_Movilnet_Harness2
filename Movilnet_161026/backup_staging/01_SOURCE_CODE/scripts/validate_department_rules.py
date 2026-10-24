#!/usr/bin/env python3
"""
scripts/validate_department_rules.py — Validador Pre-Commit y CLI de Reglas Departamentales
==========================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal

Valida sintaxis, tipos e invariantes de negocio para los 5 catálogos departamentales
antes de permitir su carga en caliente en producción.
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.department_rule_engine import DepartmentRuleEngine, RULES_DIR


def audit_department_rules() -> Tuple[bool, List[str], Dict[str, Any]]:
    """Ejecuta una auditoría estricta de invariantes de negocio sobre los 5 catálogos."""
    issues = []
    engine = DepartmentRuleEngine.get_instance()
    success, msg, meta = engine.reload_rules()

    if not success:
        issues.append(f"Error crítico en recarga: {msg}")
        return False, issues, meta

    # Validaciones cruzadas de integridad
    snap = engine.get_snapshot()

    # 1. Comercial
    if len(snap.comercial.plans_catalog) < 3:
        issues.append("Comercial: Se requieren al menos 3 planes activos en el catálogo.")

    # 2. Finanzas
    c2p_rec = snap.finanzas.official_receiver_account
    if c2p_rec.get("receiver_phone") != "0424-1533712":
        issues.append(f"Finanzas: El teléfono receptor ({c2p_rec.get('receiver_phone')}) no coincide con 0424-1533712.")

    # 3. Atención
    if "saldo" not in snap.atencion.fastpath_intents:
        issues.append("Atención: Falta la intención crítica 'saldo' en fastpath_intents.")

    # 4. Seguridad
    if not snap.seguridad.zero_pii_policy.get("enforce_zero_pii"):
        issues.append("Seguridad: La política Zero-PII DEBE estar activada obligatoriamente.")

    # 5. NOC
    if not snap.noc.proactive_bulletins:
        issues.append("NOC: Debe registrarse al menos un boletín operativo o histórico.")

    is_clean = len(issues) == 0
    return is_clean, issues, meta


def main():
    parser = argparse.ArgumentParser(description="Validador Soberano de Reglas Departamentales Movilnet")
    parser.add_argument("--audit", action="store_true", help="Audita los 5 catálogos e imprime el informe formal")
    parser.add_argument("--test", action="store_true", help="Modo test con aserciones formales para CI/CD")
    parser.add_argument("--reload-api", action="store_true", help="Solicita recarga remota al endpoint /api/v1/rules/reload")
    parser.add_argument("--port", type=int, default=8010, help="Puerto del servicio local (default: 8010)")
    args = parser.parse_args()

    print("=" * 75)
    print("🏛️ VALIDADOR MAESTRO DE REGLAS DEPARTAMENTALES — PROTOCOLO DECAGONAL")
    print("=" * 75)

    is_clean, issues, meta = audit_department_rules()

    if is_clean:
        print("✅ ESTADO: TODOS LOS CATÁLOGOS APROBADOS (0 HALLAZGOS)")
        print(f"📦 Master SHA-256: {meta.get('master_hash', 'N/A')}")
        print(f"⚡ Latencia de Carga: {meta.get('duration_ms', 0)} ms")
        print("\n📊 Resumen de Componentes Cargados:")
        print(json.dumps(meta.get("rules_loaded", {}), indent=2))
    else:
        print("❌ ESTADO: SE DETECTARON INCONSISTENCIAS DE DOMINIO")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")

    if args.reload_api:
        import urllib.request
        url = f"http://localhost:{args.port}/api/v1/rules/reload"
        print(f"\n📡 Notificando al servicio en línea: {url}")
        try:
            req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                print(f"  ➔ Respuesta HTTP {resp.status}: {data.get('message')}")
        except Exception as e:
            print(f"  ⚠️ No se pudo comunicar con el servicio en puerto {args.port} ({e})")

    if args.test:
        assert is_clean, f"Falló la validación pre-commit de reglas: {issues}"
        print("\n🧪 Test de aserciones: 100% PASS.")


if __name__ == "__main__":
    main()
