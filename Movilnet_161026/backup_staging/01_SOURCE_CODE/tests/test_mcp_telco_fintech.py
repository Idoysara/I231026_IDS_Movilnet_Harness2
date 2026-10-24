#!/usr/bin/env python3
"""
test_mcp_telco_fintech.py — Redirección oficial a test_all_mcp_suites.py
Suite de Pruebas y Certificación de las 5 Suites MCP de Movilnet.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.test_all_mcp_suites import (
    TestSuite1CoreTelecom,
    TestSuite2FintechC2P,
    TestSuite3CrmRetention,
    TestSuite4PrivacyGuard,
    TestSuite5OmnichannelWhatsApp,
    TestMasterGatewayAndMcpProtocol,
    run_master_certification
)

if __name__ == "__main__":
    sys.exit(run_master_certification())
