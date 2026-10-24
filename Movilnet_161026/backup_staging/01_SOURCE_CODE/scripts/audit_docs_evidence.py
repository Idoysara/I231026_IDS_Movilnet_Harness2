#!/usr/bin/env python3
"""
scripts/audit_docs_evidence.py — Auditor ZH-MHEP de Documentos (Bitácora, Libro Maestro, STATE, README)
=====================================================================================================
Proyecto: AI_Movilnet_300926 — Gobernanza: rules/zero_hallucination_hard_evidence_rule.md

Controles (ambos son ERRORES que fallan la auditoría):
  C1  Números telefónicos venezolanos en documentos que NO existan en ninguna fuente dura
      (código, tests, JSON de workflows, SQLite). Excepción: líneas que documentan un
      incidente (contienen 'alucin', 'fantasma', 'OCR', 'purg').
  C2  Medianas de latencia de la matriz medida: cada `median_ms` guardado en
      reports/fastpath_latency_report.json debe aparecer textualmente en la bitácora,
      y el SHA-256 del reporte debe coincidir con el recalculado.

Alcance honesto: NO verifica cualquier cifra arbitraria; solo teléfonos y la matriz de latencia.

Uso:
    python scripts/audit_docs_evidence.py --audit     # imprime hallazgos, exit 1 si hay errores
    python scripts/audit_docs_evidence.py --test      # auto-verificación con aserciones
"""

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DOC_FILES = [
    "docs/BITACORA_MOVILNET.md",
    "docs/LIBRO_MAESTRO_BITACORA_Y_DOCUMENTOS.md",
    "docs/FASE_5_INTEGRACION_GOOGLE_SUITE_Y_N8N_MCP_EN_VIVO.md",
    "STATE.md",
    "README.md",
]
SOURCE_DIRS = ["api", "core", "db", "mcp", "reports", "scripts", "tests", "ui"]
SOURCE_EXT = {".py", ".json", ".sql", ".js", ".html"}
INCIDENT_WORDS = ("alucin", "fantasma", "ocr", "purg")
LATENCY_REPORT = PROJECT_ROOT / "reports/fastpath_latency_report.json"
BITACORA = PROJECT_ROOT / "docs/BITACORA_MOVILNET.md"

# 0412/0414/0416/0424/0426 + 7 dígitos, con prefijo país 58 opcional y separadores opcionales
PHONE_RE = re.compile(r"(?<!\d)(?:\+?58[- ]?)?0?(4(?:12|14|16|24|26))[- ]?(\d{3})[- ]?(\d{4})(?!\d)")


@dataclass(frozen=True)
class Finding:
    code: str
    file: str
    line: int
    detail: str


def normalize_phone(m: "re.Match[str]") -> str:
    """Normaliza a formato nacional 0XXXYYYYYYY (11 dígitos)."""
    return "0" + m.group(1) + m.group(2) + m.group(3)


def extract_phones(text: str) -> Set[str]:
    return {normalize_phone(m) for m in PHONE_RE.finditer(text)}


def collect_evidence_phones(root: Path = PROJECT_ROOT) -> Set[str]:
    """Teléfonos presentes en fuentes duras (no documentación)."""
    found: Set[str] = set()
    for d in SOURCE_DIRS:
        base = root / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in SOURCE_EXT and "venv" not in p.parts:
                try:
                    found |= extract_phones(p.read_text(encoding="utf-8", errors="ignore"))
                except OSError as exc:
                    print(f"[WARN] no se pudo leer {p}: {exc}", file=sys.stderr)
    for wf in (root / "api/n8n_workflows").glob("*.json"):
        found |= extract_phones(wf.read_text(encoding="utf-8", errors="ignore"))
    db = root / "db/local_movilnet.db"
    if db.exists():
        conn = sqlite3.connect(db)
        try:
            for (msisdn,) in conn.execute("SELECT msisdn FROM telco_lines"):
                found |= extract_phones(str(msisdn))
        except sqlite3.Error as exc:
            print(f"[WARN] SQLite telco_lines no consultable: {exc}", file=sys.stderr)
        finally:
            conn.close()
    return found


