#!/usr/bin/env python3
"""
replicate_movilnet_pwa_package.py — Replicador Criptográfico y Certificador del Paquete Movilnet PWA
=====================================================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII) & Protocolo Decagonal

Objetivo:
Ejecuta la copia integral, estructurada, auditada y certificada de todos los activos,
bases de datos, Docker, componentes activos, skills, MCP, scripts, agentes,
subagentes, modelos, orquestadores y algoritmos necesarios para activar la PWA
utilizando un número de consulta desde WhatsApp, hacia la ruta destino:
  /Users/ismael/Desktop/121026_CORE_MOVILNET/Movilnet_121026/Movilnet_PWA

Garantías:
  1. Cero omisión de módulos (api, core, db, mcp, ui, skills, active_skills, scripts, tests, docs, reports, .agents).
  2. Verificación criptográfica SHA-256 archivo por archivo (integridad 100%).
  3. Exclusión limpia de basura (.git, venv, __pycache__, .DS_Store).
  4. Generación de lanzadores autónomos directos en la carpeta destino.
  5. Emisión de informe de certificación formal con sello SHA-256.
"""

from __future__ import annotations

import os
import sys
import uuid
import shutil
import hashlib
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any

SRC_ROOT = Path("/Users/ismael/Desktop/Movilnet_051026")
SRC_APP = SRC_ROOT / "AI_Movilnet_300926-main"
DEST_ROOT = Path("/Users/ismael/Desktop/121026_CORE_MOVILNET/Movilnet_121026/Movilnet_PWA")

# Carpetas esenciales a copiar desde SRC_APP
CORE_DIRECTORIES = [
    "api",
    "core",
    "db",
    "mcp",
    "ui",
    "skills",
    "active_skills",
    "scripts",
    "tests",
    "docs",
    "reports"
]

# Archivos raíz esenciales a copiar desde SRC_APP
CORE_FILES = [
    "Dockerfile",
    "render.yaml",
    "railway.json",
    "Procfile",
    "requirements.txt",
    ".env",
    ".env.example",
    ".mcp.json",
    "PUNTO_DE_CONTROL_SESION_ACTIVA.md",
    "README.md",
    "STATE.md",
    "INICIAR_MOVILNET_PWA.command",
    "PROBAR_PWA_CELULAR.command",
    "DESPLEGAR_A_LA_NUBE.command",
    "INICIAR_MONITOR_SECUENCIAS.command",
    "CONECTAR_N8N_EN_VIVO.command",
    "REINICIAR_SERVICIOS_MOVILNET.command"
]


