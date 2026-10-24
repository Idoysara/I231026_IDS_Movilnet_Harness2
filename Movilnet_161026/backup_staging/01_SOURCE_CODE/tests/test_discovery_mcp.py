#!/usr/bin/env python3
"""
test_discovery_mcp.py — Suite de Pruebas, Auditoría y Certificación
======================================================================
Proyecto: AI_Movilnet_300926 / Fase 0 Discovery Suite
Alcance: Valida, prueba y certifica las 5 herramientas MCP de descubrimiento.

Niveles de prueba:
  L1 - Pruebas Unitarias (contrato de cada herramienta MCP)
  L2 - Pruebas de Integración (servidor MCP completo JSON-RPC 2.0)
  L3 - Pruebas de Seguridad SAST (validación de patrones prohibidos)
  L4 - Certificación Final (emite sello de calidad SHA-256)
"""

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Patch sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.discovery_tools import (
    DiscoveryMcpServer,
    audit_perimeter,
    inspect_db_schema,
    parse_api_spec,
    generate_discovery_matrix,
    gatekeeper_validate,
    REPORTS_DIR,
    DOCS_DIR,
)

# ──────────────────────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────────────────────
PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

_results: list[dict] = []


def _record(level: str, test_id: str, name: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    _results.append({
        "level": level, "test_id": test_id, "name": name,
        "status": status, "detail": detail
    })
    tag = f"[{level}][{test_id}]"
    print(f"  {status}  {tag} {name}" + (f"\n        → {detail}" if detail else ""))


# ──────────────────────────────────────────────────────────────
# L1 — Pruebas Unitarias
# ──────────────────────────────────────────────────────────────
def test_l1_generate_matrix():
    print("\n── L1.1: generate_discovery_matrix ─────────────────")
    result = generate_discovery_matrix(client_name="TestCo Telco")
    _record("L1", "U001", "Status GENERATED", result.get("status") == "GENERATED")
    _record("L1", "U002", "Archivo Markdown creado", Path(result.get("output_file", "")).exists())
    _record("L1", "U003", "Dimensiones presentes (>= 5)", len(result.get("dimensions", [])) >= 5)
    _record("L1", "U004", "Cliente correcto en resultado", result.get("client") == "TestCo Telco")


def test_l1_inspect_db():
    print("\n── L1.2: inspect_db_schema ──────────────────────────")
    # Create temporary SQLite with Telco-like schema
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name

    conn = sqlite3.connect(tmp_path)
    conn.execute("""
        CREATE TABLE subscribers (
            id TEXT PRIMARY KEY,
            cedula_rif TEXT NOT NULL,
            full_name TEXT,
            status TEXT DEFAULT 'ACTIVA'
        )
    """)
    conn.execute("""
        CREATE TABLE contracts (
            id TEXT PRIMARY KEY,
            subscriber_id TEXT REFERENCES subscribers(id),
            phone_number TEXT NOT NULL,
            modality TEXT
        )
    """)
    conn.execute("CREATE INDEX idx_phone ON contracts(phone_number)")
    conn.execute("INSERT INTO subscribers VALUES ('S001', 'V-12345678', 'Juan Pérez', 'ACTIVA')")
    conn.execute("INSERT INTO contracts VALUES ('C001', 'S001', '04161234567', 'PREPAGO')")
    conn.commit()
    conn.close()

    result = inspect_db_schema(tmp_path)
    _record("L1", "U005", "Tablas detectadas (>= 2)", len(result.get("tables", {})) >= 2)
    _record("L1", "U006", "Tabla 'subscribers' presente", "subscribers" in result.get("tables", {}))
    _record("L1", "U007", "Tabla 'contracts' presente", "contracts" in result.get("tables", {}))
    _record("L1", "U008", "Índice detectado (idx_phone)", len(result.get("indexes", [])) >= 1)
    _record("L1", "U009", "Conteo de filas correcto", result["tables"].get("subscribers", {}).get("row_count") == 1)
    _record("L1", "U010", "Reporte guardado", Path(result.get("report_saved", "")).exists())
    os.unlink(tmp_path)


def test_l1_parse_api_spec():
    print("\n── L1.3: parse_api_spec ─────────────────────────────")
    # Create temporary OpenAPI spec
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Movilnet Telco API", "version": "1.0.0"},
        "servers": [{"url": "https://api.movilnet.com.ve/v1"}],
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
            },
            "schemas": {"Subscriber": {"type": "object"}, "Balance": {"type": "object"}}
        },
        "paths": {
            "/subscriber/{phone}": {
                "get": {"summary": "Obtener abonado por teléfono", "parameters": [
                    {"name": "phone", "in": "path"}], "responses": {"200": {}}}
            },
            "/subscriber/{phone}/balance": {
                "get": {"summary": "Consultar saldo del abonado", "responses": {"200": {}}}
            },
            "/plans": {
                "get": {"summary": "Catálogo de planes comerciales", "responses": {"200": {}}}
            },
            "/payment/recharge": {
                "post": {"summary": "Procesar recarga/pago", "responses": {"200": {}, "400": {}}}
            }
        }
    }

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as tmp:
        json.dump(spec, tmp, ensure_ascii=False)
        tmp_path = tmp.name

    result = parse_api_spec(tmp_path)
    _record("L1", "U011", "Formato OpenAPI 3.x detectado", result.get("format") == "OpenAPI 3.x")
    _record("L1", "U012", "Título API extraído", result.get("api_title") == "Movilnet Telco API")
    _record("L1", "U013", "Base URL extraída", "movilnet.com.ve" in (result.get("base_url") or ""))
    _record("L1", "U014", "Autenticación detectada (>= 1)", len(result.get("auth_schemes", [])) >= 1)
    _record("L1", "U015", "Endpoints extraídos (>= 4)", result.get("total_endpoints", 0) >= 4)
    _record("L1", "U016", "Cobertura Telco > 60%",
            result.get("telco_coverage", {}).get("coverage_percentage", 0) >= 60)
    _record("L1", "U017", "Schemas contados", result.get("schemas_count", 0) >= 2)
    os.unlink(tmp_path)


