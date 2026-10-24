#!/usr/bin/env python3
"""
MCP Discovery Tools Server - Fase 0 Telco Discovery Suite
==========================================================
Proyecto: AI_Movilnet_300926
Alcance: GLOBAL (reutilizable en cualquier proyecto Telco)
Scope: Herramientas MCP de auditoría perimetral, introspección de esquemas
       y análisis de contratos de integración para la Fase 0 de Discovery.

Herramientas expuestas:
  - mcp_discovery_audit_perimeter   : Diagnóstico WAF/firewall/SSL del cliente
  - mcp_discovery_inspect_db_schema : Introspección de BD SQLite/PostgreSQL
  - mcp_discovery_parse_api_spec    : Parseo de OpenAPI/WSDL/Postman
  - mcp_discovery_generate_matrix   : Genera cuestionario de levantamiento
  - mcp_discovery_gatekeeper        : Valida si Fase 0 está completa
"""

import json
import re
import socket
import ssl
import sqlite3
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# HERRAMIENTA 1: Diagnóstico Perimetral WAF/SSL
# ─────────────────────────────────────────────
def audit_perimeter(target_url: str, port: int = 443) -> Dict[str, Any]:
    """
    Evalúa conectividad, certificado SSL, política WAF y latencia del endpoint
    del cliente. Detecta bloqueos, redirecciones y políticas restrictivas.
    """
    result = {
        "target": target_url,
        "timestamp": datetime.now().isoformat(),
        "connectivity": "UNKNOWN",
        "ssl_valid": False,
        "ssl_expiry": None,
        "waf_detected": False,
        "waf_vendor": None,
        "http_status": None,
        "latency_ms": None,
        "redirect_chain": [],
        "block_reason": None,
        "recommendations": []
    }

    parsed = urlparse(target_url if "://" in target_url else f"https://{target_url}")
    host = parsed.hostname
    scheme = parsed.scheme or "https"
    path = parsed.path or "/"

    # 1. TCP Connectivity
    try:
        start = datetime.now()
        sock = socket.create_connection((host, port), timeout=8)
        latency = (datetime.now() - start).total_seconds() * 1000
        result["latency_ms"] = round(latency, 2)
        result["connectivity"] = "REACHABLE"
        sock.close()
    except socket.timeout:
        result["connectivity"] = "TIMEOUT"
        result["recommendations"].append(
            "El host no responde en 8s. Verificar VPN, whitelist de IP o firewall corporativo.")
        return result
    except Exception as e:
        result["connectivity"] = f"UNREACHABLE: {e}"
        result["recommendations"].append("Confirmar con el equipo de red del cliente si requiere VPN o IP estática.")
        return result

    # 2. SSL Certificate inspection
    if scheme == "https":
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=host) as ssock:
                ssock.connect((host, port))
                cert = ssock.getpeercert()
                expiry_str = cert.get("notAfter", "")
                result["ssl_valid"] = True
                result["ssl_expiry"] = expiry_str
                result["ssl_subject"] = dict(x[0] for x in cert.get("subject", []))
                result["ssl_issuer"] = dict(x[0] for x in cert.get("issuer", []))
        except ssl.SSLCertVerificationError as e:
            result["ssl_valid"] = False
            result["recommendations"].append(f"Certificado SSL inválido o autofirmado: {e}. "
                                             "Confirmar con el cliente si usa CA privada.")
        except Exception as e:
            result["ssl_valid"] = False
            result["recommendations"].append(f"Error SSL: {e}")

    # 3. HTTP Request + WAF Detection
    waf_signatures = {
        "Cloudflare": ["cf-ray", "cf-cache-status", "__cfduid"],
        "AWS WAF / CloudFront": ["x-amz-cf-id", "x-amzn-requestid"],
        "Akamai": ["akamai-origin-hop", "x-check-cacheable"],
        "Imperva / Incapsula": ["x-iinfo", "incap_ses"],
        "F5 BIG-IP": ["bigipserver", "f5-trafficshield"],
        "Fortinet": ["fortiwafsid"],
    }

    try:
        req = urllib.request.Request(
            target_url,
            headers={
                "User-Agent": "TelcoDiscoveryBot/1.0 (AI_Movilnet_300926 Phase0 Audit)",
                "Accept": "text/html,application/json"
            }
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            result["http_status"] = resp.status
            headers = dict(resp.headers)
            # WAF Detection
            headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
            for vendor, signatures in waf_signatures.items():
                if any(sig in headers_lower for sig in signatures):
                    result["waf_detected"] = True
                    result["waf_vendor"] = vendor
                    result["recommendations"].append(
                        f"WAF detectado: {vendor}. Solicitar whitelist de IP del servidor Movilnet AI.")
                    break
            # Server header
            result["server_header"] = headers.get("server") or headers.get("Server") or "No expuesto"

    except urllib.error.HTTPError as e:
        result["http_status"] = e.code
        # Read WAF block body
        try:
            body = e.read().decode("utf-8", errors="ignore")[:500]
            result["block_reason"] = body
        except Exception:
            pass
        if e.code in [403, 406, 429]:
            result["waf_detected"] = True
            result["recommendations"].append(
                f"HTTP {e.code} – El WAF del cliente está bloqueando peticiones de origen externo. "
                "Solicitar: (1) IP Whitelist, (2) API Key de acceso controlado, o (3) VPN Site-to-Site.")
        elif e.code == 401:
            result["recommendations"].append(
                "HTTP 401 – El endpoint requiere autenticación. Solicitar credenciales de acceso al equipo Telco.")
    except Exception as e:
        result["connectivity"] = f"HTTP_ERROR: {e}"
        result["recommendations"].append(f"Error en la petición HTTP: {e}")

    # 4. Final recommendations
    if result["http_status"] in [200, 301, 302]:
        result["recommendations"].append(
            "✅ Endpoint accesible. Proceder con exploración de APIs expuestas y documentación de contratos.")
    if not result["ssl_valid"] and scheme == "https":
        result["recommendations"].append(
            "⚠️ SSL no verificado. Solicitar cadena de certificados CA privada del cliente.")

    # 5. Save report
    report_path = REPORTS_DIR / f"perimeter_audit_{host}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    result["report_saved"] = str(report_path)

    return result


# ──────────────────────────────────────────────────────────
# HERRAMIENTA 2: Introspección de Esquema de Base de Datos
# ──────────────────────────────────────────────────────────
def inspect_db_schema(db_path: str) -> Dict[str, Any]:
    """
    Inspecciona la estructura real de un archivo SQLite entregado por el cliente:
    tablas, columnas, tipos de datos, llaves primarias, índices y relaciones.
    Genera un reporte de esquema para alimentar el Mapping Manifesto.
    """
    path = Path(db_path)
    if not path.exists():
        return {"error": f"Archivo de base de datos no encontrado: {db_path}"}

    result = {
        "db_path": str(path),
        "timestamp": datetime.now().isoformat(),
        "tables": {},
        "foreign_keys": [],
        "indexes": [],
        "total_rows_estimate": {},
        "recommendations": []
    }

    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cur.fetchall()]

        for table in tables:
            clean_table = "".join(c for c in table if c.isalnum() or c == "_")
            # Columns
            cur.execute("PRAGMA table_info(" + clean_table + ")")
            columns = []
            for col in cur.fetchall():
                columns.append({
                    "name": col["name"],
                    "type": col["type"],
                    "not_null": bool(col["notnull"]),
                    "primary_key": bool(col["pk"]),
                    "default": col["dflt_value"]
                })
            # Row count estimate
            try:
                cur.execute("SELECT COUNT(*) FROM [" + clean_table + "]")
                row_count = cur.fetchone()[0]
            except Exception:
                row_count = -1

            result["tables"][table] = {
                "columns": columns,
                "column_count": len(columns),
                "row_count": row_count
            }
            result["total_rows_estimate"][table] = row_count

            # Foreign keys
            cur.execute("PRAGMA foreign_key_list(" + clean_table + ")")
            for fk in cur.fetchall():
                result["foreign_keys"].append({
                    "from_table": table,
                    "from_col": fk["from"],
                    "to_table": fk["table"],
                    "to_col": fk["to"],
                    "on_delete": fk["on_delete"]
                })

        # Indexes
        cur.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name")
        for idx in cur.fetchall():
            if idx["sql"]:
                result["indexes"].append({
                    "name": idx["name"],
                    "table": idx["tbl_name"],
                    "definition": idx["sql"]
                })

        conn.close()

        # Analysis recommendations
        total_rows = sum(v for v in result["total_rows_estimate"].values() if v > 0)
        if total_rows > 1_000_000:
            result["recommendations"].append(
                f"⚠️ Base de datos grande ({total_rows:,} filas). Evaluar particionado y réplicas de solo lectura.")
        if not result["foreign_keys"]:
            result["recommendations"].append(
                "⚠️ No se detectaron claves foráneas explícitas. Verificar integridad referencial en capa de aplicación.")
        if not result["indexes"]:
            result["recommendations"].append(
                "⚠️ No se detectaron índices. Riesgo de Full Table Scan en consultas de saldo con 4M de abonados.")
        else:
            result["recommendations"].append(
                f"✅ {len(result['indexes'])} índices detectados. Validar cobertura en campos phone_number y cedula_rif.")

        result["recommendations"].append("✅ Esquema inspeccionado. Alimentar MAPPING_MANIFESTO.md con estos metadatos reales.")

        # Save report
        report_path = REPORTS_DIR / f"schema_inspection_{path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        result["report_saved"] = str(report_path)

    except Exception as e:
        result["error"] = str(e)

    return result


