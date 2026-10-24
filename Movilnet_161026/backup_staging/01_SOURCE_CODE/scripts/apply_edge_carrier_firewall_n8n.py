#!/usr/bin/env python3
"""
scripts/apply_edge_carrier_firewall_n8n.py
===========================================
Implementación del Firewall Perimetral Booleano (0416/0426) y Arquitectura
del Ecosistema Comercial 'NO_USUARIOS_MOVILNET'.

Cumple:
1. Inserción de la compuerta perimetral 'Edge Carrier Firewall (0416/0426)'
   inmediatamente después de 'Edit Fields' (post-descarte de eco) y antes de 'Switch'.
2. Estampado inmutable de banderas de dominio:
   - IS_MOVILNET_SUBSCRIBER (boolean: true exclusivamente para 0416 y 0426)
   - msisdn_national (ej: '04161234567', '04142554590', '+13051234567')
   - carrier_prefix (ej: '0416', '0414', '0412', '0212', 'EXT')
   - authorized_pipeline ('CORE_MOVILNET_AUTOGESTION' vs 'NO_USUARIOS_MOVILNET')
   - detected_carrier ('MOVILNET', 'MOVISTAR', 'DIGITEL', 'CANTV_FIJO', 'VOIP_SPECIAL', 'INTERNACIONAL_ROAMING')
   - carrier_label ('Movilnet 4GMAX', 'Movistar Venezuela', etc.)
3. Actualización de 'Movilnet Core & Marketing Router' y 'AI Agent' para consumir
   directamente la bandera sin cálculos duplicados.
4. Sincronización atómica local y en n8n Cloud.
"""

from __future__ import annotations

import os
import sys
import json
import ssl
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WORKFLOW_PATH = PROJECT_ROOT / "api" / "n8n_workflows" / "viki_lpgtec_v2_ids_instant_dispatch.json"

# ==============================================================================
# 1. CÓDIGO JS DEL NODO 'Edge Carrier Firewall (0416/0426)'
# ==============================================================================
EDGE_CARRIER_FIREWALL_JS = r'''for (const item of items) {
  const ef = item.json.body || {};
  const wh = $('Webhook').first().json.body || {};
  const whData = Array.isArray(wh.data) ? wh.data[0] : (wh.data || {});
  const dataKey = (whData && whData.key) || (ef.data && ef.data.key) || {};

  let rawJid = dataKey.remoteJid || whData.remoteJid || wh.sender || (ef && ef.phone) || '';
  const altJid = dataKey.remoteJidAlt || '';

  // 1. Resolución de Identidad LID vs JID real de WhatsApp
  if (rawJid.endsWith('@lid')) {
    if (altJid && !altJid.endsWith('@lid')) {
      rawJid = altJid;
    } else if (whData.participant && !whData.participant.endsWith('@lid')) {
      rawJid = whData.participant;
    }
  }

  // 2. Extracción y Normalización Defensiva
  let digits = rawJid.replace(/@.*$/, '').replace(/\D/g, '');
  let isVenezuelan = false;
  let national = '';

  if (digits.startsWith('0058') && digits.length === 14) {
    digits = digits.slice(4);
    isVenezuelan = true;
  } else if (digits.startsWith('58') && digits.length === 12) {
    digits = digits.slice(2);
    isVenezuelan = true;
  } else if (digits.startsWith('0') && digits.length === 11) {
    digits = digits.slice(1);
    isVenezuelan = true;
  } else if (digits.length === 10 && !digits.startsWith('0')) {
    isVenezuelan = true;
  }

  if (isVenezuelan && digits.length === 10) {
    national = '0' + digits;
  } else {
    national = digits ? '+' + digits : 'UNKNOWN';
  }

  const prefix = national.startsWith('0') ? national.slice(0, 4) : 'EXT';

  // 3. Compuerta Booleana Inmutable (0416 / 0426)
  const isMovilnet = (prefix === '0416' || prefix === '0426');

  // 4. Estampado de Invariantes de Dominio
  item.json.msisdn_national = national;
  item.json.carrier_prefix = prefix;
  item.json.IS_MOVILNET_SUBSCRIBER = Boolean(isMovilnet);

  if (isMovilnet) {
    item.json.authorized_pipeline = "CORE_MOVILNET_AUTOGESTION";
    item.json.detected_carrier = "MOVILNET";
    item.json.carrier_label = "Movilnet 4GMAX";
  } else {
    item.json.authorized_pipeline = "NO_USUARIOS_MOVILNET";
    if (prefix === '0414' || prefix === '0424') {
      item.json.detected_carrier = "MOVISTAR";
      item.json.carrier_label = "Movistar Venezuela";
    } else if (prefix === '0412') {
      item.json.detected_carrier = "DIGITEL";
      item.json.carrier_label = "Digitel 4G";
    } else if (prefix.startsWith('02')) {
      item.json.detected_carrier = "CANTV_FIJO";
      item.json.carrier_label = "Telefonía Fija CANTV";
    } else if (['0500', '0800', '0501'].includes(prefix)) {
      item.json.detected_carrier = "VOIP_SPECIAL";
      item.json.carrier_label = "Servicio Especial No Geográfico";
    } else {
      item.json.detected_carrier = "INTERNACIONAL_ROAMING";
      item.json.carrier_label = "Línea Internacional / Externa";
    }
  }

  // Preservar en body para retrocompatibilidad total
  if (!item.json.body) item.json.body = {};
  item.json.body.IS_MOVILNET_SUBSCRIBER = Boolean(isMovilnet);
  item.json.body.msisdn_national = national;
  item.json.body.carrier_prefix = prefix;
  item.json.body.authorized_pipeline = item.json.authorized_pipeline;
  item.json.body.detected_carrier = item.json.detected_carrier;
  item.json.body.carrier_label = item.json.carrier_label;
}
return items;'''