def test_l1_gatekeeper_approved():
    print("\n── L1.4: gatekeeper_validate — Escenario APROBADO ──")
    content = """
    Motor de Facturación: Huawei CBS (Billing Engine activo)
    Autenticación: Número telefónico + Cédula de Identidad (V-XXXXXXXX)
    Plan 4GMAX 10GB: 10 Gigabytes, Bs. 180, Inteliplan
    API Gateway: Kong Gateway en https://api.movilnet.com.ve (REST)
    Canales: BDV en línea, Banesco, Pago Móvil
    CONATEL: Providencia administrativa No. 038
    """
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    result = gatekeeper_validate(tmp_path)
    _record("L1", "U018", "Estado APROBADO o PARCIAL",
            result.get("status", "").startswith(("APROBADO", "PARCIAL")))
    _record("L1", "U019", "Autorizado=True", result.get("authorized") is True)
    _record("L1", "U020", "Reporte guardado", Path(result.get("report_saved", "")).exists())
    os.unlink(tmp_path)


def test_l1_gatekeeper_blocked():
    print("\n── L1.5: gatekeeper_validate — Escenario BLOQUEADO ─")
    content = "Solo información de contacto del cliente. Nada técnico."
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    result = gatekeeper_validate(tmp_path)
    _record("L1", "U021", "Estado BLOQUEADO", "BLOQUEADO" in result.get("status", ""))
    _record("L1", "U022", "Autorizado=False", result.get("authorized") is False)
    os.unlink(tmp_path)


def test_l1_perimeter_invalid_host():
    print("\n── L1.6: audit_perimeter — Host inaccesible ────────")
    result = audit_perimeter("http://host.invalido.telco.test", port=443)
    _record("L1", "U023", "Conectividad no es REACHABLE",
            result.get("connectivity") != "REACHABLE")
    _record("L1", "U024", "Recomendaciones generadas", len(result.get("recommendations", [])) >= 1)