# ──────────────────────────────────────────────────────────
# HERRAMIENTA 3: Parseo y Análisis de Contratos de API
# ──────────────────────────────────────────────────────────
def parse_api_spec(spec_path: str) -> Dict[str, Any]:
    """
    Parsea un contrato de API en formato OpenAPI 3.x / Swagger 2.0 / Postman Collection.
    Extrae endpoints, métodos, esquemas de request/response y autenticación.
    """
    path = Path(spec_path)
    if not path.exists():
        return {"error": f"Archivo de especificación no encontrado: {spec_path}"}

    result = {
        "spec_path": str(path),
        "format": "UNKNOWN",
        "timestamp": datetime.now().isoformat(),
        "api_title": None,
        "api_version": None,
        "base_url": None,
        "auth_schemes": [],
        "endpoints": [],
        "schemas_count": 0,
        "telco_coverage": {},
        "recommendations": []
    }

    try:
        raw = path.read_text(encoding="utf-8")
        # Detect format
        if path.suffix in [".yaml", ".yml"]:
            try:
                import yaml
                spec = yaml.safe_load(raw)
            except ImportError:
                # Fallback: basic YAML-as-text parsing
                spec = {}
                result["recommendations"].append(
                    "⚠️ PyYAML no instalado. Instalar con: pip install pyyaml. Análisis limitado.")
        elif path.suffix in [".json"]:
            spec = json.loads(raw)
        else:
            spec = {}

        # Detect format type
        if spec.get("openapi", "").startswith("3"):
            result["format"] = "OpenAPI 3.x"
        elif spec.get("swagger") == "2.0":
            result["format"] = "Swagger 2.0"
        elif "info" in spec and "collection" in str(spec.get("info", {}).get("schema", "")):
            result["format"] = "Postman Collection"

        # Extract metadata
        info = spec.get("info", {})
        result["api_title"] = info.get("title", "Sin título")
        result["api_version"] = info.get("version", "Sin versión")

        # Base URL
        if result["format"] == "OpenAPI 3.x":
            servers = spec.get("servers", [])
            result["base_url"] = servers[0].get("url") if servers else "No especificado"
        elif result["format"] == "Swagger 2.0":
            host = spec.get("host", "")
            base = spec.get("basePath", "/")
            schemes = spec.get("schemes", ["https"])
            result["base_url"] = f"{schemes[0]}://{host}{base}" if host else "No especificado"

        # Authentication
        security_schemes = spec.get("components", {}).get("securitySchemes", {}) or \
                           spec.get("securityDefinitions", {})
        for name, scheme in security_schemes.items():
            result["auth_schemes"].append({
                "name": name,
                "type": scheme.get("type"),
                "flow": scheme.get("flows", scheme.get("flow")),
                "description": scheme.get("description")
            })
        if not result["auth_schemes"]:
            result["recommendations"].append(
                "⚠️ No se detectaron esquemas de autenticación. Confirmar si la API es pública o requiere token.")

        # Endpoints
        paths = spec.get("paths", {})
        telco_patterns = {
            "subscriber": ["suscriptor", "subscriber", "abonado", "customer", "client"],
            "balance": ["balance", "saldo", "account", "statement", "billing", "factura"],
            "plan": ["plan", "product", "offer", "service", "tariff", "tarifa"],
            "payment": ["payment", "pago", "recharge", "recarga", "transaction"],
            "auth": ["auth", "login", "validate", "token", "identity"]
        }
        telco_hits: Dict[str, int] = {k: 0 for k in telco_patterns}

        for path_str, methods in paths.items():
            for method, details in methods.items():
                if method.lower() in ["get", "post", "put", "patch", "delete"]:
                    endpoint = {
                        "method": method.upper(),
                        "path": path_str,
                        "summary": details.get("summary") or details.get("description", ""),
                        "tags": details.get("tags", []),
                        "parameters": len(details.get("parameters", [])),
                        "responses": list(details.get("responses", {}).keys())
                    }
                    result["endpoints"].append(endpoint)

                    # Telco coverage check
                    searchable = f"{path_str} {endpoint['summary']}".lower()
                    for category, keywords in telco_patterns.items():
                        if any(kw in searchable for kw in keywords):
                            telco_hits[category] += 1

        result["telco_coverage"] = {
            "subscriber_endpoints": telco_hits["subscriber"],
            "balance_endpoints": telco_hits["balance"],
            "plan_endpoints": telco_hits["plan"],
            "payment_endpoints": telco_hits["payment"],
            "auth_endpoints": telco_hits["auth"],
            "coverage_percentage": round(
                (sum(1 for v in telco_hits.values() if v > 0) / len(telco_hits)) * 100, 1)
        }

        # Schemas count
        result["schemas_count"] = len(spec.get("components", {}).get("schemas", {}))

        # Coverage recommendations
        missing = [cat for cat, cnt in telco_hits.items() if cnt == 0]
        if missing:
            result["recommendations"].append(
                f"⚠️ Endpoints Telco faltantes en la especificación: {', '.join(missing)}. "
                "Verificar si existen como servicios internos no documentados.")
        if result["telco_coverage"]["coverage_percentage"] >= 80:
            result["recommendations"].append(
                f"✅ Cobertura Telco del {result['telco_coverage']['coverage_percentage']}%. "
                "Buena base para integración. Revisar esquemas de respuesta en detalle.")
        else:
            result["recommendations"].append(
                f"⚠️ Cobertura Telco del {result['telco_coverage']['coverage_percentage']}%. "
                "Se requerirá desarrollo de endpoints adicionales o acceso directo al BSS.")

        # Save report
        report_path = REPORTS_DIR / f"api_spec_{path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        result["report_saved"] = str(report_path)
        result["total_endpoints"] = len(result["endpoints"])

    except Exception as e:
        result["error"] = str(e)

    return result


