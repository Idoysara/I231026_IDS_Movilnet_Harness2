#!/usr/bin/env python3
"""
Fix HTTP Request body expression in n8n workflow sNMbtiEiTkuQ9OCY
Prevents bash substitution bugs and ensures clean JSON.stringify.
"""
import json
import sys

def main():
    source_file = "/Users/ismael/.gemini/antigravity/brain/f444294f-59ab-4d3d-a8f2-64914e7c683f/.system_generated/steps/5092/output.txt"
    with open(source_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    wf = data["workflow"]
    target_node = None
    for node in wf["nodes"]:
        if node["name"] == "HTTP Request":
            target_node = node
            break

    if not target_node:
        print("ERROR: HTTP Request node not found")
        sys.exit(1)

    # Clean body expression using JSON.stringify
    # Preserves adaptive human cadence (delay) and composing presence
    # Sanitizes number by stripping @s.whatsapp.net / @lid
    body_expr = (
        "={{ JSON.stringify({\n"
        "  \"number\": $('Webhook').item.json.body.data.key.remoteJid.replace(/@.*/, ''),\n"
        "  \"options\": {\n"
        "    \"delay\": ($json.human_delay_ms || 1200),\n"
        "    \"presence\": \"composing\"\n"
        "  },\n"
        "  \"text\": $json.final_text\n"
        "}) }}"
    )

    target_node["parameters"]["body"] = body_expr
    target_node["parameters"]["url"] = (
        "={{ ($('Webhook').item.json.body.server_url || 'http://evolution:8080') }}"
        "/message/sendText/{{ ($('Edit Fields').item.json.body.instance || $('Webhook').item.json.body.instance || 'Viki LPGTEC') }}"
    )
    target_node["parameters"]["headerParameters"] = {
        "parameters": [
            {
                "name": "apikey",
                "value": "={{ $('Webhook').item.json.body.apikey || '957EEABBC570-4C60-8EDB-949655A34113' }}"
            }
        ]
    }

    out_file = "/tmp/fixed_workflow_payload.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2)

    local_file = "/Users/ismael/Desktop/Movilnet_051026/AI_Movilnet_300926-main/api/n8n_workflows/viki_lpgtec_v2_ids_live.json"
    with open(local_file, "r", encoding="utf-8") as f:
        loc_data = json.load(f)
    for n in loc_data.get("nodes", []):
        if n.get("name") == "HTTP Request":
            n["parameters"]["body"] = body_expr
            n["parameters"]["url"] = target_node["parameters"]["url"]
            n["parameters"]["headerParameters"] = target_node["parameters"]["headerParameters"]
    with open(local_file, "w", encoding="utf-8") as f:
        json.dump(loc_data, f, indent=2, ensure_ascii=False)

    print(f"SUCCESS: Saved fixed workflow to {out_file} and {local_file}")
    print(f"Body parameter preview:\n{target_node['parameters']['body']}")

if __name__ == "__main__":
    main()
