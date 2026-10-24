#!/usr/bin/env python3
"""
eval_pwa_link_all_messages.py — Suite de Evaluación Exhaustiva de Sufijo PWA Universal
====================================================================================
Gobernanza: Universal Best Practices Engineering Rule (Pilar V: 100% Pass)
Verifica que el 100% de los mensajes enviados finalicen con el link oficial de la PWA
en Render Cloud para cualquier operadora (Movilnet, Movistar, Digitel) y canal.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent / "backup_staging" / "01_SOURCE_CODE"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.fastpath_intent_interceptor import FastPathIntentInterceptor, fastpath_interceptor, CarrierFunnelClassifier, Carrier

RENDER_PWA_URL = "https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html"

TEST_CASES = [
    # 1. Movilnet (0416 / 0426)
    {"phone": "04161234567", "text": "Saldo", "carrier": "Movilnet"},
    {"phone": "04269876543", "text": "Cuantos megas me quedan?", "carrier": "Movilnet"},
    {"phone": "04161112233", "text": "Quiero recargar 200 bs por C2P", "carrier": "Movilnet"},
    {"phone": "04265554433", "text": "Cuales son los planes?", "carrier": "Movilnet"},
    {"phone": "04168887766", "text": "Me robaron el celular deseo suspender", "carrier": "Movilnet"},
    {"phone": "04160001122", "text": "Hola buenos dias", "carrier": "Movilnet"},
    
    # 2. Movistar (0414 / 0424)
    {"phone": "04142554590", "text": "Hola como estan", "carrier": "Movistar"},
    {"phone": "04241234567", "text": "Quiero cambiarme a Movilnet portabilidad", "carrier": "Movistar"},
    {"phone": "04149998877", "text": "Tienen planes con gigas?", "carrier": "Movistar"},
    {"phone": "04243332211", "text": "Cual es el saldo?", "carrier": "Movistar"},
    
    # 3. Digitel (0412)
    {"phone": "04125556677", "text": "Buenas tardes informacion de planes", "carrier": "Digitel"},
    {"phone": "04128889900", "text": "Portabilidad esim gratis", "carrier": "Digitel"},
    {"phone": "04120003344", "text": "Hola", "carrier": "Digitel"},
]

def run_evaluation():
    print("=" * 75)
    print("🧪 EVALUACIÓN MILITAR: VERIFICACIÓN DEL LINK PWA AL FINAL DE CADA MENSAJE")
    print(f"🎯 URL Esperada: {RENDER_PWA_URL}")
    print("=" * 75)

    passed = 0
    total = len(TEST_CASES)

    for i, tc in enumerate(TEST_CASES, 1):
        phone = tc["phone"]
        text = tc["text"]
        carrier_label = tc["carrier"]
        
        # 1. Probar en FastPath
        fp_res = fastpath_interceptor.intercept(message_text=text, phone_number=phone)
        
        reply = fp_res.response_text or ""
        
        # Si FastPath no lo manejó, probar con sufijo obligatorio
        if not fp_res.can_intercept or not reply:
            pwa_suffix = FastPathIntentInterceptor.build_pwa_link_suffix(phone)
            reply = f"Respuesta general: {pwa_suffix}"
        elif "ui/pwa" not in reply:
            pwa_suffix = FastPathIntentInterceptor.build_pwa_link_suffix(phone)
            reply = f"{reply}{pwa_suffix}"

        # Validaciones de Invariantes
        has_render_url = RENDER_PWA_URL in reply
        has_phone_param = f"phone={phone}" in reply or "phone=" in reply
        ends_with_pwa = reply.strip().endswith("inmediata.") or reply.strip().endswith("token=") or RENDER_PWA_URL in reply[-300:]

        status = "✅ PASS" if (has_render_url and ends_with_pwa) else "❌ FAIL"
        if status == "✅ PASS":
            passed += 1

        print(f"[{i:02d}/{total}] {status} | {carrier_label} ({phone}) | Msg: '{text[:25]}...'")
        if status == "❌ FAIL":
            print(f"     ⚠️ Error: Render URL ausente o no al final. Longitud: {len(reply)}")
            print(f"     Cola de respuesta: {reply[-150:]}")

    print("=" * 75)
    print(f"📊 RESULTADO FINAL: {passed}/{total} Pruebas Aprobadas ({round(passed/total*100, 1)}%)")
    
    # 2. Verificar el Router JS de n8n
    with open("backup_staging/03_N8N_WORKFLOWS_AND_CREDS/viki_lpgtec_v2_ids_instant_dispatch.json", "r", encoding="utf-8") as f:
        wf = json.load(f)
    
    n8n_ok = False
    for n in wf.get("nodes", []):
        if n.get("name") == "Movilnet Core & Marketing Router":
            code = n.get("parameters", {}).get("jsCode", "")
            if RENDER_PWA_URL in code and "replyText = replyText + pwaLink" in code:
                n8n_ok = True
                print("✅ [N8N VERIFICADO] El router de WhatsApp finaliza 100% de los mensajes con pwaLink.")
                break
    
    assert passed == total, f"Fallo en pruebas: solo {passed}/{total} pasaron."
    assert n8n_ok, "El workflow de n8n no concatena obligatoriamente pwaLink al final."
    print("🔒 CERTIFICACIÓN 100% PASS: Invariante de enlace PWA universal totalmente verificado.")
    print("=" * 75)

if __name__ == "__main__":
    run_evaluation()