# ──────────────────────────────────────────────────────────
# HERRAMIENTA 4: Generador de Cuestionario de Levantamiento
# ──────────────────────────────────────────────────────────
def generate_discovery_matrix(
    client_name: str = "Movilnet Venezuela",
    output_format: str = "markdown"
) -> Dict[str, Any]:
    """
    Genera el cuestionario completo de levantamiento de información para el
    equipo técnico del cliente (formato Markdown o JSON estructurado).
    """
    questions = {
        "DIMENSIÓN A - Sistemas BSS/OSS": [
            "¿Cuál es el motor de facturación activo? (Ericsson BSCS / Huawei CBS / Oracle BRM / otro)",
            "¿Los saldos prepago son en tiempo real (OCS) o por lotes?",
            "¿Cómo se exponen los datos de abonados? (réplica BD / API Gateway / Data Warehouse)",
            "¿Qué CRM gestiona la base de clientes? (Salesforce / SAP / propio)",
        ],
        "DIMENSIÓN B - APIs e Integración": [
            "¿Existe un API Gateway corporativo activo? ¿Cuál y en qué URL?",
            "¿Qué protocolos de integración están publicados? (REST / SOAP / gRPC / Kafka)",
            "¿Cuáles endpoints de consulta están disponibles? (getSubscriberBalance, etc.)",
            "¿Existe un ambiente sandbox/desarrollo para pruebas?",
        ],
        "DIMENSIÓN C - Autenticación KYC": [
            "¿Qué datos validan la identidad del abonado? (Teléfono + Cédula / OTP SMS / PIN)",
            "¿Existe un servicio centralizado de identidad? (LDAP / SSO / validación interna)",
            "¿Cuántos intentos fallidos disparan bloqueo y por cuánto tiempo?",
        ],
        "DIMENSIÓN D - Catálogo Comercial": [
            "¿Cuáles son los planes de datos vigentes con sus cuotas exactas en GB, Bs., minutos y SMS?",
            "¿Cuáles son los canales de pago y recarga actualmente habilitados?",
            "¿Cuál es el ciclo de facturación pospago y política de suspensión por mora?",
        ],
        "DIMENSIÓN E - Seguridad y Regulatorio": [
            "¿Qué providencias de CONATEL aplican al asistente virtual?",
            "¿Cuánto tiempo deben retenerse los registros de consultas del asistente?",
            "¿Los datos deben residir en Venezuela o pueden estar en cloud internacional?",
            "¿Qué datos NUNCA puede exponer el asistente? (saldo de terceros, CDR, ubicación)",
        ]
    }

    timestamp = datetime.now().strftime("%Y-%m-%d")

    if output_format == "markdown":
        md_lines = [
            f"# 📋 Cuestionario de Levantamiento de Información",
            f"## Cliente: {client_name}",
            f"**Fecha:** {timestamp}",
            f"**Responsable TI del Cliente:** _________________",
            f"**Responsable del Proyecto:** _________________",
            "",
            "---",
            ""
        ]
        question_num = 1
        for dimension, qs in questions.items():
            md_lines.append(f"## {dimension}")
            md_lines.append("")
            for q in qs:
                md_lines.append(f"**Pregunta {question_num}:** {q}")
                md_lines.append("```")
                md_lines.append("Respuesta: ")
                md_lines.append("```")
                md_lines.append("")
                question_num += 1
            md_lines.append("---")
            md_lines.append("")

        md_lines += [
            "## ✅ Firma y Certificación de Fase 0",
            "",
            "| Rol | Nombre | Firma | Fecha |",
            "|:---|:---|:---|:---|",
            "| Responsable TI Movilnet | | | |",
            "| Arquitecto de Integración | | | |",
            "| Gerente del Proyecto | | | |",
            "",
            "> Este cuestionario diligenciado y firmado autoriza el inicio de la Fase 1 de diseño y desarrollo.",
            ""
        ]

        content = "\n".join(md_lines)
        output_path = DOCS_DIR / f"CUESTIONARIO_LEVANTAMIENTO_{client_name.replace(' ', '_').upper()}_{timestamp}.md"
        output_path.write_text(content, encoding="utf-8")

        return {
            "status": "GENERATED",
            "format": "markdown",
            "client": client_name,
            "total_questions": sum(len(v) for v in questions.items() if isinstance(v, list)),
            "output_file": str(output_path),
            "dimensions": list(questions.keys()),
            "recommendation": "Enviar este cuestionario al responsable de TI del cliente para ser diligenciado antes de la reunión de kick-off técnico."
        }

    return {"error": f"Formato no soportado: {output_format}. Usar 'markdown'."}


