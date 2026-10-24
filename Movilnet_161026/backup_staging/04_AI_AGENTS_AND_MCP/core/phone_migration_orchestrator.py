"""
core/phone_migration_orchestrator.py
==============================================================================
Orquestador Transaccional de Migración Universal de Líneas Telefónicas
Cumple: Pilares I al VII de Excelencia Técnica & Protocolo Decagonal (10 Fases).
==============================================================================
"""

from __future__ import annotations

import os
import sys
import re
import ast
import json
import time
import shutil
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.phone_migration_models import (
    PhoneDescriptor,
    MigrationPlan,
    ComponentImpactDetail,
    CarrierOperator
)


class PhoneMigrationOrchestrator:
    """
    Motor Maestro de Migración Universal de Líneas para Movilnet Core.
    Asegura atomicidad, validación estática AST, preservación histórica y rollback total.
    """

    EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".backups", "docs", "reports"}
    INCLUDED_EXTENSIONS = {".py", ".html", ".js", ".json", ".env", ".yml", ".yaml", ".sh"}

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or PROJECT_ROOT
        self.backup_base_dir = self.root_dir / ".backups" / "phone_migration"

    def analyze_plan(
        self,
        from_phone_str: str,
        to_phone_str: str,
        bot_name: str = "MOVI"
    ) -> MigrationPlan:
        """
        Fase 1 y 2: Diagnostica en seco (Dry-Run) el impacto de la migración sin alterar disco.
        """
        from_desc = PhoneDescriptor.from_string(from_phone_str)
        to_desc = PhoneDescriptor.from_string(to_phone_str)
        plan_id = f"MIG-{int(time.time())}-{hashlib.sha256(f'{from_phone_str}:{to_phone_str}'.encode()).hexdigest()[:8]}"

        components: List[ComponentImpactDetail] = []
        total_matches = 0
        total_files = 0

        # Mapeo de reemplazos ordenado (de más específico a más general)
        replacement_pairs = self._build_replacement_pairs(from_desc, to_desc)

        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            # Excluir directorios protegidos
            dirnames[:] = [d for d in dirnames if d not in self.EXCLUDED_DIRS]
            
            for f in filenames:
                ext = Path(f).suffix.lower()
                if ext not in self.INCLUDED_EXTENSIONS and f != ".env":
                    continue

                file_path = Path(dirpath) / f
                rel_path = file_path.relative_to(self.root_dir)

                # Proteger scripts de auditoría histórica
                if f in ("audit_military_phone_migration.py", "audit_docs_evidence.py"):
                    continue

                total_files += 1
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fl:
                        content = fl.read()
                except Exception:
                    continue

                file_matches = 0
                lines_affected: List[int] = []
                previews: List[str] = []

                for idx, line in enumerate(content.splitlines(), 1):
                    for old_pat, new_val in replacement_pairs:
                        if old_pat in line:
                            file_matches += 1
                            total_matches += 1
                            if idx not in lines_affected:
                                lines_affected.append(idx)
                                previews.append(f"L{idx}: {line.strip()[:100]}")
                            break  # Priorizar el patrón más específico para evitar doble conteo

                if file_matches > 0:
                    layer = self._classify_layer(rel_path)
                    components.append(ComponentImpactDetail(
                        target_id=str(rel_path),
                        layer=layer,
                        matches_found=file_matches,
                        lines_affected=lines_affected,
                        replacements_preview=previews[:5],
                        status="PENDING"
                    ))

        return MigrationPlan(
            plan_id=plan_id,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            from_phone=from_desc,
            to_phone=to_desc,
            bot_name=bot_name,
            total_files_analyzed=total_files,
            total_matches_detected=total_matches,
            components=components,
            dry_run=True,
            executed=False,
            success=False
        )

    def execute_migration(
        self,
        plan: MigrationPlan,
        skip_tests: bool = False
    ) -> MigrationPlan:
        """
        Fase 5, 6, 7 y 8: Ejecuta la migración atómica con snapshot de rollback y validación AST.
        """
        if not plan.components:
            plan.executed = True
            plan.success = True
            return plan

        # 1. Crear Snapshot de Respaldo
        snapshot_dir = self.backup_base_dir / plan.plan_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        plan.backup_snapshot_dir = str(snapshot_dir)

        replacement_pairs = self._build_replacement_pairs(plan.from_phone, plan.to_phone)
        modified_files: List[Path] = []

        try:
            # 2. Respaldar y Aplicar Reemplazos Quirúrgicos
            for comp in plan.components:
                src_path = self.root_dir / comp.target_id
                if not src_path.exists():
                    comp.status = "SKIPPED"
                    continue

                # Respaldar archivo preservando ruta relativa
                bak_path = snapshot_dir / comp.target_id
                bak_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, bak_path)

                with open(src_path, "r", encoding="utf-8") as fl:
                    content = fl.read()

                # Reemplazo secuencial ordenado
                new_content = content
                for old_val, new_val in replacement_pairs:
                    new_content = new_content.replace(old_val, new_val)

                # Validación de Pureza Sintáctica AST (Pilar VI) si es Python
                if src_path.suffix == ".py":
                    try:
                        ast.parse(new_content, filename=str(src_path))
                    except SyntaxError as syn_err:
                        raise RuntimeError(f"Error de sintaxis AST provocado en {comp.target_id}: {syn_err}")

                with open(src_path, "w", encoding="utf-8") as fl:
                    fl.write(new_content)

                modified_files.append(src_path)
                comp.status = "REPLACED"

            # 2.1 Sincronización y Blindaje del Protocolo PWA (Service Worker Cache & QR)
            try:
                from core.pwa_protocol_guardian import PWAProtocolGuardian
                pwa_guardian = PWAProtocolGuardian(root_dir=self.root_dir)
                if pwa_guardian.sw_path.exists():
                    sw_rel = pwa_guardian.sw_path.relative_to(self.root_dir)
                    sw_bak = snapshot_dir / sw_rel
                    sw_bak.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(pwa_guardian.sw_path, sw_bak)

                    pwa_sync = pwa_guardian.synchronize_pwa_on_migration(
                        from_phone_str=plan.from_phone.international_e164,
                        to_phone_str=plan.to_phone.international_e164,
                        bump_sw=True
                    )
                    if pwa_guardian.sw_path not in modified_files:
                        modified_files.append(pwa_guardian.sw_path)
            except Exception as pwa_err:
                print(f"⚠️ [PWA_GUARDIAN_WARN] Advertencia en sincronización PWA: {pwa_err}")

            # 2.2 Actualización de Parametrización Central (.env y SystemConfig)
            try:
                from core.system_config import SystemConfigManager
                SystemConfigManager.update_active_phone_in_env(
                    plan.to_phone.national_formatted,
                    plan.bot_name,
                    root_dir=self.root_dir
                )
            except Exception as cfg_err:
                print(f"⚠️ [CONFIG_WARN] Advertencia al actualizar parametrización .env: {cfg_err}")

            # 3. Validar con pruebas automatizadas rápidas si no se omite
            if not skip_tests:
                self._run_integrity_check(modified_files)

            # 4. Sellar la migración
            seal = self._generate_seal(modified_files)
            plan.sha256_seal = seal
            plan.executed = True
            plan.success = True
            plan.dry_run = False

            # Persistir manifiesto de migración en el snapshot
            with open(snapshot_dir / "migration_manifest.json", "w", encoding="utf-8") as fl:
                json.dump(plan.to_dict(), fl, indent=2)

            return plan

        except Exception as ex:
            # Rollback inmediato ante cualquier fallo
            self.rollback_snapshot(str(snapshot_dir))
            plan.executed = True
            plan.success = False
            for comp in plan.components:
                if comp.status == "REPLACED":
                    comp.status = "ROLLED_BACK"
                    comp.error_message = str(ex)
            raise RuntimeError(f"Falla durante la migración atómica. Rollback ejecutado: {ex}")

    def rollback_snapshot(self, snapshot_dir_str: str) -> bool:
        """
        Revierte el sistema exactamente al estado previo al inicio de la migración.
        """
        snapshot_dir = Path(snapshot_dir_str)
        if not snapshot_dir.exists():
            return False

        for root, _, files in os.walk(snapshot_dir):
            for f in files:
                if f == "migration_manifest.json":
                    continue
                bak_file = Path(root) / f
                rel_path = bak_file.relative_to(snapshot_dir)
                orig_file = self.root_dir / rel_path
                orig_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bak_file, orig_file)

        return True

    def _build_replacement_pairs(
        self,
        from_desc: PhoneDescriptor,
        to_desc: PhoneDescriptor
    ) -> List[Tuple[str, str]]:
        """
        Construye la matriz de sustitución ordenada por especificidad para evitar
        sustituciones colaterales.
        """
        return [
            # 1. URLs directas de WhatsApp
            (f"wa.me/{from_desc.international_digits}", f"wa.me/{to_desc.international_digits}"),
            (f"wa.me/{from_desc.clean_digits}", f"wa.me/{to_desc.clean_digits}"),
            # 2. WhatsApp JID
            (from_desc.whatsapp_jid, to_desc.whatsapp_jid),
            # 3. Formato Internacional E.164
            (from_desc.international_e164, to_desc.international_e164),
            # 4. Formato 0058
            (from_desc.international_0058, to_desc.international_0058),
            # 5. Formato Nacional con guión
            (from_desc.national_formatted, to_desc.national_formatted),
            # 6. Formato Internacional numérico
            (from_desc.international_digits, to_desc.international_digits),
            # 7. Formato Nacional con cero
            (from_desc.national_with_zero, to_desc.national_with_zero),
        ]

    def _classify_layer(self, path: Path) -> str:
        s = str(path)
        if s.startswith("core/"): return "CORE_MODULE"
        if s.startswith("api/"): return "API_BACKEND"
        if s.startswith("ui/"): return "UI_FRONTEND"
        if s.startswith("scripts/"): return "SCRIPT_DAEMON"
        if ".env" in s or "docker" in s: return "DOCKER_ENV"
        if s.startswith("tests/"): return "TEST_SUITE"
        return "GENERAL_COMPONENT"

    def _run_integrity_check(self, files: List[Path]) -> None:
        """Verifica que todos los archivos Python modificados compilen limpiamente."""
        for f in files:
            if f.suffix == ".py":
                with open(f, "r", encoding="utf-8") as fl:
                    ast.parse(fl.read(), filename=str(f))

    def _generate_seal(self, files: List[Path]) -> str:
        """Genera el sello criptográfico SHA-256 consolidado de todos los archivos modificados."""
        h = hashlib.sha256()
        for f in sorted(files, key=lambda x: str(x)):
            with open(f, "rb") as fl:
                h.update(fl.read())
        return h.hexdigest()