def audit_phones(doc_lines: Iterable[str], doc_name: str, evidence: Set[str]) -> List[Finding]:
    out: List[Finding] = []
    for i, line in enumerate(doc_lines, 1):
        low = line.lower()
        if any(w in low for w in INCIDENT_WORDS):
            continue
        for ph in sorted(extract_phones(line)):
            if ph not in evidence:
                out.append(Finding("C1_PHONE_WITHOUT_EVIDENCE", doc_name, i, ph))
    return out


def compute_seal(measurements: list) -> str:
    blob = json.dumps(measurements, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def audit_latency(report_path: Path, bitacora_text: str) -> List[Finding]:
    if not report_path.exists():
        return [Finding("C2_REPORT_MISSING", str(report_path.name), 0, "reporte de latencia no existe")]
    data = json.loads(report_path.read_text(encoding="utf-8"))
    out: List[Finding] = []
    if compute_seal(data["measurements"]) != data.get("sha256"):
        out.append(Finding("C2_SEAL_MISMATCH", report_path.name, 0, "SHA-256 no coincide con el contenido"))
    if data.get("sha256", "") not in bitacora_text:
        out.append(Finding("C2_SEAL_NOT_IN_BITACORA", "BITACORA_MOVILNET.md", 0, data.get("sha256", "")))
    for m in data["measurements"]:
        token = f"{m['median_ms']} ms"
        if token not in bitacora_text:
            out.append(Finding("C2_MEDIAN_NOT_IN_BITACORA", "BITACORA_MOVILNET.md", 0, f"{m['phone']}: {token}"))
    return out


def run_audit() -> List[Finding]:
    evidence = collect_evidence_phones()
    findings: List[Finding] = []
    for rel in DOC_FILES:
        p = PROJECT_ROOT / rel
        if p.exists():
            findings += audit_phones(p.read_text(encoding="utf-8").splitlines(), rel, evidence)
    findings += audit_latency(LATENCY_REPORT, BITACORA.read_text(encoding="utf-8"))
    return findings


def run_self_test() -> bool:
    # Extracción y normalización en todos los formatos
    assert extract_phones("0416-6251587 y +58 414 2650088 y 584142650088@s.whatsapp.net") == {
        "04166251587", "04142650088"}
    assert extract_phones("id 1234567890123") == set()
    # Un teléfono sin evidencia se marca; con evidencia no; en línea de incidente se exime
    ev = {"04166251587"}
    ghost = "0414" + "3301801"  # número sin evidencia (construido por partes a propósito)
    assert [f.detail for f in audit_phones(["bot 0416-6251587"], "x", ev)] == []
    assert [f.detail for f in audit_phones([f"abonado 0414-{ghost[4:]}"], "x", ev)] == [ghost]
    assert audit_phones([f"alucinación 0414-{ghost[4:]} purgada"], "x", ev) == []
    # Sello: coincide / no coincide
    ms = [{"phone": "1", "median_ms": 0.1}]
    assert compute_seal(ms) == compute_seal(list(ms))
    assert compute_seal(ms) != compute_seal([{"phone": "1", "median_ms": 0.2}])
    # Latencia: valor ausente en bitácora se detecta (reporte temporal)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rp = Path(td) / "r.json"
        rp.write_text(json.dumps({"measurements": ms, "sha256": compute_seal(ms)}))
        codes = {f.code for f in audit_latency(rp, "sin cifras")}
        assert "C2_MEDIAN_NOT_IN_BITACORA" in codes and "C2_SEAL_NOT_IN_BITACORA" in codes
        ok = audit_latency(rp, f"0.1 ms {compute_seal(ms)}")
        assert ok == [], ok
        rp.write_text(json.dumps({"measurements": ms, "sha256": "0" * 64}))
        assert "C2_SEAL_MISMATCH" in {f.code for f in audit_latency(rp, "x")}
    print("✅ [AUDITOR DOCS ZH-MHEP]: auto-verificación 100% OK")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Auditor ZH-MHEP de documentos")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    if args.test:
        run_self_test()
    elif args.audit:
        res = run_audit()
        for f in res:
            print(f"❌ {f.code} {f.file}:{f.line} -> {f.detail}")
        print(f"\nHallazgos: {len(res)}")
        sys.exit(1 if res else 0)
    else:
        ap.print_help()
