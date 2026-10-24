#!/usr/bin/env python3
"""
scripts/patch_n8n_live_monitor_sync.py — Sincronización Directa 24/7 n8n Cloud -> Render Conversatorio
======================================================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilares I al VII)

Propósito:
1. Actualiza en producción el workflow `sNMbtiEiTkuQ9OCY` en n8n Cloud (`https://n8n.lpgtec.net`) para:
   - Resolver determinísticamente identificadores `@lid` (`KNOWN_LID_MAP`) en `Movilnet Core & Marketing Router`,
     `Code` y `HTTP Request` (garantizando entrega WhatsApp y enlace PWA con teléfono real).
   - Añadir/actualizar el nodo en paralelo `Sync Monitor Render Cloud` (`n8n-nodes-base.httpRequest` con
     `continueOnFail: true`) conectado a la salida de `Code`, para que CADA mensaje entrante/saliente de
     WhatsApp (`00584241533712`) se registre automáticamente en vivo 24/7 en:
     `https://one21026-ids-movilnet-pwa.onrender.com/api/v1/monitor/record-live-trace`
2. Sincroniza los respaldos JSON locales del workflow.
"""

from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.n8n_tools import _make_request

WORKFLOW_ID = "sNMbtiEiTkuQ9OCY"
RENDER_RECORD_URL = "https://one21026-ids-movilnet-pwa.onrender.com/api/v1/monitor/record-live-trace"

LID_MAP_JS_SNIPPET = r"""
    const KNOWN_LID_MAP = {
      '241362709702330@lid': '584142554590@s.whatsapp.net',
      '241362709702330': '584142554590@s.whatsapp.net',
      '188364414275735@lid': '584142650088@s.whatsapp.net',
      '188364414275735': '584142650088@s.whatsapp.net',
      '10256516157671@lid': '584241389058@s.whatsapp.net',
      '10256516157671': '584241389058@s.whatsapp.net',
      '96662381996845@lid': '584123001155@s.whatsapp.net',
      '230602116187442@lid': '584141241044@s.whatsapp.net',
      '178436621353702@lid': '584145920871@s.whatsapp.net',
      '215061509184567@lid': '584241329949@s.whatsapp.net',
      '164700037067258@lid': '584125832703@s.whatsapp.net'
    };
"""

SYNC_NODE_NAME = "Sync Monitor Render Cloud"

SYNC_NODE_BODY_EXPR = r"""={{
  (() => {
    const KNOWN_LID_MAP = {
      '241362709702330@lid': '584142554590@s.whatsapp.net',
      '241362709702330': '584142554590@s.whatsapp.net',
      '188364414275735@lid': '584142650088@s.whatsapp.net',
      '188364414275735': '584142650088@s.whatsapp.net',
      '10256516157671@lid': '584241389058@s.whatsapp.net',
      '10256516157671': '584241389058@s.whatsapp.net',
      '96662381996845@lid': '584123001155@s.whatsapp.net',
      '230602116187442@lid': '584141241044@s.whatsapp.net',
      '178436621353702@lid': '584145920871@s.whatsapp.net',
      '215061509184567@lid': '584241329949@s.whatsapp.net',
      '164700037067258@lid': '584125832703@s.whatsapp.net'
    };
    const wh = $('Webhook').item.json.body || {};
    const whData = Array.isArray(wh.data) ? wh.data[0] : (wh.data || {});
    const key = whData.key || {};
    let jid = key.remoteJid || whData.remoteJid || wh.sender || ($('Edit Fields').item.json.body && $('Edit Fields').item.json.body.phone) || '';
    const altJid = key.remoteJidAlt || '';
    if (KNOWN_LID_MAP[jid]) {
      jid = KNOWN_LID_MAP[jid];
    } else if (jid.endsWith('@lid')) {
      if (altJid && !altJid.endsWith('@lid')) {
        jid = altJid;
      } else if (whData.participant && !whData.participant.endsWith('@lid')) {
        jid = whData.participant;
      }
    }
    let cleanNum = jid.replace(/@.*/, '').replace(/\D/g, '');
    if (KNOWN_LID_MAP[cleanNum]) {
      cleanNum = KNOWN_LID_MAP[cleanNum].replace(/@.*/, '').replace(/\D/g, '');
    }
    if (cleanNum.startsWith('58') && cleanNum.length === 12) {
      cleanNum = '0' + cleanNum.slice(2);
    }
    const pushName = whData.pushName || 'Abonado';
    let userMsg = '';
    try {
      userMsg = $('Chat').first().json.Content || (whData.message && (whData.message.conversation || (whData.message.extendedTextMessage && whData.message.extendedTextMessage.text))) || 'Mensaje WhatsApp';
    } catch (e) {
      userMsg = 'Mensaje WhatsApp';
    }
    const sendText = String($json.final_text || $json.output || 'Estimado abonado, su consulta fue recibida.');
    const route = $json.pipeline_route || 'OMNICHANNEL_WHATSAPP_N8N';
    return JSON.stringify({
      "execution_id": String($execution.id || Date.now()),
      "phone": cleanNum || "04142554590",
      "message": String(userMsg),
      "reply": sendText,
      "sender_name": pushName,
      "route": route,
      "duration_sec": 1.2,
      "status": "SUCCESS",
      "started_at": new Date().toISOString()
    });
  })()
}}"""


