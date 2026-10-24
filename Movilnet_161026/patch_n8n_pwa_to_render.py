#!/usr/bin/env python3
"""
scripts/patch_n8n_pwa_to_render.py — Actualizador de Enlace PWA en n8n Cloud hacia Render 24/7
=============================================================================================
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)
Objetivo: Conmutar el enlace PWA que envía WhatsApp desde el túnel temporal de Cloudflare hacia
la URL pública y permanente de Render Cloud: https://one21026-ids-movilnet-pwa.onrender.com
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent / "backup_staging" / "01_SOURCE_CODE"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.n8n_tools import _make_request

OLD_URL = "https://mixture-merchandise-jumping-expenditures.trycloudflare.com"
NEW_URL = "https://one21026-ids-movilnet-pwa.onrender.com"

OLD_TEXT = "*Portal PWA 4GMAX (Datos Móviles 3G/4G/5G):*"
NEW_TEXT = "*Portal PWA 4GMAX (Acceso libre por Wi-Fi o Datos Móviles - Cualquier Operadora):*"

WORKFLOW_ID = "sNMbtiEiTkuQ9OCY"

def patch_local_files():
    base_dir = Path(__file__).resolve().parent
    local_targets = [
        base_dir / "backup_staging" / "01_SOURCE_CODE" / "scripts" / "update_n8n_instant_dispatch.py",
        base_dir / "backup_staging" / "01_SOURCE_CODE" / "api" / "n8n_workflows" / "viki_lpgtec_v2_ids_instant_dispatch.json",
        base_dir / "backup_staging" / "03_N8N_WORKFLOWS_AND_CREDS" / "viki_lpgtec_v2_ids_instant_dispatch.json"
    ]
    
    for target in local_targets:
        if target.exists():
            content = target.read_text(encoding="utf-8")
            changed = False
            if OLD_URL in content:
                content = content.replace(OLD_URL, NEW_URL)
                changed = True
            if OLD_TEXT in content:
                content = content.replace(OLD_TEXT, NEW_TEXT)
                changed = True
            if changed:
                target.write_text(content, encoding="utf-8")
                print(f"✅ Archivo local actualizado: {target.name}")
            else:
                print(f"ℹ️ Archivo ya estaba actualizado: {target.name}")
        else:
            print(f"⚠️ Archivo no encontrado: {target}")

def patch_live_n8n():
    print(f"📡 Obteniendo workflow {WORKFLOW_ID} desde n8n Cloud...")
    res = _make_request(f"workflows/{WORKFLOW_ID}")
    if not res.get("success"):
        print(f"❌ Error al obtener workflow de n8n: {res}")
        sys.exit(1)

    wf = res["data"]
    nodes = wf.get("nodes", [])
    conns = wf.get("connections", {})
    patched = False

    for n in nodes:
        if n.get("name") == "Movilnet Core & Marketing Router":
            code = n.get("parameters", {}).get("jsCode", "")
            if OLD_URL in code or OLD_TEXT in code:
                code = code.replace(OLD_URL, NEW_URL).replace(OLD_TEXT, NEW_TEXT)
                n["parameters"]["jsCode"] = code
                patched = True
                print("  ✅ Nodo 'Movilnet Core & Marketing Router' actualizado con la URL y texto de Render.")
            elif NEW_URL in code and NEW_TEXT in code:
                print("  ℹ️ El nodo ya tenía la URL y texto actualizados.")
                patched = True

    if not patched:
        print("⚠️ No se encontró la cadena OLD_URL en los nodos del workflow.")

    st = wf.get("settings", {})
    clean_settings = {
        "executionOrder": st.get("executionOrder", "v1"),
        "timezone": st.get("timezone", "America/Caracas"),
        "callerPolicy": st.get("callerPolicy", "workflowsFromSameOwner")
    }

    payload = {
        "name": wf.get("name"),
        "nodes": nodes,
        "connections": conns,
        "settings": clean_settings
    }

    print(f"🚀 Enviando actualización a n8n Cloud ({WORKFLOW_ID})...")
    put_res = _make_request(f"workflows/{WORKFLOW_ID}", method="PUT", data=payload)
    if put_res.get("success"):
        print("🎉 ¡Workflow actualizado y guardado exitosamente en n8n Cloud!")
    else:
        print(f"❌ Falló actualización en n8n Cloud: {put_res}")
        sys.exit(1)

    # Verificación final
    verify_res = _make_request(f"workflows/{WORKFLOW_ID}")
    if verify_res.get("success"):
        v_nodes = verify_res["data"].get("nodes", [])
        for n in v_nodes:
            if n.get("name") == "Movilnet Core & Marketing Router":
                v_code = n.get("parameters", {}).get("jsCode", "")
                if NEW_URL in v_code and OLD_URL not in v_code:
                    print(f"🔒 VERIFICACIÓN 100% PASS: El nodo router ahora despacha hacia {NEW_URL}")
                else:
                    print("⚠️ Advertencia: No se pudo verificar la nueva URL en el nodo.")

if __name__ == "__main__":
    patch_local_files()
    patch_live_n8n()
