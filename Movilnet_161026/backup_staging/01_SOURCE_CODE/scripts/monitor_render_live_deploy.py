#!/usr/bin/env python3
"""
scripts/monitor_render_live_deploy.py — Monitor Autónomo de Despliegue en Render Cloud
=======================================================================================
Monitorea en tiempo real el despliegue del nuevo release en Render Cloud hasta confirmar
que los nuevos endpoints de Cazador de Ofertas & Club 4GMAX respondan HTTP 200 OK.
"""

import time
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

TARGET_OPENAPI = "https://one21026-ids-movilnet-pwa.onrender.com/openapi.json"
TARGET_CAZADOR = "https://one21026-ids-movilnet-pwa.onrender.com/api/v1/cazador/ofertas?lat=10.4925&lon=-66.8550&max_m=2000"
TARGET_PWA = "https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html"

def check_openapi():
    try:
        req = urllib.request.Request(TARGET_OPENAPI, headers={"User-Agent": "DeployMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.getcode() == 200:
                data = json.loads(resp.read().decode("utf-8"))
                paths = data.get("paths", {})
                cazador_paths = [p for p in paths if "cazador" in p]
                return len(cazador_paths) > 0, len(paths), cazador_paths
    except Exception as e:
        return False, 0, str(e)
    return False, 0, []

def check_cazador_endpoint():
    try:
        req = urllib.request.Request(TARGET_CAZADOR, headers={"User-Agent": "DeployMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.getcode() == 200:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                return True, data
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)
    return False, "UNKNOWN"

def check_pwa_tab():
    try:
        req = urllib.request.Request(TARGET_PWA, headers={"User-Agent": "DeployMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.getcode() == 200:
                html = resp.read().decode("utf-8")
                has_club = "Club 4GMAX" in html or "Cazador" in html or "radar" in html.lower()
                return has_club
    except Exception:
        return False
    return False

def main():
    print("=" * 80)
    print("📡 INICIANDO MONITOREO DE DESPLIEGUE EN RENDER CLOUD (DEP-DBD643QVCJ2C73F1C8E0)")
    print("=" * 80)
    
    max_attempts = 24  # Hasta 6 minutos (24 x 15s)
    attempt = 1
    
    while attempt <= max_attempts:
        now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        print(f"[{now_str}] Intento {attempt}/{max_attempts}: sondeando endpoints en vivo...")
        
        has_cazador_openapi, total_paths, cazador_paths = check_openapi()
        cazador_ok, cazador_info = check_cazador_endpoint()
        has_pwa = check_pwa_tab()
        
        print(f"   • OpenAPI paths: {total_paths} | Rutas Cazador activas: {len(cazador_paths) if isinstance(cazador_paths, list) else 0}")
        print(f"   • Endpoint Radar Cazador: {'ACTIVO (200 OK)' if cazador_ok else cazador_info}")
        print(f"   • PWA Stitch Club 4GMAX: {'PRESENTE' if has_pwa else 'PENDIENTE'}")
        
        if has_cazador_openapi and cazador_ok:
            print("\n" + "=" * 80)
            print("🎉 ¡DESPLIEGUE EN RENDER CONFIRMADO 100% EN VIVO!")
            print("=" * 80)
            print(f"  ✓ OpenAPI rutas Cazador: {cazador_paths}")
            print(f"  ✓ Total rutas expuestas: {total_paths}")
            print(f"  ✓ Radar Cazador: {cazador_info.get('total_comercios_en_rango', 0)} comercios en rango")
            print("=" * 80)
            return 0
            
        print("   ⏳ Compilación en curso en los servidores de Render... esperando 15 segundos.")
        time.sleep(15)
        attempt += 1
        
    print("\n⚠️ Tiempo de espera alcanzado. El despliegue aún podría estar compilando en Render.")
    return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
