#!/usr/bin/env python3
"""
scripts/generate_backup_manifest.py — Generador de Manifiesto Criptográfico SHA-256 para Respaldo
Proyecto: AI_Movilnet_300926 / Movilnet Core PWA
Gobernanza: Universal Best Practices Engineering Rule (Pilar VI y VII) & Protocolo Decagonal
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

def calculate_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def scan_project(root_dir: Path) -> dict:
    manifest = {
        "project_name": "141026_Movilnet_Core_PWA",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "root_directory": str(root_dir.resolve()),
        "total_files_scanned": 0,
        "total_bytes": 0,
        "directories": {},
        "files": {}
    }

    exclude_dirs = {".git", ".pytest_cache", "__pycache__", "venv"}
    exclude_exts = {".pyc", ".DS_Store"}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Excluir directorios ignorados
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == ".":
            rel_dir = "root"

        dir_files_count = 0
        dir_bytes = 0

        for fname in sorted(filenames):
            if any(fname.endswith(ext) for ext in exclude_exts):
                continue
            fpath = Path(dirpath) / fname
            if fpath.is_symlink():
                continue

            try:
                fsize = fpath.stat().st_size
                fhash = calculate_sha256(fpath)
                rel_path = str(fpath.relative_to(root_dir))

                manifest["files"][rel_path] = {
                    "size_bytes": fsize,
                    "sha256": fhash
                }
                manifest["total_files_scanned"] += 1
                manifest["total_bytes"] += fsize
                dir_files_count += 1
                dir_bytes += fsize
            except Exception as ex:
                print(f"⚠️ Error procesando {fpath}: {ex}", file=sys.stderr)

        manifest["directories"][rel_dir] = {
            "files_count": dir_files_count,
            "total_bytes": dir_bytes
        }

    # Hash maestro del manifiesto
    serialized = json.dumps(manifest["files"], sort_keys=True).encode("utf-8")
    manifest["master_integrity_sha256"] = hashlib.sha256(serialized).hexdigest()
    return manifest

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    print(f"🔍 Escaneando y sellando criptográficamente: {target}")
    mf = scan_project(target)
    out_dir = target / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "MANIFESTO_SHA256_RESPALDO_141026.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(mf, f, indent=2, ensure_ascii=False)
    print(f"✅ Manifiesto generado con éxito: {out_file}")
    print(f"📊 Archivos auditados: {mf['total_files_scanned']}")
    print(f"📦 Tamaño total: {mf['total_bytes'] / (1024*1024):.2f} MB")
    print(f"🔒 Hash Maestro SHA-256: {mf['master_integrity_sha256']}")