def run_self_verification() -> bool:
    """Auto-verificación matemática formal de 5 pruebas (Pilar II y V)."""
    print("🧪 [TEST 1/5] Instanciación y análisis de PhoneDescriptor...")
    d1 = PhoneDescriptor.from_string("0424-1533712")
    assert d1.international_digits == "584241533712"
    assert d1.whatsapp_jid == "584241533712@s.whatsapp.net"
    assert d1.carrier == CarrierOperator.MOVISTAR

    d2 = PhoneDescriptor.from_string("+58 416 123 4567")
    assert d2.carrier == CarrierOperator.MOVILNET
    assert d2.national_with_zero == "04161234567"

    print("🧪 [TEST 2/5] Generación de pares de sustitución ordenados...")
    orch = PhoneMigrationOrchestrator()
    pairs = orch._build_replacement_pairs(d1, d2)
    assert len(pairs) >= 6
    assert pairs[0][0] == "wa.me/584241533712"
    assert pairs[0][1] == "wa.me/584161234567"

    print("🧪 [TEST 3/5] Simulación en directorio temporal con validación AST...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        test_py = tmp_path / "test_module.py"
        test_py.write_text("BOT_NUMBER = '0424-1533712'\nWA_JID = '584241533712@s.whatsapp.net'\n")

        orch_tmp = PhoneMigrationOrchestrator(root_dir=tmp_path)
        plan = orch_tmp.analyze_plan("04241533712", "04161234567")
        assert len(plan.components) == 1
        assert plan.total_matches_detected == 2

        print("🧪 [TEST 4/5] Ejecución atómica y verificación de contenido...")
        executed_plan = orch_tmp.execute_migration(plan, skip_tests=True)
        assert executed_plan.success is True
        new_text = test_py.read_text()
        assert "0416-1234567" in new_text
        assert "584161234567@s.whatsapp.net" in new_text
        assert "0424-1533712" not in new_text

        print("🧪 [TEST 5/5] Reversión total (Rollback)...")
        assert executed_plan.backup_snapshot_dir is not None
        rolled_back = orch_tmp.rollback_snapshot(executed_plan.backup_snapshot_dir)
        assert rolled_back is True
        restored_text = test_py.read_text()
        assert "0424-1533712" in restored_text
        assert "0416-1234567" not in restored_text

    print("🏆 5/5 PRUEBAS FORMALES SUPERADAS CON 100% DE ÉXITO.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orquestador Universal de Migración Telefónica Movilnet Core")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación matemática de 5 pruebas")
    parser.add_argument("--plan", action="store_true", help="Genera reporte de impacto en seco (Dry-Run)")
    parser.add_argument("--execute", action="store_true", help="Ejecuta la migración atómica en disco")
    parser.add_argument("--rollback", type=str, help="Ejecuta reversión indicando directorio de snapshot")
    parser.add_argument("--from-phone", type=str, default="04166251587", help="Número origen a sustituir")
    parser.add_argument("--to-phone", type=str, default="04241533712", help="Nuevo número destino")
    parser.add_argument("--bot-name", type=str, default="MOVI", help="Nombre del bot oficial")

    args = parser.parse_args()

    if args.test:
        run_self_verification()
        sys.exit(0)

    orchestrator = PhoneMigrationOrchestrator()

    if args.rollback:
        success = orchestrator.rollback_snapshot(args.rollback)
        print(f"Rollback status: {'EXITOSO' if success else 'FALLIDO'}")
        sys.exit(0 if success else 1)

    plan = orchestrator.analyze_plan(args.from_phone, args.to_phone, args.bot_name)

    if args.plan:
        print("\n" + "=" * 70)
        print(f"📋 PLAN DE MIGRACIÓN: {plan.from_phone.international_e164} ➔ {plan.to_phone.international_e164}")
        print("=" * 70)
        print(f"Archivos analizados: {plan.total_files_analyzed}")
        print(f"Coincidencias detectadas: {plan.total_matches_detected}")
        print(f"Componentes afectados: {len(plan.components)}")
        for comp in plan.components:
            print(f"  • [{comp.layer}] {comp.target_id} ({comp.matches_found} coincidencias)")
        print("=" * 70)
        sys.exit(0)

    if args.execute:
        print(f"🚀 Ejecutando migración atómica: {plan.from_phone.international_e164} ➔ {plan.to_phone.international_e164}...")
        res = orchestrator.execute_migration(plan)
        print(f"✅ Migración finalizada con éxito. Sello SHA-256: {res.sha256_seal}")
        print(f"📁 Snapshot de respaldo: {res.backup_snapshot_dir}")
        sys.exit(0)

    parser.print_help()