# ──────────────────────────────────────────────────────────
# HERRAMIENTA 5: Gatekeeper - Certificación de Fase 0
# ──────────────────────────────────────────────────────────
def gatekeeper_validate(discovery_doc_path: str) -> Dict[str, Any]:
    """
    Valida si el documento de levantamiento de información está suficientemente
    completo para autorizar el paso a la Fase 1 de diseño y desarrollo.
    """
    path = Path(discovery_doc_path)
    if not path.exists():
        return {
            "status": "BLOQUEADO",
            "reason": f"No se encontró el documento de levantamiento: {discovery_doc_path}",
            "authorized": False
        }

    content = path.read_text(encoding="utf-8").lower()

    mandatory_checks = {
        "Billing Engine identificado": any(kw in content for kw in
            ["ericsson", "huawei", "oracle brm", "amdocs", "motor de facturación", "billing", "desarrollo propio"]),
        "Mecanismo de autenticación KYC definido": any(kw in content for kw in
            ["cedula", "cédula", "otp", "autenticación", "validación", "kyc", "número + cédula"]),
        "Catálogo de planes documentado": any(kw in content for kw in
            ["plan", "gb", "megabyte", "inteliplan", "4gmax", "cuota"]),
        "Modelo de exposición de datos clarificado": any(kw in content for kw in
            ["api gateway", "réplica", "replica", "data warehouse", "rest", "soap"]),
    }

    optional_checks = {
        "Canales de pago identificados": any(kw in content for kw in
            ["bdv", "banesco", "pago móvil", "patria", "mercantil", "canal"]),
        "Marco regulatorio CONATEL mapeado": any(kw in content for kw in
            ["conatel", "regulatorio", "providencia", "normativa"]),
        "Entorno sandbox disponible": any(kw in content for kw in
            ["sandbox", "desarrollo", "prueba", "test", "staging"]),
    }

    mandatory_passed = sum(mandatory_checks.values())
    optional_passed = sum(optional_checks.values())
    total_mandatory = len(mandatory_checks)

    if mandatory_passed == total_mandatory:
        status = "APROBADO ✅"
        authorized = True
        verdict = "Todas las verificaciones críticas pasaron. AUTORIZADO para iniciar Fase 1."
    elif mandatory_passed >= 3:
        status = "PARCIAL ⚠️"
        authorized = True
        verdict = "La mayoría de verificaciones críticas pasaron. Proceder con supuestos documentados."
    else:
        status = "BLOQUEADO 🚫"
        authorized = False
        verdict = "Verificaciones críticas insuficientes. NO proceder a Fase 1 hasta completar el levantamiento."

    missing_mandatory = [k for k, v in mandatory_checks.items() if not v]
    missing_optional = [k for k, v in optional_checks.items() if not v]

    report = {
        "status": status,
        "authorized": authorized,
        "verdict": verdict,
        "timestamp": datetime.now().isoformat(),
        "mandatory_checks": mandatory_checks,
        "optional_checks": optional_checks,
        "mandatory_score": f"{mandatory_passed}/{total_mandatory}",
        "optional_score": f"{optional_passed}/{len(optional_checks)}",
        "missing_mandatory": missing_mandatory,
        "missing_optional": missing_optional,
        "next_action": (
            "Proceder con diseño de arquitectura definitiva y modelo de datos real."
            if authorized else
            "Completar las preguntas críticas faltantes con el equipo TI del cliente antes de continuar."
        )
    }

    report_path = REPORTS_DIR / f"gatekeeper_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report["report_saved"] = str(report_path)

    return report


