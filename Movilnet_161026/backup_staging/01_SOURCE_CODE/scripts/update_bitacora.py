#!/usr/bin/env python3
"""
Motor Autónomo de Bitácora Continua - Proyecto AI_Movilnet_300926
================================================================
Registra y actualiza automáticamente los capítulos de la bitácora técnica
en cada sesión/chat, garantizando memoria histórica inmutable y trazabilidad.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BITACORA_PATH = PROJECT_ROOT / "docs" / "BITACORA_MOVILNET.md"


def get_project_files_hash() -> str:
    """Calculates SHA-256 checksum over key project files to ensure integrity."""
    hasher = hashlib.sha256()
    for root, _, files in sorted(os.walk(PROJECT_ROOT)):
        for f in sorted(files):
            if f.endswith((".py", ".sql", ".json", ".md")) and "BITACORA" not in f:
                fp = Path(root) / f
                try:
                    hasher.update(fp.read_bytes())
                except Exception:
                    pass
    return hasher.hexdigest()[:16]


def parse_latest_chapter_number(content: str) -> int:
    """Finds the highest chapter number in the existing bitácora."""
    matches = re.findall(r"## Capítulo\s+(\d+):", content)
    if matches:
        return max(map(int, matches))
    return 0


def append_chapter(title: str, prompt_text: str, actions: list[str], modified_files: list[str], next_steps: list[str]) -> int:
    """Appends a new chapter to the bitácora file."""
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    project_hash = get_project_files_hash()

    if not BITACORA_PATH.exists():
        header = f"""# 📖 BITÁCORA MAESTRA DE INGENIERÍA Y OPERACIONES
## Proyecto: Asistente de IA para Telecomunicaciones (Movilnet Venezuela)
**Ubicación:** `{PROJECT_ROOT}`  
**Fecha de Inicialización:** {now}  
**Gobernanza:** Nivel 5 de Autonomía con ACPO & CognitiveForge  

---

```mermaid
timeline
    title Cronología de Capítulos del Proyecto AI_Movilnet_300926
    Capítulo 1 : Concepción y Viabilidad : Análisis de Banco de Agentes y MCP
    Capítulo 2 : Inicialización Estructura : Creación de Carpetas y Documentación Base
```

---

## ÍNDICE DE CAPÍTULOS
"""
        BITACORA_PATH.write_text(header, encoding="utf-8")

    content = BITACORA_PATH.read_text(encoding="utf-8")
    last_num = parse_latest_chapter_number(content)
    new_num = last_num + 1

    actions_md = "\n".join([f"  * {a}" for a in actions]) if actions else "  * Registro de actividad técnica y consolidación."
    files_md = "\n".join([f"  * [`{f}`](file://{PROJECT_ROOT}/{f})" for f in modified_files]) if modified_files else "  * Documentación y estructura base."
    steps_md = "\n".join([f"  * {s}" for s in next_steps]) if next_steps else "  * Continuar con la fase subsiguiente del roadmap."

    chapter_block = f"""
---

## Capítulo {new_num}: {title}
* **Fecha y Hora:** `{now}`
* **Sello de Integridad del Proyecto:** `SHA-256:{project_hash}`
* **Requerimiento / Prompt del Usuario:**
  > "{prompt_text}"

### 🛠️ Acciones y Desarrollos Ejecutados:
{actions_md}

### 📂 Archivos y Componentes Creados o Modificados:
{files_md}

### 🎯 Próximos Pasos Definidos:
{steps_md}
"""

    # Update index if exists
    index_entry = f"* [Capítulo {new_num}: {title}](#capítulo-{new_num}-{title.lower().replace(' ', '-').replace(':', '')})\n"
    if "## ÍNDICE DE CAPÍTULOS" in content and index_entry not in content:
        parts = content.split("## ÍNDICE DE CAPÍTULOS\n", 1)
        content = parts[0] + "## ÍNDICE DE CAPÍTULOS\n" + index_entry + parts[1]

    content += chapter_block
    BITACORA_PATH.write_text(content, encoding="utf-8")
    print(f"✓ Bitácora actualizada: Capítulo {new_num} registrado con éxito en {BITACORA_PATH}")
    return new_num


def main():
    parser = argparse.ArgumentParser(description="Actualizador de Bitácora Continua Movilnet")
    parser.add_argument("--chapter", default="Avance Técnico y Sincronización", help="Título del capítulo")
    parser.add_argument("--prompt", default="", help="Prompt o requerimiento que originó el capítulo")
    parser.add_argument("--actions", nargs="*", default=[], help="Lista de acciones completadas")
    parser.add_argument("--files", nargs="*", default=[], help="Lista de archivos afectados")
    parser.add_argument("--next", nargs="*", default=[], help="Próximos pasos")

    args = parser.parse_args()
    append_chapter(args.chapter, args.prompt, args.actions, args.files, args.next)


if __name__ == "__main__":
    main()