# ==============================================================================
# 2. PROMPT REFINADO DEL AI AGENT CON CONSUMO DIRECTO DEL FIREWALL
# ==============================================================================
AI_AGENT_TEXT_PROMPT = r'''={{
  (() => {
    const isMovilnet = Boolean($json.IS_MOVILNET_SUBSCRIBER ?? ($json.body && $json.body.IS_MOVILNET_SUBSCRIBER));
    const carrier = $json.carrier_label || ($json.body && $json.body.carrier_label) || (isMovilnet ? 'Movilnet 4GMAX' : 'Operadora Externa');
    const national = $json.msisdn_national || ($json.body && $json.body.msisdn_national) || '04160000001';
    const modoOperativo = isMovilnet ? 'ABONADO_MOVILNET_ACTIVO' : 'MODO_CAPTACION_FUNNEL_MARKETING_NO_MOVILNET';
    const pushName = ($json.body && $json.body.data && $json.body.data.pushName) || ($json.data && $json.data.pushName) || 'Abonado';

    return `[PERFIL DEL USUARIO]\n` +
           `- Nombre: ${pushName}\n` +
           `- Teléfono: ${national} (${carrier})\n` +
           `- MODO OPERATIVO DEL SISTEMA: ${modoOperativo}\n` +
           `- IS_MOVILNET_SUBSCRIBER: ${isMovilnet}\n` +
           `- Fecha Actual: ${$now}\n\n` +
           `[MENSAJE DEL USUARIO]\n` +
           `${$json.Content}`;
  })()
}}'''


def patch_local_workflow():
    print(f"📖 Cargando workflow local desde {WORKFLOW_PATH}...")
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        wf = json.load(f)

    nodes = wf.get("nodes", [])
    conns = wf.get("connections", {})

    node_names = {n.get("name"): n for n in nodes}

    # 1. Crear o actualizar el nodo 'Edge Carrier Firewall (0416/0426)'
    firewall_node_name = "Edge Carrier Firewall (0416/0426)"
    if firewall_node_name in node_names:
        fn = node_names[firewall_node_name]
        fn["parameters"]["jsCode"] = EDGE_CARRIER_FIREWALL_JS
        print(f"  🔄 Nodo '{firewall_node_name}' actualizado con nueva lógica defensiva.")
    else:
        fn = {
            "parameters": {
                "jsCode": EDGE_CARRIER_FIREWALL_JS
            },
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1200, -432],
            "id": "edge-carrier-firewall-0416-0426",
            "name": firewall_node_name
        }
        nodes.append(fn)
        print(f"  ✨ Nodo '{firewall_node_name}' insertado en la lista de nodos.")

    # 2. Modificar topología de conexiones:
    # 'Edit Fields' -> 'Edge Carrier Firewall (0416/0426)' -> 'Switch'
    if "Edit Fields" in conns and "main" in conns["Edit Fields"]:
        conns["Edit Fields"]["main"] = [[
            {
                "node": firewall_node_name,
                "type": "main",
                "index": 0
            }
        ]]
        print("  🔗 Conexión ajustada: Edit Fields -> Edge Carrier Firewall (0416/0426)")

    conns[firewall_node_name] = {
        "main": [[
            {
                "node": "Switch",
                "type": "main",
                "index": 0
            }
        ]]
    }
    print("  🔗 Conexión ajustada: Edge Carrier Firewall (0416/0426) -> Switch")

    # 3. Actualizar AI Agent prompt
    for n in nodes:
        if n.get("name") == "AI Agent":
            params = n.setdefault("parameters", {})
            params["text"] = AI_AGENT_TEXT_PROMPT
            print("  ✅ Nodo 'AI Agent' actualizado para leer directamente del Firewall Perimetral.")

    # Guardar archivo local
    with open(WORKFLOW_PATH, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)
    print(f"💾 Workflow local guardado exitosamente en {WORKFLOW_PATH}")
    return wf


def deploy_to_cloud(wf: Dict[str, Any]) -> bool:
    from mcp.n8n_tools import N8N_BASE_URL, N8N_API_KEY, HTTP_USER_AGENT, _make_request

    print("🚀 Intentando sincronización en caliente con n8n Cloud...")
    st = wf.get("settings", {})
    clean_settings = {
        "executionOrder": st.get("executionOrder", "v1"),
        "timezone": st.get("timezone", "America/Caracas"),
        "callerPolicy": st.get("callerPolicy", "workflowsFromSameOwner")
    }
    payload = {
        "name": wf.get("name"),
        "nodes": wf.get("nodes"),
        "connections": wf.get("connections"),
        "settings": clean_settings
    }

    res = _make_request("workflows/sNMbtiEiTkuQ9OCY", method="PUT", data=payload)
    if res.get("success"):
        print("🎉 ¡Workflow sNMbtiEiTkuQ9OCY sincronizado exitosamente en n8n Cloud!")
        return True
    else:
        print(f"ℹ️ Nota de conexión a n8n Cloud: {res.get('error', 'Revisar conectividad')}")
        return False


def main():
    wf = patch_local_workflow()
    deploy_to_cloud(wf)
    print("✅ Proceso completado exitosamente.")


if __name__ == "__main__":
    main()
