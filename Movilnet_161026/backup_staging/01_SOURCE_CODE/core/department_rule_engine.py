#!/usr/bin/env python3
"""
core/department_rule_engine.py — Motor de Reglas Departamentales Hot-Reload
===========================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal

Permite a los 5 departamentos de Movilnet (Comercial, Finanzas, Atención, Seguridad y NOC)
actualizar sus políticas de negocio en caliente con cero caídas (<5ms en memoria volátil).
Implementa un cerrojo atómico multihilo `threading.RLock()` y verificación estricta de tipos.
"""

from __future__ import annotations

import os
import sys
import json
import time
import hashlib
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RULES_DIR = PROJECT_ROOT / "config" / "department_rules"


# ============================================================================
# MODELOS DE DOMINIO TIPADOS (Pilar III: Type Safety)
# ============================================================================

@dataclass
class PlanSpec:
    id: str
    name: str
    data_quota_gb: float
    price_bs: float
    minutes_movilnet: Any
    minutes_other: int
    sms: int
    description: str
    is_active: bool = True


@dataclass
class CommercialRules:
    department: str
    version: str
    last_updated: str
    plans_catalog: List[PlanSpec]
    portability_campaign: Dict[str, Any]
    seasonal_promotions: List[Dict[str, Any]]


@dataclass
class FinanceRules:
    department: str
    version: str
    last_updated: str
    bcv_parameters: Dict[str, Any]
    c2p_recharge_limits: Dict[str, Any]
    official_receiver_account: Dict[str, Any]
    enabled_banks_sudeban: List[Dict[str, Any]]
    billing_invariants: Dict[str, Any]


@dataclass
class CustomerCareRules:
    department: str
    version: str
    last_updated: str
    fastpath_intents: Dict[str, Any]
    human_handoff_schedule: Dict[str, Any]
    claim_sla_hours: Dict[str, int]
    tone_and_voice: Dict[str, Any]


@dataclass
class SecurityRules:
    department: str
    version: str
    last_updated: str
    imei_rules: Dict[str, Any]
    kyc_rules: Dict[str, Any]
    zero_pii_policy: Dict[str, Any]
    conatel_compliance: Dict[str, Any]


@dataclass
class NocRules:
    department: str
    version: str
    last_updated: str
    proactive_bulletins: List[Dict[str, Any]]
    monitoring_thresholds: Dict[str, Any]
    radiobase_technologies: List[Dict[str, Any]]


@dataclass
class MasterCatalogSnapshot:
    """Instantánea inmutable de todas las reglas en memoria."""
    timestamp: float
    master_hash: str
    comercial: CommercialRules
    finanzas: FinanceRules
    atencion: CustomerCareRules
    seguridad: SecurityRules
    noc: NocRules
    file_hashes: Dict[str, str] = field(default_factory=dict)


# ============================================================================
# MOTOR SINGLETON DE RECARGA EN CALIENTE
# ============================================================================