# ─────────────────────────────────────────
# SERVIDOR MCP - JSON-RPC 2.0 sobre stdio
# ─────────────────────────────────────────
TOOLS_MANIFEST = [
    {
        "name": "mcp_discovery_audit_perimeter",
        "description": (
            "Fase 0 Telco: Diagnóstica conectividad, SSL, WAF y latencia de los endpoints del cliente. "
            "Detecta bloqueos, redirecciones y políticas restrictivas perimetrales."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_url": {"type": "string", "description": "URL o dominio del cliente Telco a auditar"},
                "port": {"type": "integer", "default": 443, "description": "Puerto TCP (por defecto 443)"}
            },
            "required": ["target_url"]
        }
    },
    {
        "name": "mcp_discovery_inspect_db_schema",
        "description": (
            "Fase 0 Telco: Inspecciona la estructura real de una base de datos SQLite entregada por el cliente. "
            "Extrae tablas, columnas, tipos, índices y llaves foráneas para el Mapping Manifesto."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Ruta absoluta del archivo SQLite del cliente"}
            },
            "required": ["db_path"]
        }
    },
    {
        "name": "mcp_discovery_parse_api_spec",
        "description": (
            "Fase 0 Telco: Parsea contratos de API en formato OpenAPI 3.x, Swagger 2.0 o Postman Collection. "
            "Extrae endpoints, autenticación, esquemas y cobertura Telco (saldo, plan, pago, abonado)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec_path": {"type": "string", "description": "Ruta al archivo .yaml/.json de la especificación API"},
            },
            "required": ["spec_path"]
        }
    },
    {
        "name": "mcp_discovery_generate_matrix",
        "description": (
            "Fase 0 Telco: Genera el cuestionario completo de levantamiento de información para ser "
            "diligenciado por el equipo TI del cliente. Produce archivo Markdown listo para enviar."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "default": "Movilnet Venezuela",
                                "description": "Nombre oficial del cliente Telco"},
                "output_format": {"type": "string", "default": "markdown", "enum": ["markdown"]}
            }
        }
    },
    {
        "name": "mcp_discovery_gatekeeper",
        "description": (
            "Fase 0 Telco: Valida si el documento de levantamiento de información está suficientemente completo "
            "para autorizar el paso a Fase 1 (diseño y desarrollo). Emite certificado APROBADO / PARCIAL / BLOQUEADO."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "discovery_doc_path": {"type": "string",
                                      "description": "Ruta al documento Markdown de levantamiento diligenciado"}
            },
            "required": ["discovery_doc_path"]
        }
    }
]


