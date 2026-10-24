"""tests/test_quality_gatekeeper_10phases.py — Test de la Suite Decagonal de Calidad

Valida que el Guardián Decagonal evalúe exitosamente las 10 etapas del ciclo
de ingeniería (Analítica, Propuestas, Diseño, Consultas, Desarrollo, Pruebas,
Verificación, Ajustes, Comprobación, Auditoría y Certificación).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from quality_gatekeeper_10phases import QualityGatekeeper10Phases, run_self_verification  # noqa: E402


def test_quality_gatekeeper_self_verification():
    """Valida la auto-verificación formal del gatekeeper."""
    assert run_self_verification() is True


def test_quality_gatekeeper_all_phases_pass():
    """Valida que las 10 fases reporten estado aprobado (10/10 PASS)."""
    gk = QualityGatekeeper10Phases()
    report = gk.audit_all()
    assert report["all_passed"] is True, f"Fallo en fases: {report['phases']}"
    assert len(report["phases"]) == 10
    for phase_name, data in report["phases"].items():
        assert data["passed"] is True, f"Fase fallida: {phase_name} -> {data['detail']}"
