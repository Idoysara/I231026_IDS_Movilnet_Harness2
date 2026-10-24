#!/usr/bin/env python3
"""
scripts/audit_service_refactor_parity.py — Auditor de Paridad "Golden Master" de api/service.py
==============================================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilares II, III, IV, V, VI)
Capítulo: 216 — Refactorización Hexagonal de api/service.py

Técnica: Characterization Testing / Golden Master.
    1. --capture : ejecuta un corpus de peticiones contra el MONOLITO ORIGINAL (referencia
                   inmutable), DOS VECES, y detecta empíricamente los campos volátiles
                   (timestamps, uptime...) comparando ambas capturas. Guarda el golden.
    2. --verify  : reproduce exactamente las mismas peticiones contra el `api.service`
                   ACTUAL (refactorizado) y exige igualdad con el golden, ignorando solo
                   los campos volátiles detectados. Cualquier divergencia => exit 1.
    3. --test    : auto-verificación de los helpers de normalización (sin servicio).

El corpus es de SOLO LECTURA / validación (sin mutaciones de dominio: no ejecuta pagos C2P
reales, ni bloqueos EIR, ni envía mensajes), por lo que es seguro de ejecutar en cualquier
momento sin alterar datos.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Evita registrar trazas vivas / despachos a n8n durante la auditoría (cero efectos laterales).
os.environ.setdefault("PYTEST_CURRENT_TEST", "service_refactor_parity_audit")

MONOLITH_REFERENCE = PROJECT_ROOT / "api" / "service_monolith_backup_pre_refactor.py.bak"
GOLDEN_PATH = PROJECT_ROOT / "tests" / "fixtures" / "service_parity_golden.json"
REPORT_DIR = PROJECT_ROOT / "reports"

MASK = "<VOLATILE>"
IGNORED_HEADERS = {"content-length", "date"}
JSON_HEADERS = {"Content-Type": "application/json"}


class ParityAuditError(RuntimeError):
    """Error de infraestructura de la auditoría (no una divergencia de paridad)."""


@dataclass
class Case:
    """Una petición del corpus. mode='strict' compara valores; 'shape' solo estructura/tipos."""
    case_id: str
    method: str
    path: str
    body: Optional[Any] = None
    raw_body: Optional[str] = None
    mode: str = "strict"

    def body_bytes(self) -> bytes:
        if self.raw_body is not None:
            return self.raw_body.encode("utf-8")
        if self.body is not None:
            return json.dumps(self.body).encode("utf-8")
        return b""

    def to_dict(self) -> Dict[str, Any]:
        return {"case_id": self.case_id, "method": self.method, "path": self.path,
                "body": self.body, "raw_body": self.raw_body, "mode": self.mode}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Case":
        return Case(d["case_id"], d["method"], d["path"], d.get("body"), d.get("raw_body"), d.get("mode", "strict"))


# ------------------------------------------------------------------------------
# Helpers puros de normalización (probados en --test)
# ------------------------------------------------------------------------------

def shape_of(value: Any) -> Any:
    """Reduce un valor JSON a su estructura de claves y tipos."""
    if isinstance(value, dict):
        return {k: shape_of(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [shape_of(value[0])] if value else []
    return type(value).__name__


def diff_mask(a: Any, b: Any) -> Any:
    """Fusiona dos capturas idénticas: las hojas que difieren (volátiles) pasan a MASK."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return MASK
        return {k: diff_mask(a[k], b[k]) for k in a}
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return MASK
        return [diff_mask(x, y) for x, y in zip(a, b)]
    return a if a == b else MASK


