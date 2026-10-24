#!/usr/bin/env python3
"""
test_cloud_deployment_readiness.py — Suite de Pruebas Unitarias para Despliegue en la Nube (Modo A)
===================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: Regla del 100% Pass)
"""

try:
    import pytest
except ImportError:
    pytest = None
from pathlib import Path
from scripts.validate_cloud_deployment_readiness import CloudDeploymentValidator


def test_dockerfile_multi_stage_and_hardening():
    """Valida que Dockerfile sea multi-stage, use non-root y copie core/."""
    validator = CloudDeploymentValidator()
    check = validator.check_dockerfile()
    assert check.status == "PASS"
    assert "core/ presente" in check.details


def test_render_iac_configuration():
    """Valida que render.yaml cumpla con la especificación de servicio web gratuito."""
    validator = CloudDeploymentValidator()
    check = validator.check_render_iac()
    assert check.status == "PASS"
    assert "Free Tier" in check.details


def test_railway_iac_configuration():
    """Valida que railway.json esté configurado con Dockerfile y healthcheck."""
    validator = CloudDeploymentValidator()
    check = validator.check_railway_iac()
    assert check.status == "PASS"


def test_pwa_static_assets_and_phone_params():
    """Valida que la PWA soporte parámetros URL ?phone= y persistencia local."""
    validator = CloudDeploymentValidator()
    check = validator.check_pwa_static_assets()
    assert check.status == "PASS"


def test_dynamic_port_injection():
    """Valida que service.py lea dinámicamente el puerto HOST y PORT inyectado por la nube."""
    validator = CloudDeploymentValidator()
    check = validator.check_dynamic_port_support()
    assert check.status == "PASS"


def test_magic_link_generation_for_whatsapp():
    """Valida la generación de enlaces mágicos hacia el dominio de la nube."""
    validator = CloudDeploymentValidator()
    render_link = validator.generate_magic_link_sample("04142554590", "https://movilnet-core.onrender.com")
    assert render_link == "https://movilnet-core.onrender.com/ui/pwa_stitch/index.html?phone=04142554590"

    custom_link = validator.generate_magic_link_sample("584160000001", "https://autogestion.movilnet.com.ve")
    assert custom_link == "https://autogestion.movilnet.com.ve/ui/pwa_stitch/index.html?phone=04160000001"


def test_full_cloud_deployment_audit_pass():
    """Valida que la auditoría completa de nube arroje estatus READY y 100% PASS."""
    validator = CloudDeploymentValidator()
    report = validator.run_full_audit()
    assert report.all_passed is True
    assert report.summary["readiness_status"] == "READY_FOR_24_7_CLOUD_DEPLOYMENT"
    assert report.summary["passed_checks"] == report.summary["total_checks"]
    assert report.sha256_seal.startswith("SHA256:")


def test_render_deploy_endpoint_and_ops_routing():
    """Valida el endpoint de operaciones /api/v1/ops/render-deploy (GET y POST)."""
    import json
    from api.service import MovilnetAPIService
    service = MovilnetAPIService()

    # 1. Probar GET de estado de Render Deploy
    status, headers, body = service.dispatch("GET", "/api/v1/ops/render-deploy", {}, b"")
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert "configured" in data
    assert "render_url" in data
    assert data["render_url"] == "https://movilnet-core.onrender.com"

    # 2. Probar POST con despacho estructurado
    status_post, _, body_post = service.dispatch("POST", "/api/v1/ops/render-deploy", {}, json.dumps({}).encode("utf-8"))
    data_post = json.loads(body_post.decode("utf-8"))
    assert "success" in data_post
