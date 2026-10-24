#!/usr/bin/env python3
"""
tests/test_n8n_database_schema.py — Suite de Pruebas Unitarias para el Modelo de Datos de n8n
=============================================================================================
Valida la integridad de la base de datos relacional asociada al flujo sNMbtiEiTkuQ9OCY:
- 11 Tablas requeridas creadas.
- Tipos de datos, claves primarias y claves foráneas.
- Ciclo de vida completo simulación E2E sin violaciones de integridad referencial.
"""

try:
    import pytest
except ImportError:
    pytest = None
from scripts.verify_n8n_db_schema import verify_schema_integrity, simulate_full_workflow_data_lifecycle


def test_schema_structural_integrity():
    """Valida que todas las 11 tablas y sus campos existan correctamente."""
    result = verify_schema_integrity()
    assert result["status"] == "success"
    assert result["total_tables"] >= 11
    assert "evolution_instances" in result["tables"]
    assert "whatsapp_contacts" in result["tables"]
    assert "inbound_webhook_events" in result["tables"]
    assert "media_assets" in result["tables"]
    assert "chat_histories" in result["tables"]
    assert "exchange_rates_cache" in result["tables"]
    assert "exchange_calculations_log" in result["tables"]
    assert "catalog_price_list" in result["tables"]
    assert "subworkflow_executions" in result["tables"]
    assert "outbound_messages" in result["tables"]
    assert "movilnet_n8n_bridge_logs" in result["tables"]


def test_schema_e2e_data_lifecycle_and_foreign_keys():
    """Valida la inserción relacional cruzada y cero violaciones de claves foráneas."""
    result = simulate_full_workflow_data_lifecycle()
    assert result["status"] == "success"
    assert result["lifecycle_verified"] is True
    assert result["fk_violations"] == 0
    assert result["records_inserted"] == 8
    assert "04160000001" in result["subscriber"]
