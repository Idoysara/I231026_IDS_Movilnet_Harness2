#!/usr/bin/env python3
"""
scripts/verify_zero_hallucination_compliance.py — Auditor de Evidencia Dura y Anti-Alucinación
==============================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Protocolo ZH-MHEP (rules/zero_hallucination_hard_evidence_rule.md)

Funcionalidad:
1. Audita la presencia de datos fantasma o alucinados en bases de datos y código.
2. Comprueba que los payloads de prueba provengan al 100% de evidencia matemática dura (JSON de API).
3. Purga registros falsos en SQLite y certifica el consenso.
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PHANTOM_NAMES = ["Franclim Arvelo"]
PHANTOM_PHONES = ["04143301801", "584143301801"]
GROUND_TRUTH_PHONE = "04160000001"
GROUND_TRUTH_NAME = "Francisco Landaeta"

try:
    from core.system_config import SystemConfigManager
    _active_bot = SystemConfigManager.get_active_bot_phone()
    CANONICAL_BOT_SENDER = _active_bot.whatsapp_jid
    CANONICAL_BOT_PHONE = _active_bot.national_with_zero
    ALLOWED_BOT_SENDERS = SystemConfigManager.get_allowed_bot_senders()
except Exception:
    CANONICAL_BOT_SENDER = "584241533712@s.whatsapp.net"
    CANONICAL_BOT_PHONE = "04241533712"
    ALLOWED_BOT_SENDERS = {"584241533712@s.whatsapp.net"}

LIVE_WORKFLOW_FILE = PROJECT_ROOT / "api/n8n_workflows/viki_lpgtec_v2_ids_live.json"
DB_FILE = PROJECT_ROOT / "db/local_movilnet.db"


def audit_workflow_evidence() -> Dict[str, Any]:
    """Valida que el archivo JSON descargado de la API n8n coincida con los datos base."""
    if not LIVE_WORKFLOW_FILE.exists():
        return {"status": "error", "message": "No se encontró el archivo de workflow en vivo."}

    with open(LIVE_WORKFLOW_FILE, "r", encoding="utf-8") as f:
        wf = json.load(f)

    pin = wf.get("pinData", {}).get("Webhook", [{}])[0].get("json", {}).get("body", {})
    actual_sender = pin.get("sender")
    actual_customer = pin.get("data", {}).get("key", {}).get("remoteJid")
    actual_name = pin.get("data", {}).get("pushName")
    actual_msg = pin.get("data", {}).get("message", {}).get("conversation")

    sender_ok = actual_sender in ALLOWED_BOT_SENDERS or actual_sender == CANONICAL_BOT_SENDER
    customer_ok = actual_customer == "584160000001@s.whatsapp.net"
    name_ok = actual_name == "Francisco Landaeta"
    msg_ok = actual_msg == "Calcular diferencial cambiario"

    return {
        "status": "success" if (sender_ok and customer_ok and name_ok and msg_ok) else "discrepancy",
        "bot_line": actual_sender,
        "customer_line": actual_customer,
        "customer_name": actual_name,
        "customer_message": actual_msg,
        "verified_against_json": True
    }


def purge_phantom_records() -> Dict[str, Any]:
    """Elimina registros fantasma de la base de datos local SQLite."""
    if not DB_FILE.exists():
        return {"status": "error", "message": "Base de datos no encontrada."}

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    deleted_lines = 0
    deleted_subs = 0

    try:
        # 1. Buscar si existe la línea fantasma
        for p in PHANTOM_PHONES:
            cur.execute("SELECT subscriber_id FROM telco_lines WHERE msisdn = ?", (p,))
            rows = cur.fetchall()
            for r in rows:
                sub_id = r[0]
                cur.execute("DELETE FROM balances_and_quotas WHERE msisdn = ?", (p,))
                cur.execute("DELETE FROM telco_lines WHERE msisdn = ?", (p,))
                cur.execute("DELETE FROM subscribers WHERE id = ?", (sub_id,))
                deleted_lines += 1
                deleted_subs += 1

        conn.commit()
    finally:
        conn.close()

    # 2. Asegurar que Francisco Landaeta (Dato Real) exista en la base de datos
    from db.repository import MovilnetRepository
    repo = MovilnetRepository()
    existing_real = repo.get_subscriber_by_msisdn(GROUND_TRUTH_PHONE)
    if not existing_real:
        repo.create_subscriber_with_line(
            cid="V-14265008",
            msisdn=GROUND_TRUTH_PHONE,
            plan_id="PLAN-4G-INTELIPLAN-10GB",
            customer_type="NATURAL"
        )

    return {
        "status": "success",
        "deleted_phantoms": deleted_lines,
        "real_subscriber_seeded": GROUND_TRUTH_PHONE
    }


def scan_for_phantoms_in_code() -> List[str]:
    """Escanea el código fuente buscando referencias a los datos fantasma."""
    findings = []
    target_dirs = ["core", "scripts", "api/agents", "tests"]
    for d in target_dirs:
        dir_path = PROJECT_ROOT / d
        if not dir_path.exists():
            continue
        for root, _, files in os.walk(dir_path):
            for file in files:
                if not file.endswith(".py"):
                    continue
                file_path = Path(root) / file
                # Excluir el propio script de auditoría que define las constantes de búsqueda
                if file_path.name == "verify_zero_hallucination_compliance.py":
                    continue
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for ph in PHANTOM_NAMES + PHANTOM_PHONES:
                        if ph in content:
                            findings.append(f"{file_path.relative_to(PROJECT_ROOT)}: contiene '{ph}'")
    return findings


def run_self_verification() -> bool:
    """Ejecuta la suite de verificación formal de la regla anti-alucinación."""
    rule_file = PROJECT_ROOT / "rules/zero_hallucination_hard_evidence_rule.md"
    if not rule_file.exists():
        rule_file = PROJECT_ROOT / ".agents/rules/zh-mhep-zero-hallucination.md"
    assert rule_file.exists(), "La regla formal ZH-MHEP debe existir en rules/ o .agents/rules/"

    # 2. Documento de incidente existe
    incident_file = PROJECT_ROOT / "docs/REGISTRO_FORENSE_ALUCINACIONES.md"
    assert incident_file.exists(), "El registro forense de alucinaciones debe existir en docs/"

    # 3. Purgar base de datos
    purge_res = purge_phantom_records()
    assert purge_res["status"] == "success"

    # 4. Validar JSON de producción
    evidence = audit_workflow_evidence()
    assert evidence["status"] == "success"
    assert evidence["customer_name"] == GROUND_TRUTH_NAME
    assert "584241533712" in evidence["bot_line"] or "58416" in evidence["bot_line"]
    assert evidence["customer_line"] == "584160000001@s.whatsapp.net"

    # 5. Validar que no existen alucinaciones en el código ni tests
    phantoms = scan_for_phantoms_in_code()
    assert len(phantoms) == 0, f"Alucinaciones detectadas en código: {phantoms}"

    print("✅ [AUDITORÍA ANTI-ALUCINACIÓN]: Todos los invariantes de evidencia dura fueron 100% verificados.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auditor y Certificador de Evidencia Dura Anti-Alucinación")
    parser.add_argument("--test", action="store_true", help="Ejecutar suite de auto-verificación")
    parser.add_argument("--audit", action="store_true", help="Escanear evidencias y base de datos")
    parser.add_argument("--purge", action="store_true", help="Purgar registros fantasma en la BD")
    args = parser.parse_args()

    if args.test:
        run_self_verification()
    elif args.audit:
        wf_ev = audit_workflow_evidence()
        phantoms = scan_for_phantoms_in_code()
        print("\n🔍 REPORTE DE EVIDENCIA EN WORKFLOW:")
        print(json.dumps(wf_ev, indent=2))
        print(f"\n🔍 ALUCINACIONES DETECTADAS EN CÓDIGO ({len(phantoms)}):")
        for p in phantoms:
            print(f"  ❌ {p}")
        if not phantoms:
            print("  🟢 Cero alucinaciones detectadas en código activo.")
    elif args.purge:
        res = purge_phantom_records()
        print(json.dumps(res, indent=2))
    else:
        parser.print_help()
