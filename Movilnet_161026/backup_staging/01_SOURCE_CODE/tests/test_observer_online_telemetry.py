#!/usr/bin/env python3
"""
tests/test_observer_online_telemetry.py — Suite de Pruebas del Observador de Telemetría E2E
===========================================================================================
Valida la auditoría de los 5 eslabones y generación de reportes con sellos criptográficos.
"""

import sys
import json
from pathlib import Path
try:
    import pytest
except ImportError:
    pytest = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.observer_online_telemetry import (
    OnlineTelemetryObserver,
    HopTelemetry,
    OnlineEcosystemReport,
    ExecutionAuditSummary,
    run_self_test
)


class TestObserverOnlineTelemetry:
    """Batería de validación para el observador continuo del ecosistema."""

    def test_observer_self_test(self):
        """Verifica la auto-verificación formal del módulo."""
        assert run_self_test() is True

    def test_all_5_hops_evaluated(self):
        """Verifica que los 5 eslabones estén presentes y tipados."""
        obs = OnlineTelemetryObserver()
        report = obs.generate_full_report()

        assert report.total_hops_evaluated == 5
        assert len(report.hops) == 5
        hop_names = [h.name for h in report.hops]
        assert any("Ingesta" in n for n in hop_names)
        assert any("Orquestador n8n" in n for n in hop_names)
        assert any("Túnel Seguro" in n for n in hop_names)
        assert any("Motor Core ODA" in n for n in hop_names)
        assert any("Despacho WhatsApp" in n for n in hop_names)

    def test_recent_executions_forensic_integrity(self):
        """Verifica que las ejecuciones auditadas incluyan 9644, 9643, 9642, 9640, 9638, 9637, 9636, 9635 y 9623."""
        obs = OnlineTelemetryObserver()
        report = obs.generate_full_report()

        exec_ids = [e.execution_id for e in report.recent_executions]
        assert "9644" in exec_ids
        assert "9643" in exec_ids
        assert "9642" in exec_ids
        assert "9640" in exec_ids
        assert "9638" in exec_ids
        assert "9637" in exec_ids
        assert "9636" in exec_ids
        assert "9635" in exec_ids
        assert "9623" in exec_ids

        # Verificar que la ejecución 9623 sea de Francisco Landaeta
        e9623 = next(e for e in report.recent_executions if e.execution_id == "9623")
        assert e9623.sender_name == "Francisco Landaeta"
        assert e9623.sender_phone == "0414-2650088"

    def test_report_persistence_and_seal(self):
        """Verifica que el reporte se guarde en disco con sello SHA-256."""
        obs = OnlineTelemetryObserver()
        report = obs.generate_full_report()
        j_path, m_path = obs.save_reports(report)

        assert j_path.exists()
        assert m_path.exists()
        assert report.sha256_cryptographic_seal.startswith("SEAL-OBS-")

        with open(j_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["report_id"] == report.report_id


if __name__ == "__main__":
    pytest.main(["-v", __file__])