def matches(golden: Any, actual: Any, path: str = "$") -> List[str]:
    """Compara golden (con MASK) contra actual. Retorna lista de divergencias (vacía = paridad)."""
    if golden == MASK:
        return []
    if isinstance(golden, dict):
        if not isinstance(actual, dict):
            return [f"{path}: se esperaba objeto, llegó {type(actual).__name__}"]
        issues: List[str] = []
        for k in sorted(set(golden) | set(actual)):
            if k not in golden:
                issues.append(f"{path}.{k}: clave NUEVA no presente en el golden")
            elif k not in actual:
                issues.append(f"{path}.{k}: clave AUSENTE respecto al golden")
            else:
                issues.extend(matches(golden[k], actual[k], f"{path}.{k}"))
        return issues
    if isinstance(golden, list):
        if not isinstance(actual, list):
            return [f"{path}: se esperaba lista, llegó {type(actual).__name__}"]
        if len(golden) != len(actual):
            return [f"{path}: longitud {len(actual)} != {len(golden)}"]
        out: List[str] = []
        for i, (g, a) in enumerate(zip(golden, actual)):
            out.extend(matches(g, a, f"{path}[{i}]"))
        return out
    return [] if golden == actual else [f"{path}: {actual!r} != {golden!r}"]


def load_module(name: str, file_path: Path) -> ModuleType:
    """Carga un módulo desde una ruta arbitraria (incluye el respaldo .bak del monolito)."""
    if not file_path.exists():
        raise ParityAuditError(f"No existe el archivo de referencia: {file_path}")
    loader = importlib.machinery.SourceFileLoader(name, str(file_path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise ParityAuditError(f"No se pudo crear spec para {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


# ------------------------------------------------------------------------------
# Ejecución del corpus
# ------------------------------------------------------------------------------

def record_response(case: Case, status: int, headers: Dict[str, str], data: bytes) -> Dict[str, Any]:
    """Convierte una respuesta de dispatch() en un registro comparable."""
    hdrs = {k: v for k, v in sorted(headers.items()) if k.lower() not in IGNORED_HEADERS}
    content_type = headers.get("Content-Type", "")
    kind, body = "bytes", None
    if "json" in content_type:
        try:
            parsed = json.loads(data.decode("utf-8"))
            kind, body = "json", (shape_of(parsed) if case.mode == "shape" else parsed)
        except (UnicodeDecodeError, json.JSONDecodeError):
            kind = "bytes"
    if kind == "bytes":
        body = {"sha256": hashlib.sha256(data).hexdigest(), "length": len(data)}
    return {"status": status, "headers": hdrs, "kind": kind, "body": body}


def run_corpus(service: Any, cases: List[Case]) -> Dict[str, Dict[str, Any]]:
    """Ejecuta cada caso contra service.dispatch(); una excepción se registra como resultado."""
    results: Dict[str, Dict[str, Any]] = {}
    for case in cases:
        try:
            status, headers, data = service.dispatch(case.method, case.path, dict(JSON_HEADERS), case.body_bytes())
            results[case.case_id] = record_response(case, status, headers, data)
        except Exception as exc:  # noqa: BLE001 — se registra tipo+mensaje; es una auditoría, no producción
            results[case.case_id] = {"status": "EXCEPTION", "headers": {}, "kind": "exception",
                                     "body": {"type": type(exc).__name__, "message": str(exc)[:200]}}
    return results


def build_corpus(reference_service: Any) -> List[Case]:
    """Corpus de solo lectura/validación. El id de plan se deriva del catálogo real."""
    plan_id = "PLAN-INEXISTENTE"
    status, _h, data = reference_service.dispatch("GET", "/api/v1/catalog/plans", dict(JSON_HEADERS), b"")
    if status == 200:
        try:
            payload = json.loads(data.decode("utf-8"))
            plans = payload.get("plans") or payload.get("items") or payload.get("data") or []
            if plans and isinstance(plans, list):
                plan_id = str(plans[0].get("id") or plans[0].get("plan_id") or plan_id)
        except (ValueError, AttributeError):
            pass

    c: List[Case] = []
    add = c.append
    # Observabilidad y contrato
    add(Case("health", "GET", "/health", mode="shape"))
    add(Case("api_health", "GET", "/api/v1/health", mode="shape"))
    add(Case("status", "GET", "/api/v1/status", mode="shape"))
    add(Case("openapi", "GET", "/openapi.json"))
    add(Case("openapi_v1", "GET", "/api/v1/openapi.json"))
    add(Case("docs", "GET", "/docs"))
    add(Case("options_status", "OPTIONS", "/api/v1/status"))
    # Catálogo
    add(Case("plans", "GET", "/api/v1/catalog/plans"))
    add(Case("plan_by_id", "GET", f"/api/v1/catalog/plans/{plan_id}"))
    add(Case("plan_missing", "GET", "/api/v1/catalog/plans/PLAN-NO-EXISTE-XYZ"))
    add(Case("banks", "GET", "/api/v1/banks"))
    # Rutas inexistentes
    add(Case("unknown_get", "GET", "/ruta/no/registrada"))
    add(Case("unknown_post", "POST", "/api/v1/no-existe", body={}))
    # Saldos / pagos / seguridad: SOLO entradas inválidas o de lectura (cero mutación)
    add(Case("balance_empty", "POST", "/api/v1/subscribers/balance", body={}))
    add(Case("balance_bad_phone", "POST", "/api/v1/subscribers/balance", body={"msisdn": "123"}))
    add(Case("balance_competitor", "POST", "/api/v1/subscribers/balance", body={"msisdn": "04141234567", "cid": "V-12345678"}))
    add(Case("balance_invalid_json", "POST", "/api/v1/subscribers/balance", raw_body="{no es json"))
    add(Case("c2p_empty", "POST", "/api/v1/payments/c2p", body={}))
    add(Case("c2p_bad_bank", "POST", "/api/v1/payments/c2p",
             body={"msisdn": "04161234567", "cid": "V-12345678", "bank_code": "9", "amount": 10}))
    add(Case("c2p_negative_amount", "POST", "/api/v1/payments/c2p",
             body={"msisdn": "04161234567", "cid": "V-12345678", "bank_code": "0102", "amount": -5, "reference_id": "REF-PARITY"}))
    add(Case("c2p_invalid_json", "POST", "/api/v1/payments/c2p", raw_body="[[[["))
    add(Case("simswap_empty", "POST", "/api/v1/security/sim-swap", body={}))
    add(Case("simswap_bad_phone", "POST", "/api/v1/security/sim-swap", body={"msisdn": "xx"}))
    add(Case("eir_empty", "POST", "/api/v1/security/eir-lock", body={}))
    add(Case("eir_bad_phone", "POST", "/api/v1/security/eir-lock", body={"msisdn": "xx"}))
    # Webhooks
    add(Case("wh_deliveries", "GET", "/api/v1/webhooks/deliveries", mode="shape"))
    add(Case("wh_inbound_empty", "POST", "/api/v1/webhooks/inbound-events", body={}))
    add(Case("wh_c2p_callback_empty", "POST", "/api/v1/webhooks/c2p-callback", body={}))
    add(Case("wh_eir_callback_empty", "POST", "/api/v1/webhooks/eir-callback", body={}))
    add(Case("wh_dlq_empty", "POST", "/api/v1/webhooks/dlq/retry", body={}))
    add(Case("wh_dlq_missing", "POST", "/api/v1/webhooks/dlq/retry", body={"dlq_id": "dlq-no-existe-xyz"}))
    # Agentes (validaciones y guardas deterministas)
    add(Case("cc_empty", "POST", "/api/v1/agents/customer-care/process", body={}))
    add(Case("cc_blank_text", "POST", "/api/v1/agents/customer-care/process", body={"text": "   "}))
    add(Case("cc_prohibited_sender", "POST", "/api/v1/agents/customer-care/process",
             body={"text": "hola", "phone": "04166251587"}))
    add(Case("cc_alias_chat_empty", "POST", "/api/v1/agent/chat", body={}))
    add(Case("cc_saldo", "POST", "/api/v1/agents/customer-care/process",
             body={"text": "cual es mi saldo", "phone": "04160000001", "channel": "api"}, mode="shape"))
    add(Case("fintech_empty", "POST", "/api/v1/agents/fintech-c2p/process", body={}))
    add(Case("eir_agent_empty", "POST", "/api/v1/agents/emergency-eir/process", body={}))
    add(Case("eir_agent_status_noparam", "GET", "/api/v1/agents/emergency-eir/status"))
    add(Case("churn_predict_empty", "POST", "/api/v1/agents/retention-churn/predict", body={}))
    add(Case("churn_offer_empty", "POST", "/api/v1/agents/retention-churn/offer", body={}))
    add(Case("churn_status_noparam", "GET", "/api/v1/agents/retention-churn/status"))
    # NOC
    add(Case("noc_metrics", "GET", "/api/v1/metrics/live", mode="shape"))
    add(Case("noc_status", "GET", "/api/v1/noc/status", mode="shape"))
    # WhatsApp (solo validaciones, sin envío)
    add(Case("wa_send_empty", "POST", "/api/v1/whatsapp/send", body={}))
    add(Case("wa_gateway_bad_mode", "POST", "/api/v1/whatsapp/gateway-mode", body={"mode": "MODO_INVALIDO"}))
    # PWA estática y seguridad de rutas (path traversal debe fallar igual)
    add(Case("ui_pwa_index", "GET", "/ui/pwa_stitch/index.html"))
    add(Case("ui_simulador", "GET", "/ui/pwa_stitch/simulador.html"))
    add(Case("ui_conversatorio", "GET", "/ui/monitor/conversatorio.html"))
    add(Case("ui_missing", "GET", "/ui/no/existe.html"))
    add(Case("ui_traversal", "GET", "/ui/../../.env"))
    add(Case("ui_traversal_enc", "GET", "/ui/..%2f..%2f.env"))
    add(Case("root", "GET", "/"))
    add(Case("index_html", "GET", "/index.html"))
    add(Case("simulador_alias", "GET", "/simulador"))
    add(Case("celular_alias", "GET", "/celular"))
    return c


# ------------------------------------------------------------------------------
# Modos de operación
# ------------------------------------------------------------------------------

def capture_golden() -> Dict[str, Any]:
    """Captura el golden desde el monolito original, dos veces, enmascarando lo volátil."""
    monolith = load_module("service_monolith_reference", MONOLITH_REFERENCE)
    svc_a = monolith.MovilnetAPIService()
    cases = build_corpus(svc_a)
    first = run_corpus(svc_a, cases)
    second = run_corpus(monolith.MovilnetAPIService(), cases)

    golden_results: Dict[str, Any] = {}
    volatile_cases: List[str] = []
    for case in cases:
        merged = diff_mask(first[case.case_id], second[case.case_id])
        golden_results[case.case_id] = merged
        if MASK in json.dumps(merged):
            volatile_cases.append(case.case_id)

    return {
        "schema": "service-parity-golden/1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "reference_sha256": hashlib.sha256(MONOLITH_REFERENCE.read_bytes()).hexdigest(),
        "reference_lines": len(MONOLITH_REFERENCE.read_text(encoding="utf-8").splitlines()),
        "cases": [c.to_dict() for c in cases],
        "results": golden_results,
        "cases_with_volatile_fields": volatile_cases,
    }


def verify_against_golden(golden: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    """Reproduce el corpus contra api.service ACTUAL y compara con el golden."""
    sys.modules.pop("api.service", None)
    import api.service as current  # noqa: WPS433 — import tardío deliberado

    cases = [Case.from_dict(d) for d in golden["cases"]]
    actual = run_corpus(current.MovilnetAPIService(), cases)
    rows: List[Dict[str, Any]] = []
    failures = 0
    for case in cases:
        issues = matches(golden["results"][case.case_id], actual[case.case_id])
        ok = not issues
        failures += 0 if ok else 1
        rows.append({"case_id": case.case_id, "request": f"{case.method} {case.path}",
                     "status": actual[case.case_id].get("status"), "ok": ok, "issues": issues[:8]})
    return rows, failures


def write_report(rows: List[Dict[str, Any]], failures: int, label: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"service_refactor_parity_{label}.json"
    payload = {"label": label, "generated_at": datetime.now(timezone.utc).isoformat(),
               "total": len(rows), "passed": len(rows) - failures, "failed": failures, "rows": rows}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def _self_test() -> bool:
    """Auto-verificación de los helpers puros de normalización."""
    assert shape_of({"a": 1, "b": [1, 2], "c": {"d": "x"}, "e": []}) == {"a": "int", "b": ["int"], "c": {"d": "str"}, "e": []}
    assert diff_mask({"a": 1, "t": 5}, {"a": 1, "t": 9}) == {"a": 1, "t": MASK}
    assert diff_mask([1, 2], [1, 2, 3]) == MASK, "longitudes distintas deben enmascararse"
    assert diff_mask({"a": 1}, {"b": 1}) == MASK, "claves distintas deben enmascararse"
    assert matches({"a": 1, "t": MASK}, {"a": 1, "t": "cualquiera"}) == [], "el MASK debe aceptar cualquier valor"
    assert matches({"a": 1}, {"a": 2}), "una diferencia real debe detectarse"
    assert matches({"a": 1}, {"a": 1, "extra": 1}), "una clave nueva debe detectarse"
    assert matches({"a": 1, "b": 2}, {"a": 1}), "una clave ausente debe detectarse"
    assert matches([1, 2], [1]), "una lista más corta debe detectarse"
    assert matches({"a": {"b": 1}}, {"a": [1]}), "un cambio de tipo debe detectarse"
    case = Case("x", "POST", "/p", body={"k": 1})
    assert json.loads(case.body_bytes()) == {"k": 1}
    assert Case("y", "POST", "/p", raw_body="{mal").body_bytes() == b"{mal"
    assert Case.from_dict(case.to_dict()).to_dict() == case.to_dict(), "round-trip del caso"
    rec = record_response(Case("z", "GET", "/z"), 200, {"Content-Type": "text/html", "Content-Length": "9"}, b"<html></>")
    assert rec["kind"] == "bytes" and rec["body"]["length"] == 9 and "Content-Length" not in rec["headers"]
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditor de paridad golden-master de api/service.py (Cap. 216)")
    parser.add_argument("--capture", action="store_true", help="Captura el golden desde el monolito original")
    parser.add_argument("--verify", action="store_true", help="Verifica el service.py actual contra el golden")
    parser.add_argument("--label", default="current", help="Etiqueta del reporte (p. ej. fase1)")
    parser.add_argument("--test", action="store_true", help="Auto-verificación de los helpers")
    args = parser.parse_args()

    if args.test:
        _self_test()
        print("✅ [TEST PASS] audit_service_refactor_parity: helpers de normalización aprobados (100%).")
        return 0

    if args.capture:
        golden = capture_golden()
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_text(json.dumps(golden, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"📸 Golden capturado: {len(golden['cases'])} casos | referencia={golden['reference_lines']} líneas "
              f"| SHA-256={golden['reference_sha256'][:16]}…")
        print(f"   Casos con campos volátiles detectados empíricamente: {len(golden['cases_with_volatile_fields'])}")
        print(f"   ➜ {GOLDEN_PATH}")
        return 0

    if args.verify:
        if not GOLDEN_PATH.exists():
            raise ParityAuditError(f"Golden inexistente: ejecute --capture primero ({GOLDEN_PATH})")
        golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        rows, failures = verify_against_golden(golden)
        report = write_report(rows, failures, args.label)
        print("=" * 78)
        print(f"🔬 AUDITORÍA DE PARIDAD — service.py ACTUAL vs MONOLITO ORIGINAL ({args.label})")
        print("=" * 78)
        for r in rows:
            mark = "✅" if r["ok"] else "❌"
            print(f"  {mark} {r['case_id']:<28} {r['request']:<58} -> {r['status']}")
            for issue in r["issues"]:
                print(f"       ↳ {issue}")
        print("-" * 78)
        print(f"  TOTAL={len(rows)}  PASS={len(rows) - failures}  FAIL={failures}   reporte: {report.name}")
        print("=" * 78)
        return 0 if failures == 0 else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
