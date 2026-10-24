#!/usr/bin/env python3
"""
tests/test_ejecutar_prueba_real.py — Pruebas Automatizadas del Comando Maestro de Prueba Real
=============================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: 100% Pass)
"""

try:
    import pytest
except ImportError:
    pytest = None
from scripts.ejecutar_prueba_real import RealTestRunner


class TestRealTestRunner:
    """Suite de validación formal del orquestador de prueba real."""

    def test_runner_initialization(self):
        runner = RealTestRunner(port=8010)
        assert runner.port == 8010
        assert runner.config.bot_name == "MOVI"
        assert runner.bot_phone_digits == "584241533712"

    def test_build_whatsapp_test_url(self):
        runner = RealTestRunner(port=8010)
        url = runner.build_whatsapp_test_url("Saldo")
        assert "wa.me/584241533712" in url
        assert "text=Saldo" in url

    def test_build_monitor_url(self):
        runner = RealTestRunner(port=8010)
        url = runner.build_monitor_url()
        assert "localhost:8010" in url
        assert "conversatorio.html" in url

    def test_open_interfaces_dictionary(self):
        runner = RealTestRunner(port=8010)
        urls = runner.open_interfaces(test_msg="Planes", open_browser=False)
        assert "whatsapp_direct_url" in urls
        assert "monitor_conversatorio_url" in urls
        assert "pwa_simulator_url" in urls
        assert "text=Planes" in urls["whatsapp_direct_url"]
