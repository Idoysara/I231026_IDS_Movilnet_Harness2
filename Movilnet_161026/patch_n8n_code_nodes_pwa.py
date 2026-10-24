#!/usr/bin/env python3
"""
scripts/patch_n8n_code_nodes_pwa.py — Inyector Inviolable de Enlace PWA en los Nodos Egress de n8n
===================================================================================================
Gobernanza: Universal Best Practices Engineering Rule & Regla Inviolable de Enlace PWA Universal
Garantiza que el nodo final 'Code' (por donde pasa TODO mensaje de AI Agent, Gemini y Fallback)
y el nodo 'Code1' inyecten OBLIGATORIAMENTE el enlace al Portal PWA en Render Cloud antes de enviar
a WhatsApp.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent / "backup_staging" / "01_SOURCE_CODE"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.n8n_tools import _make_request

WORKFLOW_ID = "sNMbtiEiTkuQ9OCY"
RENDER_URL = "https://one21026-ids-movilnet-pwa.onrender.com"

PWA_INJECTION_SNIPPET = r'''
    // REGLA INVIOLABLE: Garantizar enlace PWA al final de TODO mensaje saliente (Wi-Fi o Datos Móviles)
    if (!cleanText.includes("one21026-ids-movilnet-pwa.onrender.com") && !cleanText.includes("/ui/pwa")) {
        let cleanDigits = "04160000001";
        try {
            const ef = $('Edit Fields').first().json.body || {};
            const wh = $('Webhook').first().json.body || {};
            const whData = Array.isArray(wh.data) ? wh.data[0] : (wh.data || {});
            const dataKey = (whData && whData.key) || (ef.data && ef.data.key) || {};
            let rawJid = dataKey.remoteJid || whData.remoteJid || wh.sender || (ef && ef.phone) || item.json.carrier_phone || '';
            const digits = rawJid.replace(/@.*$/, '').replace(/[^\d]/g, '');
            if (digits) cleanDigits = digits;
        } catch(e) {}

        const prefix = cleanDigits.slice(0, 4);
        const isCompetitor = !(prefix === '0416' || prefix === '0426');
        const pwaCarrierSlug = isCompetitor ? ((prefix === '0414' || prefix === '0424') ? 'movistar' : 'digitel') : 'movilnet';
        const tokenSuffix = cleanDigits.length >= 8 ? cleanDigits.slice(-8) : '4gmaxvip';

        const pwaLink = `\n\n🌐 *Portal PWA 4GMAX (Acceso libre por Wi-Fi o Datos Móviles — Cualquier Operadora):*\n👉 https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html?carrier=${pwaCarrierSlug}&phone=${cleanDigits}&token=${tokenSuffix}4gmax`;
        cleanText = cleanText + pwaLink;
    }
'''

def update_workflow():
    print(f"📡 Obteniendo workflow {WORKFLOW_ID} desde n8n Cloud...")
    res = _make_request(f"workflows/{WORKFLOW_ID}")
    if not res.get("success"):
        print(f"❌ Error al obtener workflow de n8n: {res}")
        sys.exit(1)

    wf = res["data"]
    nodes = wf.get("nodes", [])
    conns = wf.get("connections", {})

    patched_nodes = []

    for n in nodes:
        name = n.get("name")
        if name == "Code":
            code = n.get("parameters", {}).get("jsCode", "")
            if "REGLA INVIOLABLE: Garantizar enlace PWA" not in code:
                # Inyectar justo antes de: item.json.final_text = cleanText;
                target_str = "item.json.final_text = cleanText;"
                if target_str in code:
                    code = code.replace(target_str, f"{PWA_INJECTION_SNIPPET}\n    {target_str}")
                    n["parameters"]["jsCode"] = code
                    patched_nodes.append(name)
                    print("  ✅ Nodo 'Code' parcheado con inyección obligatoria de PWA.")
                else:
                    print(f"  ⚠️ No se encontró target_str en nodo {name}")
            else:
                print("  ℹ️ Nodo 'Code' ya tenía la inyección PWA.")

        elif name == "Code1":
            code = n.get("parameters", {}).get("jsCode", "")
            if "REGLA INVIOLABLE: Garantizar enlace PWA" not in code:
                target_str = "item.json.final_text = cleanText;"
                if target_str in code:
                    code = code.replace(target_str, f"{PWA_INJECTION_SNIPPET}\n     {target_str}")
                    n["parameters"]["jsCode"] = code
                    patched_nodes.append(name)
                    print("  ✅ Nodo 'Code1' parcheado con inyección obligatoria de PWA.")
                else:
                    print(f"  ⚠️ No se encontró target_str en nodo {name}")
            else:
                print("  ℹ️ Nodo 'Code1' ya tenía la inyección PWA.")

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
        print("🎉 ¡Workflow de Producción actualizado exitosamente en n8n Cloud!")
    else:
        print(f"❌ Falló actualización en n8n Cloud: {put_res}")
        sys.exit(1)

    # Actualizar copias locales
    base_dir = Path(__file__).resolve().parent
    local_files = [
        base_dir / "backup_staging" / "03_N8N_WORKFLOWS_AND_CREDS" / "viki_lpgtec_v2_ids_instant_dispatch.json",
        base_dir / "backup_staging" / "01_SOURCE_CODE" / "api" / "n8n_workflows" / "viki_lpgtec_v2_ids_instant_dispatch.json"
    ]
    for lf in local_files:
        if lf.exists():
            with open(lf, "w", encoding="utf-8") as f:
                json.dump(wf, f, indent=2, ensure_ascii=False)
            print(f"✅ Archivo local sincronizado: {lf.name}")

    # Verificación estricta de la nube
    v_res = _make_request(f"workflows/{WORKFLOW_ID}")
    if v_res.get("success"):
        v_wf = v_res["data"]
        for n in v_wf.get("nodes", []):
            if n.get("name") == "Code":
                js = n.get("parameters", {}).get("jsCode", "")
                assert "REGLA INVIOLABLE: Garantizar enlace PWA" in js, "Fallo: 'Code' no tiene el snippet PWA"
                assert "one21026-ids-movilnet-pwa.onrender.com" in js, "Fallo: URL Render ausente en 'Code'"
                print("🔒 VERIFICACIÓN 100% PASS: Nodo 'Code' de producción certificado con enlace PWA inviolable.")

if __name__ == "__main__":
    update_workflow()