# ──────────────────────────────────────────────────────────────
# L2 — Pruebas de Integración (servidor MCP JSON-RPC 2.0)
# ──────────────────────────────────────────────────────────────
def test_l2_mcp_server():
    print("\n── L2: Integración MCP Server ───────────────────────")
    server = DiscoveryMcpServer()

    # Initialize
    r = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    _record("L2", "I001", "initialize → serverInfo presente",
            "serverInfo" in r.get("result", {}))
    _record("L2", "I002", "server name correcto",
            r["result"]["serverInfo"]["name"] == "telco-discovery-mcp")

    # tools/list
    r = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = r.get("result", {}).get("tools", [])
    _record("L2", "I003", "tools/list retorna 5 herramientas", len(tools) == 5)
    tool_names = {t["name"] for t in tools}
    expected_tools = {
        "mcp_discovery_audit_perimeter",
        "mcp_discovery_inspect_db_schema",
        "mcp_discovery_parse_api_spec",
        "mcp_discovery_generate_matrix",
        "mcp_discovery_gatekeeper"
    }
    _record("L2", "I004", "Nombres de herramientas correctos", tool_names == expected_tools)

    # tools/call: generate_matrix via MCP
    r = server.handle_request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "mcp_discovery_generate_matrix",
                   "arguments": {"client_name": "IntegrationTest Telco"}}
    })
    content_str = r.get("result", {}).get("content", [{}])[0].get("text", "{}")
    content = json.loads(content_str)
    _record("L2", "I005", "MCP generate_matrix → GENERATED", content.get("status") == "GENERATED")

    # tools/call: unknown tool
    r = server.handle_request({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "mcp_NONEXISTENT", "arguments": {}}
    })
    _record("L2", "I006", "Tool inexistente → error JSON-RPC", "error" in r)

    # Unsupported method
    r = server.handle_request({"jsonrpc": "2.0", "id": 5, "method": "unsupported/method"})
    _record("L2", "I007", "Método no soportado → error JSON-RPC", "error" in r)


# ──────────────────────────────────────────────────────────────
# L3 — Pruebas de Seguridad SAST
# ──────────────────────────────────────────────────────────────
def test_l3_sast():
    print("\n── L3: Seguridad SAST ───────────────────────────────")
    source = Path(__file__).parent.parent / "mcp" / "discovery_tools.py"
    content = source.read_text(encoding="utf-8")

    # (pattern, description, is_regex)
    prohibited = [
        ("DROP TABLE", "Instrucción SQL destructiva", False),
        ("DELETE FROM", "Eliminación masiva sin WHERE", False),
        ("rm -rf", "Eliminación recursiva de archivos", False),
        ("os.system(", "Ejecución de shell sin sanitizar", False),
        ("exec(request", "Ejecución dinámica de input externo", False),
        ("eval(request", "Evaluación dinámica de input externo", False),
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key hardcodeada", True),
        (r"password\s*=\s*['\"][^'\"]{4,}", "Credencial hardcodeada", True),
    ]

    import re
    for pattern, description, is_regex in prohibited:
        if is_regex:
            found = bool(re.search(pattern, content, re.IGNORECASE))
        else:
            found = pattern.lower() in content.lower()
        _record("L3", f"S-{pattern[:8].replace(' ', '_')}", f"Patrón prohibido: {description}", not found,
                detail="" if not found else f"⚠️ Patrón encontrado en el código fuente: '{pattern}'")

    # Verify all DB access is READ-ONLY
    has_write_ops = any(op in content for op in ["conn.execute(\"INSERT", "conn.execute(\"UPDATE",
                                                  "conn.execute(\"DELETE"])
    _record("L3", "S009", "MCP no tiene operaciones de escritura en BD reales",
            not has_write_ops, detail="Toda escritura es solo en archivos de reporte del proyecto.")

    # Verify SSL context is used, not bypassed completely in production paths
    _record("L3", "S010", "SSL context definido en audit_perimeter",
            "ssl.create_default_context()" in content)