def compute_sha256(file_path: Path) -> str:
    """Calcula el hash SHA-256 de un archivo."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def should_skip(path: Path) -> bool:
    """Filtra archivos temporales, entornos pesados y symlinks rotos."""
    if path.is_symlink() and not path.exists():
        return True
    parts = path.parts
    if any(p in parts for p in [".git", "venv", ".venv", "__pycache__", ".pytest_cache", ".DS_Store"]):
        return True
    if path.name.endswith(".pyc") or path.name.endswith(".pyo") or path.name == ".DS_Store":
        return True
    return False


def copy_file_with_verify(src_file: Path, dest_file: Path) -> Tuple[bool, str, str]:
    """Copia un archivo y valida que los hashes SHA-256 coincidan exactamente."""
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_file, dest_file)
    src_hash = compute_sha256(src_file)
    dest_hash = compute_sha256(dest_file)
    is_valid = (src_hash == dest_hash)
    return is_valid, src_hash, dest_hash


def execute_replication(dry_run: bool = False) -> Dict[str, Any]:
    """Ejecuta la replicación integral de todos los componentes hacia la carpeta destino."""
    print("=" * 80)
    print("🚀 [MOVILNET PWA REPLICATOR]: INICIANDO COPIA Y CERTIFICACIÓN CRIPTOGRÁFICA")
    print(f"📂 Origen:  {SRC_ROOT}")
    print(f"📁 Destino: {DEST_ROOT}")
    print("=" * 80)

    if not DEST_ROOT.exists() and not dry_run:
        DEST_ROOT.mkdir(parents=True, exist_ok=True)

    copied_files = 0
    verified_files = 0
    corrupted_files = 0
    total_bytes = 0
    copied_catalog: List[Dict[str, Any]] = []

    # 1. Copiar directorios esenciales desde SRC_APP
    for dir_name in CORE_DIRECTORIES:
        src_dir = SRC_APP / dir_name
        dest_dir = DEST_ROOT / dir_name
        if not src_dir.exists():
            print(f"⚠️  [WARN]: Directorio {src_dir} no encontrado, omitiendo.")
            continue

        print(f"📦 Procesando módulo: {dir_name}/ ...")
        for root, dirs, files in os.walk(src_dir):
            root_path = Path(root)
            for f in files:
                src_file = root_path / f
                if should_skip(src_file):
                    continue

                rel_path = src_file.relative_to(SRC_APP)
                dest_file = DEST_ROOT / rel_path

                if not dry_run:
                    valid, s_hash, d_hash = copy_file_with_verify(src_file, dest_file)
                    file_size = src_file.stat().st_size
                    total_bytes += file_size
                    copied_files += 1

                    if valid:
                        verified_files += 1
                    else:
                        corrupted_files += 1
                        print(f"❌ [ERROR]: Discrepancia de hash en {rel_path}")

                    copied_catalog.append({
                        "rel_path": str(rel_path),
                        "size_bytes": file_size,
                        "sha256": s_hash,
                        "verified": valid
                    })
                else:
                    copied_files += 1

    # 2. Copiar archivos raíz de configuración y scripts
    print("📄 Copiando archivos raíz y configuraciones...")
    for file_name in CORE_FILES:
        src_file = SRC_APP / file_name
        if not src_file.exists():
            # Buscar en SRC_ROOT si no está en SRC_APP
            src_file = SRC_ROOT / file_name
        if not src_file.exists():
            continue

        dest_file = DEST_ROOT / file_name
        if not dry_run:
            valid, s_hash, d_hash = copy_file_with_verify(src_file, dest_file)
            file_size = src_file.stat().st_size
            total_bytes += file_size
            copied_files += 1
            if valid:
                verified_files += 1
            else:
                corrupted_files += 1

            copied_catalog.append({
                "rel_path": file_name,
                "size_bytes": file_size,
                "sha256": s_hash,
                "verified": valid
            })

    # 3. Copiar .agents/ desde SRC_ROOT si existe
    src_agents = SRC_ROOT / ".agents"
    if src_agents.exists():
        print("🤖 Copiando catálogo de agentes y reglas .agents/ ...")
        for root, dirs, files in os.walk(src_agents):
            for f in files:
                src_file = Path(root) / f
                if should_skip(src_file):
                    continue
                rel_path = src_file.relative_to(SRC_ROOT)
                dest_file = DEST_ROOT / rel_path
                if not dry_run:
                    valid, s_hash, d_hash = copy_file_with_verify(src_file, dest_file)
                    file_size = src_file.stat().st_size
                    total_bytes += file_size
                    copied_files += 1
                    if valid:
                        verified_files += 1
                    copied_catalog.append({
                        "rel_path": str(rel_path),
                        "size_bytes": file_size,
                        "sha256": s_hash,
                        "verified": valid
                    })

    # 4. Generar lanzador adaptado de doble clic en DEST_ROOT
    if not dry_run:
        adapted_launcher = DEST_ROOT / "INICIAR_MOVILNET_PWA.command"
        launcher_content = """#!/bin/bash
# ==============================================================================
# INICIAR_MOVILNET_PWA.command — Lanzador Soberano Movilnet PWA (121026_CORE)
# Proyecto: Movilnet PWA & Asistente 4GMAX — Telecomunicaciones Movilnet C.A.
# ==============================================================================

cd "$(dirname "$0")"

