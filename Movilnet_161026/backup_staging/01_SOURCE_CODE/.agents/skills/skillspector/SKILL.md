---
name: skillspector
description: >-
  Auditor de seguridad, detector de malware, troyanos, jailbreaks y virus para AI Agent Skills
  basado en el motor de NVIDIA SkillSpector (Apache-2.0). Analiza SKILL.md, scripts Python (AST),
  comandos bash, vectores de exfiltración y configuraciones MCP produciendo reportes SARIF 2.1.0.
---

# 🛡️ SkillSpector — Auditor de Seguridad y Antimalware para AI Agent Skills (NVIDIA Verified Engine)

Este skill proporciona capacidades de auditoría de seguridad preventiva e inspección estática profunda para cualquier **Agent Skill**, **tool MCP** o **script de automatización** antes de ser adoptado, ejecutado o instalado en el ecosistema Antigravity.

Homologado con las especificaciones de [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) (Release 2.12.0, Apache-2.0).

---

## 🎯 Cuándo Activar Este Skill

Activar inmediatamente cuando:
1. El usuario solicite: *"escanea este skill"*, *"es seguro este script"*, *"revisa si tiene virus o malware"*, *"audita la seguridad de esta herramienta"*.
2. Se descargue o clone un nuevo skill foráneo desde Git, un archivo zip o una URL.
3. Se cree un nuevo skill con `creador-de-skills` o se modifiquen herramientas en `scripts/` o `.agents/skills/`.
4. En la **Fase 1 (Analítica)** o **Fase 5 (Desarrollo)** del Protocolo Decagonal de Calidad.

---

## 🔍 Cobertura de Amenazas (17 Categorías de NVIDIA)

1. **`prompt_injection` (SC1):** Evasión de instrucciones (patrones de ignorar instrucciones previas o bypass de seguridad).
2. **`data_exfiltration` (SC2):** Fuga de credenciales o variables de entorno hacia endpoints remotos no autorizados.
3. **`privilege_escalation` (SC3):** Comandos privilegiados no autorizados, alteración de permisos o escape de sandboxes.
4. **`supply_chain` (SC4):** Dependencias maliciosas y cotejo con [OSV.dev](https://osv.dev).
5. **`excessive_agency` (SC5):** Comandos destructivos sin límites (borrado masivo en raíz del sistema, sobreescritura de permisos raíz, fork bombs).
6. **`output_handling` (SC6):** Ejecución ciega de salidas de modelos (`eval(output)`).
7. **`system_prompt_leakage` (SC7):** Técnicas de extracción de instrucciones confidenciales.
8. **`memory_poisoning` (SC8):** Alteración maliciosa de contexto persistente o scratchpads.
9. **`tool_misuse` (SC9):** Coerción de argumentos en herramientas MCP.
10. **`rogue_agent` (SC10):** Generación no acotada de subagentes recursivos.
11. **`anti_refusal` (SC11):** Jailbreaks y bypass tipo DAN ("Do Anything Now").
12. **`trigger_abuse` (SC12):** Palabras clave ocultas en markdown para secuestrar intenciones.
13. **`dangerous_code_ast` (SC13):** AST Python: llamadas a `eval()`, `exec()`, `subprocess(shell=True)`, `os.system()`.
14. **`taint_tracking` (SC14):** Rastreo de datos no confiables hacia sumideros de ejecución.
15. **`yara_signatures` (SC15):** Firmas de malware binario y scripts droppers.
16. **`mcp_least_privilege` (SC16):** Herramientas MCP con privilegios excesivos no justificados.
17. **`mcp_tool_poisoning` (SC17):** Manipulación maliciosa de descripciones de herramientas MCP.

---

## 🛠️ Modos de Ejecución Disponibles

### Modo 1: Motor Local Soberano (Recomendado — Zero Tokens, <15ms)
Ejecutar el script nativo certificado:
```bash
# Escaneo de un skill específico
python scripts/scan_skill_security.py --scan path/to/skill

# Escaneo con salida SARIF 2.1.0 para CI/CD
python scripts/scan_skill_security.py --scan path/to/skill --format sarif

# Auto-verificación matemática formal (100% Pass)
python scripts/scan_skill_security.py --test
```

### Modo 2: Servidor MCP Nativo (`skillspector_mcp`)
Invocar la herramienta MCP registrada en `.agents/mcp_config.json`:
- **Herramienta:** `mcp_skillspector_scan`
- **Argumentos:** `{"target_path": "path/to/skill", "format": "json"}`

### Modo 3: Contenedor Docker Oficial de NVIDIA
Para entornos aislados sin dependencias de Python locales:
```bash
docker run --rm -v "$PWD:/scan" skillspector scan /scan/my-skill/ --no-llm
```

---

## ⚖️ Umbrales de Riesgo y Recomendaciones

- **Puntuación 0.0 - 19.9:** `SAFE` ✅ (Skill limpio, aprobado para producción).
- **Puntuación 20.0 - 49.9:** `CAUTION` ⚠️ (Advertencias de severidad Media/Baja; requiere revisión).
- **Puntuación 50.0 - 100.0 o cualquier hallazgo `CRITICAL`:** `DO_NOT_INSTALL` ❌ (Rechazado automáticamente).
