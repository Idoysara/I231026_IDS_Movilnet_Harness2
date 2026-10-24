#!/usr/bin/env python3
"""
scripts/patch_n8n_movilnet_workflow.py
Aplica los ajustes de resiliencia y enrutamiento comercial en n8n Cloud para el workflow sNMbtiEiTkuQ9OCY:
1. continueOnFail: True en Google Calendar y Google Drive (evita caídas 500 por credenciales).
2. Desconecta Chat -> Enrutador Servicios Google (evita bifurcación errónea en consultas generales).
3. Añade enrutamiento oficial para oficinas / agencias / Los Palos Grandes en Movilnet Core & Marketing Router.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.n8n_tools import _make_request

def main():
    print("📡 Obteniendo workflow sNMbtiEiTkuQ9OCY desde n8n Cloud...")
    res = _make_request("workflows/sNMbtiEiTkuQ9OCY")
    if not res.get("success"):
        print(f"❌ Error al obtener workflow: {res}")
        sys.exit(1)

    wf = res["data"]
    nodes = wf.get("nodes", [])
    conns = wf.get("connections", {})

    # 1. Ajustar continueOnFail en nodos de Google
    for n in nodes:
        if n.get("name") in ["Google Calendar - Agendar Cita Agencia", "Google Drive - Respaldar Contrato"]:
            n["continueOnFail"] = True
            print(f"  ✅ continueOnFail activado en: {n.get('name')}")

        # 2. Agregar atención oficial de agencias/oficinas en Movilnet Core & Marketing Router
        if n.get("name") == "Movilnet Core & Marketing Router":
            code = n.get("parameters", {}).get("jsCode", "")
            if "Oficinas de Atención Comercial Movilnet 4GMAX" not in code:
                office_block = '''  // CASO: OFICINAS / AGENCIAS / SUCURSALES COMERCIALES
  if (/oficina|agencia|sucursal|tienda|sede|atencion presencial|donde queda|los palos grandes/.test(cleanMsg)) {
    replyText = `🏢 *Oficinas de Atención Comercial Movilnet 4GMAX:*\\n\\n` +
                `📍 *Oficina Los Palos Grandes / Chacao:*\\n` +
                `• Centro Comercial Centro Plaza, Av. Francisco de Miranda, Nivel 4, Los Palos Grandes, Caracas.\\n` +
                `• Horario: Lunes a Viernes de 8:00 AM a 4:00 PM.\\n\\n` +
                `📍 *Sede Principal El Recreo:*\\n` +
                `• Torre Movilnet, Av. Venezuela con Av. Casanova, El Recreo, Sabana Grande.\\n\\n` +
                `📍 *Oficina CCCT (Chuao):*\\n` +
                `• Centro Ciudad Comercial Chacao, Nivel C-1.\\n\\n` +
                `Puedes realizar compras de líneas eSIM, reemplazo de SIM física, cambios de plan y soporte técnico especializado.`;
    item.json.verdict = "ALLOW_VALID_USER_MESSAGE";
    item.json.output = replyText + pwaLink;
    item.json.final_text = replyText + pwaLink;
    item.json.pipeline_route = isCompetitor ? "FUNNEL_MARKETING_PORTABILIDAD" : "FAST_PATH_TELCO_ODA";
    item.json.carrier_phone = cleanDigits;
    continue;
  }

  // CASO 1: CONSULTA DE SALDO'''
                code = code.replace("// CASO 1: CONSULTA DE SALDO", office_block, 1)
                n["parameters"]["jsCode"] = code
                print("  ✅ Bloque de Oficinas Comerciales integrado en Movilnet Core & Marketing Router.")

    # 3. Desconectar Chat -> Enrutador Servicios Google & Notificaciones
    if "Chat" in conns and "main" in conns["Chat"]:
        branches = conns["Chat"]["main"]
        if branches and len(branches[0]) > 1:
            conns["Chat"]["main"] = [[t for t in branches[0] if t.get("node") != "Enrutador Servicios Google & Notificaciones"]]
            print("  ✅ Chat desconectado de Enrutador Servicios Google (resuelto crash paralelo).")

    # 4. Ajustar settings para compatibilidad con esquema API n8n
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

    print("🚀 Enviando actualización a n8n Cloud...")
    put_res = _make_request("workflows/sNMbtiEiTkuQ9OCY", method="PUT", data=payload)
    if put_res.get("success"):
        print("🎉 ¡Workflow sNMbtiEiTkuQ9OCY actualizado exitosamente en n8n Cloud!")
    else:
        print(f"❌ Falló actualización: {put_res}")
        sys.exit(1)

if __name__ == "__main__":
    main()