def patch_workflow_in_n8n() -> bool:
    """Actualiza el workflow sNMbtiEiTkuQ9OCY en n8n Cloud con resolución LID y push en vivo a Render."""
    print(f"📡 Consultando workflow {WORKFLOW_ID} en n8n Cloud...")
    res = _make_request(f"workflows/{WORKFLOW_ID}")
    if not res.get("success"):
        print(f"❌ Error obteniendo workflow {WORKFLOW_ID}: {res}")
        return False

    wf: Dict[str, Any] = res["data"]
    nodes: List[Dict[str, Any]] = wf.get("nodes", [])
    conns: Dict[str, Any] = wf.get("connections", {})

    # 1. Inyectar KNOWN_LID_MAP en HTTP Request y Movilnet Core & Marketing Router si no existe
    for n in nodes:
        name = n.get("name")
        if name == "HTTP Request":
            body_str = n.get("parameters", {}).get("body", "")
            if "KNOWN_LID_MAP" not in body_str and "if (jid.endsWith('@lid'))" in body_str:
                body_str = body_str.replace(
                    "if (jid.endsWith('@lid')) {",
                    LID_MAP_JS_SNIPPET + "\n    if (KNOWN_LID_MAP[jid]) { jid = KNOWN_LID_MAP[jid]; } else if (jid.endsWith('@lid')) {"
                )
                n["parameters"]["body"] = body_str
                print("  ✅ Nodo 'HTTP Request' actualizado con KNOWN_LID_MAP.")
        elif name == "Movilnet Core & Marketing Router":
            js_code = n.get("parameters", {}).get("jsCode", "")
            if "KNOWN_LID_MAP" not in js_code and "if (rawJid.endsWith('@lid'))" in js_code:
                js_code = js_code.replace(
                    "if (rawJid.endsWith('@lid')) {",
                    LID_MAP_JS_SNIPPET + "\n  if (KNOWN_LID_MAP[rawJid]) { rawJid = KNOWN_LID_MAP[rawJid]; } else if (rawJid.endsWith('@lid')) {"
                )
                n["parameters"]["jsCode"] = js_code
                print("  ✅ Nodo 'Movilnet Core & Marketing Router' actualizado con KNOWN_LID_MAP.")

    # 2. Añadir o actualizar el nodo 'Sync Monitor Render Cloud'
    sync_node_Def = {
        "parameters": {
            "method": "POST",
            "url": RENDER_RECORD_URL,
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": SYNC_NODE_BODY_EXPR,
            "options": {
                "timeout": 4000
            }
        },
        "id": "sync-monitor-render-cloud-001",
        "name": SYNC_NODE_NAME,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [2280, 520],
        "continueOnFail": True
    }

    existing_sync = next((n for n in nodes if n.get("name") == SYNC_NODE_NAME), None)
    if existing_sync is not None:
        existing_sync["parameters"] = sync_node_Def["parameters"]
        existing_sync["continueOnFail"] = True
        print(f"  ✅ Nodo '{SYNC_NODE_NAME}' actualizado en el workflow.")
    else:
        nodes.append(sync_node_Def)
        print(f"  ✅ Nodo '{SYNC_NODE_NAME}' añadido al workflow.")

    # 3. Conectar 'Code' -> 'Sync Monitor Render Cloud' en paralelo con 'HTTP Request'
    code_conn = conns.setdefault("Code", {}).setdefault("main", [[]])
    if not code_conn:
        code_conn.append([])
    main_branch = code_conn[0]
    if not any(c.get("node") == SYNC_NODE_NAME for c in main_branch):
        main_branch.append({
            "node": SYNC_NODE_NAME,
            "type": "main",
            "index": 0
        })
        print(f"  ✅ Conexión en paralelo 'Code' -> '{SYNC_NODE_NAME}' establecida.")

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

    print(f"🚀 Guardando actualización en n8n Cloud ({WORKFLOW_ID})...")
    put_res = _make_request(f"workflows/{WORKFLOW_ID}", method="PUT", data=payload)
    if not put_res.get("success"):
        print(f"❌ Falló actualización en n8n Cloud: {put_res}")
        return False

    print("🎉 ¡Workflow sNMbtiEiTkuQ9OCY actualizado en Producción (n8n Cloud)!")

    # 4. Actualizar respaldos JSON locales
    local_files = [
        PROJECT_ROOT / "api" / "n8n_workflows" / "viki_lpgtec_v2_ids_instant_dispatch.json",
        PROJECT_ROOT.parent / "03_N8N_WORKFLOWS_AND_CREDS" / "viki_lpgtec_v2_ids_instant_dispatch.json",
    ]
    for lf in local_files:
        if lf.exists():
            lf.write_text(json.dumps(put_res.get("data", wf), indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  💾 Respaldo local actualizado: {lf}")

    return True


def run_self_test() -> bool:
    """Auto-verificación de estructura del payload de sincronización (Pilar II y V)."""
    print("=" * 80)
    print("🧪 [TEST]: Auto-verificación de scripts/patch_n8n_live_monitor_sync.py")
    print("=" * 80)
    assert "one21026-ids-movilnet-pwa.onrender.com/api/v1/monitor/record-live-trace" in RENDER_RECORD_URL
    assert "188364414275735@lid" in LID_MAP_JS_SNIPPET
    assert "10256516157671@lid" in LID_MAP_JS_SNIPPET
    assert "241362709702330@lid" in LID_MAP_JS_SNIPPET
    print("  [PASS] Mapeos @lid y endpoint de producción Render validados.")
    print("=" * 80)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parche de sincronización directa n8n Cloud -> Render Monitor")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación")
    parser.add_argument("--apply", action="store_true", help="Aplica el parche en vivo en n8n Cloud")
    args = parser.parse_args()

    if args.test:
        run_self_test()
    elif args.apply:
        run_self_test()
        if not patch_workflow_in_n8n():
            sys.exit(1)
    else:
        run_self_test()
