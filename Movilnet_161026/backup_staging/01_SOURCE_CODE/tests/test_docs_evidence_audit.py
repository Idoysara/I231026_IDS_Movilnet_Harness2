"""tests/test_docs_evidence_audit.py — Certifica los guardarraíles ZH-MHEP (Pilar V).

Valida: auto-verificación del auditor, 0 hallazgos en documentos reales,
medición de latencia en modo determinista y presencia de la regla local.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import audit_docs_evidence as audit  # noqa: E402
import measure_fastpath_latency as lat  # noqa: E402


def test_auditor_self_verification():
    assert audit.run_self_test() is True


def test_documents_have_zero_unsupported_claims():
    findings = audit.run_audit()
    assert findings == [], [f"{f.code} {f.file}:{f.line} {f.detail}" for f in findings]


def test_latency_measurer_self_verification():
    assert lat.run_self_test() is True


def test_local_rule_registered_always_on():
    rule = PROJECT_ROOT / ".agents/rules/zh-mhep-zero-hallucination.md"
    if not rule.exists():
        rule = PROJECT_ROOT.parent / ".agents/rules/zh-mhep-zero-hallucination.md"
    text = rule.read_text(encoding="utf-8")
    assert "trigger: always_on" in text
    assert "audit_docs_evidence.py" in text