# ──────────────────────────────────────────────────────────────
# L4 — Certificación Final SHA-256
# ──────────────────────────────────────────────────────────────
def generate_certification(all_passed: bool) -> dict:
    print("\n── L4: Certificación SHA-256 ────────────────────────")

    files_to_certify = [
        PROJECT_ROOT / "mcp" / "discovery_tools.py",
        PROJECT_ROOT / "tests" / "test_discovery_mcp.py",
        PROJECT_ROOT.parent.parent / "skills" / "telco-discovery-inception" / "SKILL.md",
    ]

    hasher = hashlib.sha256()
    certified_files = []
    for f in files_to_certify:
        if f.exists():
            content = f.read_bytes()
            hasher.update(content)
            certified_files.append({
                "file": str(f.relative_to(PROJECT_ROOT.parent.parent) if PROJECT_ROOT.parent.parent in f.parents else f.name),
                "sha256": hashlib.sha256(content).hexdigest()[:16],
                "size_bytes": len(content)
            })

    suite_hash = hasher.hexdigest()

    total = len(_results)
    passed = sum(1 for r in _results if r["status"] == PASS)
    failed = total - passed

    certification = {
        "certification_id": f"FASE0-CERT-{suite_hash[:12].upper()}",
        "project": "AI_Movilnet_300926",
        "suite": "Telco Discovery Inception Suite v1.0.0",
        "timestamp": datetime.now().isoformat(),
        "overall_status": "CERTIFICADO ✅" if all_passed else "REQUIERE CORRECCIONES ⚠️",
        "authorized_for_phase1": all_passed,
        "test_summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{round(passed / total * 100, 1)}%" if total > 0 else "N/A"
        },
        "scope": {
            "global_components": [
                "skills/telco-discovery-inception/SKILL.md (reutilizable en cualquier proyecto Telco)"
            ],
            "project_components": [
                "mcp/discovery_tools.py (AI_Movilnet_300926 - Movilnet Venezuela)",
                "tests/test_discovery_mcp.py",
                "scripts/audit_perimeter_waf.py",
                "scripts/generate_discovery_matrix.py",
                "docs/FASE_0_LEVANTAMIENTO_INFORMACION.md"
            ]
        },
        "certified_files": certified_files,
        "suite_sha256": suite_hash[:24],
        "github_references": [
            "https://github.com/tmforum-rand/Open_API_And_Data_Model (TMF620/678/632/676)",
            "https://github.com/schemacrawler/SchemaCrawler",
            "https://github.com/stoplightio/prism",
        ]
    }

    cert_path = REPORTS_DIR / f"CERTIFICATION_FASE0_{suite_hash[:12].upper()}.json"
    cert_path.write_text(json.dumps(certification, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  🏅 Certificado: {certification['certification_id']}")
    print(f"  📊 Tasa de éxito: {certification['test_summary']['pass_rate']}")
    print(f"  📁 Reporte: {cert_path}")

    return certification


# ──────────────────────────────────────────────────────────────
# Runner Principal
# ──────────────────────────────────────────────────────────────
def run_self_test() -> bool:
    print("=" * 60)
    print("🔬 SUITE DE PRUEBAS: Telco Discovery Inception - Fase 0")
    print(f"   Proyecto: AI_Movilnet_300926 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    test_l1_generate_matrix()
    test_l1_inspect_db()
    test_l1_parse_api_spec()
    test_l1_gatekeeper_approved()
    test_l1_gatekeeper_blocked()
    test_l1_perimeter_invalid_host()
    test_l2_mcp_server()
    test_l3_sast()

    total = len(_results)
    passed = sum(1 for r in _results if r["status"] == PASS)
    failed = total - passed
    all_passed = failed == 0

    print("\n" + "=" * 60)
    print(f"📊 RESUMEN FINAL: {passed}/{total} pruebas pasaron | {failed} fallidas")
    print("=" * 60)

    cert = generate_certification(all_passed)

    if all_passed:
        print("\n  ✅ SUITE CERTIFICADA — Autorizado para Fase 1 de Desarrollo")
    else:
        print("\n  ⚠️  SUITE CON FALLAS — Revisar los test FAIL antes de continuar")

    return all_passed


if __name__ == "__main__":
    success = run_self_test()
    sys.exit(0 if success else 1)
