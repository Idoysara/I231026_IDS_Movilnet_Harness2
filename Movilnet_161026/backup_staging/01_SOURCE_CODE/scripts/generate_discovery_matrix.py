#!/usr/bin/env python3
"""
generate_discovery_matrix.py — Script CLI de Generación del Cuestionario de Levantamiento
============================================================================================
Proyecto: AI_Movilnet_300926 | Alcance: PROYECTO (adaptable a cualquier Telco)
Uso:
    python3 scripts/generate_discovery_matrix.py
    python3 scripts/generate_discovery_matrix.py --client "CANTV Venezuela"
    python3 scripts/generate_discovery_matrix.py --client "Digitel TIM"
"""
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.discovery_tools import generate_discovery_matrix


def main():
    parser = argparse.ArgumentParser(
        description="Genera cuestionario de levantamiento de Fase 0 para cliente Telco"
    )
    parser.add_argument("--client", type=str, default="Movilnet Venezuela",
                        help="Nombre oficial del cliente Telco (default: Movilnet Venezuela)")
    args = parser.parse_args()

    print(f"\n📋 Generando cuestionario de levantamiento para: {args.client}")
    result = generate_discovery_matrix(client_name=args.client)

    if result.get("status") == "GENERATED":
        print(f"  ✅ Cuestionario generado exitosamente")
        print(f"  📁 Archivo: {result['output_file']}")
        print(f"  🏷️  Cliente: {result['client']}")
        print(f"  📐 Dimensiones: {len(result['dimensions'])}")
        print("\n  💡 Próximos pasos:")
        print("     1. Enviar el cuestionario al responsable de TI del cliente.")
        print("     2. Programar sesión de kick-off técnico para revisión conjunta.")
        print("     3. Una vez diligenciado, ejecutar:")
        print("        python3 mcp/discovery_tools.py --test para validar Gatekeeper.")
    else:
        print(f"  ❌ Error: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
