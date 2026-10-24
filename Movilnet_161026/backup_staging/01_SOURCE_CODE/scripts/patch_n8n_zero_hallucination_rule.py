#!/usr/bin/env python3
"""
scripts/patch_n8n_zero_hallucination_rule.py
Integra la Regla Inviolable de Cero Adivinación y Detección de Datos Faltantes
en el nodo 'AI Agent' del workflow canónico sNMbtiEiTkuQ9OCY en n8n Cloud.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.n8n_tools import _make_request

def patch_n8n():
    print("📡 Obteniendo workflow sNMbtiEiTkuQ9OCY desde n8n Cloud...")
    res = _make_request("workflows/sNMbtiEiTkuQ9OCY")
    if not res.get("success"):
        print(f"❌ Error al obtener workflow: {res}")
        return False

    wf = res["data"]
    nodes = wf.get("nodes", [])

    rule_text = """
8. REGLA INVIOLABLE DE CERO ADIVINACIÓN Y DATOS FALTANTES:
   - NUNCA adivines ni alucines información que el usuario no haya suministrado.
   - Si el usuario pide sugerencias de productos o recomendaciones de lugares (restaurantes, farmacias, automercados, clínicas, etc.) y NO indica en qué ciudad o zona se encuentra, QUEDA ESTRICTAMENTE PROHIBIDO asumir que está en Caracas o en cualquier otra ciudad.
   - En su lugar, solicita amablemente, de forma muy breve y cordial su ubicación o datos faltantes: "¿En qué ciudad o zona te encuentras para recomendarte las mejores opciones cercanas?".
   - Una vez que responda, usa las herramientas y la información verificada para responder de forma concisa, respetuosa y amigable, ahorrando tokens al máximo."""

    updated = False
    for n in nodes:
        if n.get("name") == "AI Agent":
            opts = n.setdefault("parameters", {}).setdefault("options", {})
            sys_msg = opts.get("systemMessage", "")
            if "REGLA INVIOLABLE DE CERO ADIVINACIÓN Y DATOS FALTANTES" not in sys_msg:
                opts["systemMessage"] = sys_msg.strip() + "\n" + rule_text
                updated = True
                print("  ✅ Regla de Cero Adivinación y Datos Faltantes inyectada en 'AI Agent'.")
            else:
                print("  ℹ️ La regla ya estaba presente en 'AI Agent'.")

    if not updated:
        print("  ℹ️ No se requirieron cambios en los nodos.")
        return True

    # Preparar payload limpio
    st = wf.get("settings", {})
    clean_settings = {
        "executionOrder": st.get("executionOrder", "v1"),
        "timezone": st.get("timezone", "America/Caracas"),
        "callerPolicy": st.get("callerPolicy", "workflowsFromSameOwner")
    }

    payload = {
        "name": wf.get("name"),
        "nodes": nodes,
        "connections": wf.get("connections", {}),
        "settings": clean_settings
    }

    print("🚀 Desplegando actualización hacia n8n Cloud...")
    put_res = _make_request("workflows/sNMbtiEiTkuQ9OCY", method="PUT", data=payload)
    if put_res.get("success"):
        print("🎉 ¡Workflow sNMbtiEiTkuQ9OCY actualizado con éxito en n8n Cloud!")
        return True
    else:
        print(f"❌ Error al actualizar workflow en n8n Cloud: {put_res}")
        return False

if __name__ == "__main__":
    success = patch_n8n()
    sys.exit(0 if success else 1)