class DepartmentRuleEngine:
    """
    Motor Soberano de Reglas Departamentales para el Asistente Movilnet (MOVI).
    Gestiona la ingesta, validación, actualización atómica multihilo y consulta
    de reglas en memoria en tiempo récord (<5 ms).
    """

    _instance: Optional[DepartmentRuleEngine] = None
    _singleton_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, rules_dir: Optional[Path] = None):
        if getattr(self, "_initialized", False):
            return

        self.rules_dir = rules_dir or RULES_DIR
        self._rw_lock = threading.RLock()
        self._snapshot: Optional[MasterCatalogSnapshot] = None
        self._reload_count: int = 0
        self._last_reload_duration_ms: float = 0.0

        # Carga inicial obligatoria
        self.reload_rules()
        self._initialized = True

    @classmethod
    def get_instance(cls) -> DepartmentRuleEngine:
        if cls._instance is None:
            cls._instance = DepartmentRuleEngine()
        return cls._instance

    def reload_rules(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Recarga todos los catálogos JSON desde disco hacia memoria volátil.
        Aplica validaciones de invariantes antes de conmutar el puntero en memoria.
        """
        start_time = time.perf_counter()

        if not self.rules_dir.exists():
            return False, f"Directorio de reglas inexistente: {self.rules_dir}", {}

        try:
            file_hashes: Dict[str, str] = {}

            def _load_json(filename: str) -> Dict[str, Any]:
                path = self.rules_dir / filename
                if not path.exists():
                    raise FileNotFoundError(f"Archivo de reglas no encontrado: {path}")
                content = path.read_text(encoding="utf-8")
                h = hashlib.sha256(content.encode("utf-8")).hexdigest()
                file_hashes[filename] = h
                return json.loads(content)

            raw_comercial = _load_json("comercial_ventas.json")
            raw_finanzas = _load_json("finanzas_c2p.json")
            raw_atencion = _load_json("atencion_cliente.json")
            raw_seguridad = _load_json("seguridad_conatel.json")
            raw_noc = _load_json("operaciones_noc.json")

            # 1. Validación de Invariantes de Dominio
            self._validate_invariants(raw_comercial, raw_finanzas, raw_atencion, raw_seguridad, raw_noc)

            # 2. Conversión a DTOs fuertemente tipados
            plans = [PlanSpec(**p) for p in raw_comercial.get("plans_catalog", [])]
            comercial_obj = CommercialRules(
                department=raw_comercial["department"],
                version=raw_comercial["version"],
                last_updated=raw_comercial["last_updated"],
                plans_catalog=plans,
                portability_campaign=raw_comercial["portability_campaign"],
                seasonal_promotions=raw_comercial["seasonal_promotions"]
            )

            finanzas_obj = FinanceRules(
                department=raw_finanzas["department"],
                version=raw_finanzas["version"],
                last_updated=raw_finanzas["last_updated"],
                bcv_parameters=raw_finanzas["bcv_parameters"],
                c2p_recharge_limits=raw_finanzas["c2p_recharge_limits"],
                official_receiver_account=raw_finanzas["official_receiver_account"],
                enabled_banks_sudeban=raw_finanzas["enabled_banks_sudeban"],
                billing_invariants=raw_finanzas["billing_invariants"]
            )

            atencion_obj = CustomerCareRules(
                department=raw_atencion["department"],
                version=raw_atencion["version"],
                last_updated=raw_atencion["last_updated"],
                fastpath_intents=raw_atencion["fastpath_intents"],
                human_handoff_schedule=raw_atencion["human_handoff_schedule"],
                claim_sla_hours=raw_atencion["claim_sla_hours"],
                tone_and_voice=raw_atencion["tone_and_voice"]
            )

            seguridad_obj = SecurityRules(
                department=raw_seguridad["department"],
                version=raw_seguridad["version"],
                last_updated=raw_seguridad["last_updated"],
                imei_rules=raw_seguridad["imei_rules"],
                kyc_rules=raw_seguridad["kyc_rules"],
                zero_pii_policy=raw_seguridad["zero_pii_policy"],
                conatel_compliance=raw_seguridad["conatel_compliance"]
            )

            noc_obj = NocRules(
                department=raw_noc["department"],
                version=raw_noc["version"],
                last_updated=raw_noc["last_updated"],
                proactive_bulletins=raw_noc["proactive_bulletins"],
                monitoring_thresholds=raw_noc["monitoring_thresholds"],
                radiobase_technologies=raw_noc["radiobase_technologies"]
            )

            # Master Hash
            hasher = hashlib.sha256()
            for k in sorted(file_hashes.keys()):
                hasher.update(file_hashes[k].encode("utf-8"))
            master_hash = hasher.hexdigest()

            # 3. Conmutación Atómica Protegida por Cerrojo
            new_snapshot = MasterCatalogSnapshot(
                timestamp=time.time(),
                master_hash=master_hash,
                comercial=comercial_obj,
                finanzas=finanzas_obj,
                atencion=atencion_obj,
                seguridad=seguridad_obj,
                noc=noc_obj,
                file_hashes=file_hashes
            )

            duration_ms = (time.perf_counter() - start_time) * 1000.0

            with self._rw_lock:
                self._snapshot = new_snapshot
                self._reload_count += 1
                self._last_reload_duration_ms = duration_ms

            metadata = {
                "master_hash": master_hash,
                "duration_ms": round(duration_ms, 2),
                "reload_count": self._reload_count,
                "rules_loaded": {
                    "plans_count": len(plans),
                    "banks_count": len(finanzas_obj.enabled_banks_sudeban),
                    "intents_count": len(atencion_obj.fastpath_intents),
                    "bulletins_count": len(noc_obj.proactive_bulletins)
                }
            }
            return True, f"Reglas departamentales recargadas exitosamente en {duration_ms:.2f} ms", metadata

        except Exception as e:
            return False, f"Fallo en recarga de reglas: {str(e)}", {}

    def _validate_invariants(
        self,
        comercial: Dict[str, Any],
        finanzas: Dict[str, Any],
        atencion: Dict[str, Any],
        seguridad: Dict[str, Any],
        noc: Dict[str, Any]
    ) -> None:
        """Verifica formalmente las invariantes de negocio no negociables."""
        # Invariante 1: Planes deben tener precio positivo y cuota válida
        plans = comercial.get("plans_catalog", [])
        if not plans:
            raise ValueError("Invariante Comercial: plans_catalog no puede estar vacío.")
        for p in plans:
            if p.get("price_bs", 0) <= 0:
                raise ValueError(f"Invariante Comercial: Plan {p.get('id')} debe tener precio positivo.")

        # Invariante 2: Límites de recarga deben ser coherentes
        limits = finanzas.get("c2p_recharge_limits", {})
        min_bs = limits.get("min_amount_bs", 0)
        max_bs = limits.get("max_amount_bs", 0)
        if min_bs <= 0 or max_bs <= min_bs:
            raise ValueError(f"Invariante Finanzas: min_amount_bs ({min_bs}) debe ser > 0 y menor que max_amount_bs ({max_bs}).")

        # Invariante 3: Receptor oficial debe coincidir con la parametrización de MOVI
        rcv = finanzas.get("official_receiver_account", {})
        phone_digits = rcv.get("receiver_phone", "").replace("-", "").replace("+", "").replace(" ", "")
        if "04241533712" not in phone_digits:
            raise ValueError(f"Invariante Finanzas: receiver_phone ({rcv.get('receiver_phone')}) debe corresponder al número oficial 0424-1533712.")

        # Invariante 4: Reglas IMEI deben exigir 15 dígitos y algoritmo Luhn
        imei_rules = seguridad.get("imei_rules", {})
        if imei_rules.get("length") != 15 or imei_rules.get("algorithm") != "luhn":
            raise ValueError("Invariante Seguridad: IMEI debe tener longitud 15 y algoritmo 'luhn'.")

        # Invariante 5: NOC debe tener boletines estructurados
        bulletins = noc.get("proactive_bulletins", [])
        for b in bulletins:
            if not b.get("incident_id") or not b.get("region"):
                raise ValueError("Invariante NOC: Cada boletín debe tener incident_id y region.")

    # ========================================================================
    # MÉTODOS DE CONSULTA ULTRA-RÁPIDOS (<1 ms)
    # ========================================================================

    def get_snapshot(self) -> MasterCatalogSnapshot:
        with self._rw_lock:
            if self._snapshot is None:
                raise RuntimeError("El motor de reglas no posee instantánea activa.")
            return self._snapshot

    def get_commercial_rules(self) -> CommercialRules:
        return self.get_snapshot().comercial

    def get_finance_rules(self) -> FinanceRules:
        return self.get_snapshot().finanzas

    def get_customer_care_rules(self) -> CustomerCareRules:
        return self.get_snapshot().atencion

    def get_security_rules(self) -> SecurityRules:
        return self.get_snapshot().seguridad

    def get_noc_rules(self) -> NocRules:
        return self.get_snapshot().noc

    def find_proactive_bulletin_for_region(self, region_or_city: str) -> Optional[Dict[str, Any]]:
        """Busca si existe un boletín activo para la región indicada."""
        clean_target = region_or_city.strip().lower()
        noc = self.get_noc_rules()
        for b in noc.proactive_bulletins:
            if b.get("status") in ["IN_PROGRESS", "DISPATCHED"]:
                if b.get("region", "").lower() in clean_target:
                    return b
                for mun in b.get("municipalities", []):
                    if mun.lower() in clean_target:
                        return b
        return None

    def match_fastpath_intent(self, user_message: str) -> Optional[Tuple[str, str]]:
        """Determina si el mensaje califica para resolución FastPath determinista."""
        msg = user_message.lower().strip()
        atencion = self.get_customer_care_rules()
        for intent_id, intent_data in atencion.fastpath_intents.items():
            for kw in intent_data.get("keywords", []):
                if kw in msg:
                    template = intent_data.get("response_template", "")
                    return intent_id, template
        return None

    def get_status_telemetry(self) -> Dict[str, Any]:
        """Retorna telemetría formal para endpoints de observabilidad y diagnósticos."""
        with self._rw_lock:
            snap = self._snapshot
            return {
                "status": "ONLINE",
                "master_hash": snap.master_hash if snap else "NONE",
                "reload_count": self._reload_count,
                "last_reload_duration_ms": self._last_reload_duration_ms,
                "timestamp": snap.timestamp if snap else 0.0,
                "files_audited": snap.file_hashes if snap else {},
                "summary": {
                    "plans_available": len(snap.comercial.plans_catalog) if snap else 0,
                    "c2p_receiver_phone": snap.finanzas.official_receiver_account.get("receiver_phone") if snap else "",
                    "active_noc_bulletins": len(snap.noc.proactive_bulletins) if snap else 0,
                    "fastpath_intents_registered": len(snap.atencion.fastpath_intents) if snap else 0
                }
            }


if __name__ == "__main__":
    engine = DepartmentRuleEngine.get_instance()
    success, msg, meta = engine.reload_rules()
    print("=" * 70)
    print("🏛️ MOTOR DE REGLAS DEPARTAMENTALES — TEST DE AUTO-VERIFICACIÓN")
    print("=" * 70)
    print(f"Estado de Carga: {'✅ EXITOSO' if success else '❌ FALLIDO'}")
    print(f"Mensaje: {msg}")
    print(f"Telemetría:")
    print(json.dumps(engine.get_status_telemetry(), indent=2, ensure_ascii=False))

    # Prueba de búsqueda rápida
    bulletin = engine.find_proactive_bulletin_for_region("Maracaibo")
    print("\n🔍 Test Búsqueda Boletín NOC (Maracaibo):")
    if bulletin:
        print(f"  ➔ Encontrado: {bulletin['incident_id']} - {bulletin['customer_message'][:80]}...")
    else:
        print("  ➔ Ninguno")
