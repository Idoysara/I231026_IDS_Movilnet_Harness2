#!/usr/bin/env python3
"""
scripts/hook_pre_invocation.py — Hook de Pre-Invocación para Antigravity
======================================================================
Inyecta un recordatorio efímero del Protocolo Decagonal de Calidad
y la regla de Evidencia Dura (ZH-MHEP) antes de cada llamada al modelo.
"""

import sys
import json

def main():
    try:
        # Consumir stdin si existe
        if not sys.stdin.isatty():
            _ = sys.stdin.read()
    except Exception:
        pass

    payload = {
        "injectSteps": [
            {
                "ephemeralMessage": (
                    "🛡️ [PROTOCOLO DECAGONAL Y ZH-MHEP ACTIVO]: "
                    "1. Cero alucinación: valida cada dato contra fuentes duras (DB, JSON de workflows, código). "
                    "2. Intercepción constructiva: no aceptes premisas erróneas del usuario sin verificar telemetría (`lsof`, SQL, grep). "
                    "3. Regla del 100% Pass: todo código modificado debe pasar la suite pytest y los auditores de documentos. "
                    "4. Seguridad de Skills (NVIDIA SkillSpector): todo skill, script o tool se audita contra inyecciones y malware con `scan_skill_security.py`."
                )
            }
        ]
    }
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()

if __name__ == "__main__":
    main()