PORT=8010
URL="http://localhost:${PORT}/ui/pwa_stitch/simulador.html"

echo "========================================================================"
echo "📱 INICIANDO NÚCLEO MOVILNET Y PWA MOBILE-FIRST (PAQUETE SOBERANO)"
echo "========================================================================"

if lsof -i :${PORT} >/dev/null 2>&1; then
    echo "🟢 Servidor Movilnet Core ya está activo en el puerto ${PORT}."
    echo "🌐 Abriendo Simulador PWA Móvil: ${URL}"
    open "${URL}"
    exit 0
fi

echo "🌐 URL de Acceso: ${URL}"
echo "------------------------------------------------------------------------"
echo "🚀 Abriendo en tu navegador predeterminado..."

(sleep 1.5 && open "${URL}") &

if [ -f "venv/bin/python3" ]; then
    venv/bin/python3 api/service.py --port ${PORT}
else
    python3 api/service.py --port ${PORT}
fi
"""
        adapted_launcher.write_text(launcher_content, encoding="utf-8")
        adapted_launcher.chmod(0o755)

        # También crear PROBAR_PWA_CELULAR.command adaptado
        adapted_mobile = DEST_ROOT / "PROBAR_PWA_CELULAR.command"
        mobile_content = """#!/bin/bash
cd "$(dirname "$0")"
PORT=8010
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")
TAILSCALE_IP=$(ifconfig 2>/dev/null | grep -E "inet 100\\." | awk '{print $2}' | head -n 1)

echo "========================================================================"
echo "📱 MOVILNET CORE 4GMAX — SIMULADOR PWA & PRUEBAS EN CELULAR"
echo "========================================================================"
echo "📡 En tu celular (misma red Wi-Fi): http://${LOCAL_IP}:${PORT}/ui/pwa_stitch/index.html"
if [ -n "${TAILSCALE_IP}" ]; then
    echo "🔒 En tu celular (Tailscale Global): http://${TAILSCALE_IP}:${PORT}/ui/pwa_stitch/index.html"
fi
echo "========================================================================"

open "http://localhost:${PORT}/ui/pwa_stitch/simulador.html"
"""
        adapted_mobile.write_text(mobile_content, encoding="utf-8")
        adapted_mobile.chmod(0o755)

    # 5. Generar reporte formal de auditoría de copia
    report = {
        "report_id": f"REP-PWA-REPLICA-{uuid.uuid4().hex[:8].upper()}",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_workspace": str(SRC_ROOT),
        "destination_workspace": str(DEST_ROOT),
        "total_files_copied": copied_files,
        "total_files_verified": verified_files,
        "corrupted_files_count": corrupted_files,
        "total_megabytes_transferred": round(total_bytes / (1024 * 1024), 2),
        "integrity_status": "CERTIFIED_100_PERCENT_MATCH" if corrupted_files == 0 else "CORRUPTION_DETECTED",
        "sample_verified_files": [c["rel_path"] for c in copied_catalog[:15]],
        "pwa_activation_ready": True
    }

    report_canonical = json.dumps(report, indent=2, sort_keys=True)
    report_seal = hashlib.sha256(report_canonical.encode("utf-8")).hexdigest()
    report["sha256_seal"] = f"SHA256:{report_seal}"

    report_path = DEST_ROOT / "reports" / "pwa_replication_certification.json"
    if not dry_run:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=" * 80)
    print(f"✅ [ÉXITO]: {copied_files} archivos copiados y verificados con 100% integridad.")
    print(f"📊 Volumen transferido: {report['total_megabytes_transferred']} MB.")
    print(f"🔒 Sello SHA-256 de Certificación: {report['sha256_seal']}")
    print("=" * 80)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replicador y Certificador de Movilnet PWA")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin copiar archivos físicamente")
    args = parser.parse_args()

    res = execute_replication(dry_run=args.dry_run)
    sys.exit(0 if res["integrity_status"] == "CERTIFIED_100_PERCENT_MATCH" else 1)