class DiscoveryMcpServer:
    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        method = req.get("method")
        params = req.get("params", {})
        req_id = req.get("id")

        if method == "initialize":
            result = {
                "serverInfo": {
                    "name": "telco-discovery-mcp",
                    "version": "1.0.0",
                    "description": "Fase 0 Telco Discovery Suite - AI_Movilnet_300926"
                },
                "capabilities": {"tools": {}}
            }
        elif method == "tools/list":
            result = {"tools": TOOLS_MANIFEST}

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            dispatch = {
                "mcp_discovery_audit_perimeter": lambda a: audit_perimeter(
                    a["target_url"], a.get("port", 443)),
                "mcp_discovery_inspect_db_schema": lambda a: inspect_db_schema(a["db_path"]),
                "mcp_discovery_parse_api_spec": lambda a: parse_api_spec(a["spec_path"]),
                "mcp_discovery_generate_matrix": lambda a: generate_discovery_matrix(
                    a.get("client_name", "Movilnet Venezuela"),
                    a.get("output_format", "markdown")
                ),
                "mcp_discovery_gatekeeper": lambda a: gatekeeper_validate(a["discovery_doc_path"]),
            }

            if tool_name in dispatch:
                try:
                    content = dispatch[tool_name](args)
                except Exception as e:
                    content = {"error": str(e)}
            else:
                return {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

            result = {"content": [{"type": "text", "text": json.dumps(content, indent=2, ensure_ascii=False)}]}
        else:
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601, "message": f"Method not supported: {method}"}}

        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def run_stdio(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                resp = self.handle_request(req)
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
            except Exception as e:
                err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Telco Discovery MCP Server - Fase 0")
    parser.add_argument("--test", action="store_true", help="Ejecutar pruebas de autovalidación")
    parser.add_argument("--generate-matrix", action="store_true", help="Generar cuestionario de levantamiento")
    parser.add_argument("--audit-url", type=str, help="Auditar URL/dominio del cliente")
    parser.add_argument("--inspect-db", type=str, help="Inspeccionar base de datos SQLite")
    args = parser.parse_args()

    if args.test:
        from tests.test_discovery_mcp import run_self_test
        sys.exit(0 if run_self_test() else 1)
    elif args.generate_matrix:
        result = generate_discovery_matrix()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.audit_url:
        result = audit_perimeter(args.audit_url)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.inspect_db:
        result = inspect_db_schema(args.inspect_db)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        server = DiscoveryMcpServer()
        server.run_stdio()
