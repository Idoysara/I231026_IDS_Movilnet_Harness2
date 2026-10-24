import re
from pathlib import Path

docs_dir = Path("docs")
bitacora_path = docs_dir / "BITACORA_MOVILNET.md"
full_book_path = docs_dir / "LIBRO_MAESTRO_BITACORA_Y_DOCUMENTOS.md"

canonical_mapping = {
    1: ['CONVERSACION_INICIAL.md'],
    2: ['REQUERIMIENTOS_ASISTENTE_TELCO.md'],
    5: ['FASE_0_LEVANTAMIENTO_INFORMACION.md'],
    6: ['CUESTIONARIO_LEVANTAMIENTO_MOVILNET_VENEZUELA_2026-09-30.md'],
    7: [
        'CUESTIONARIO_LEVANTAMIENTO_INTEGRATIONTEST_TELCO_2026-09-30.md', 
        'CUESTIONARIO_LEVANTAMIENTO_TESTCO_TELCO_2026-09-30.md',
        'CUESTIONARIO_LEVANTAMIENTO_INTEGRATIONTEST_TELCO_2026-10-01.md', 
        'CUESTIONARIO_LEVANTAMIENTO_TESTCO_TELCO_2026-10-01.md'
    ],
    12: ['DIAGRAMA_OPERATIVO_Y_FLUJO_COMPLETO.md'],
    13: ['ESTRATEGIA_MODELOS_IA_MVP_Y_ONPREMISE.md'],
    14: ['MANIFIESTO_APLICACION_COGNITIVA_HUMANA.md'],
    18: ['ARQUITECTURA_TECNICA.md'],
    19: ['EXPERIENCIA_USUARIO_JOURNEY_MOVILNET.md'],
    20: ['TRANSACCIONES_PAGOS_EN_CHAT_C2P.md'],
    21: ['ARQUITECTURA_SUPERAPP_VAS_MOVILNET.md'],
    24: ['SERVICIOS_COMERCIALES_MOVILNET_CATALOGO.md'],
    25: ['INVESTIGACION_ATENCION_DIGITAL_MOVILNET_VS_NUEVO_SISTEMA.md'],
    26: ['BATERIA_TECNOLOGICA_Y_BENCHMARK_COMPETENCIA.md'],
    27: ['DOCUMENTO_APROBACION_FASE0_EJECUTIVO.md'],
    32: ['INVESTIGACION_N8N_MCP_SKILL_ANTIGRAVITY.md'],
    34: ['EXPLICACION_FLUJO_N8N_ANTIGRAVITY.md'],
    35: ['EVALUACION_SKILLS_SH_ECOSISTEMA.md'],
    48: ['MODELO_CONCEPTUAL_FASE_1_DATOS.md'],
    49: ['DICCIONARIO_DATOS_TABLAS_POSTGRESQL.md'],
    50: ['INTEGRACION_N8N_BASE_DE_DATOS_MOVILNET.md'],
    52: ['FASE_1_ARQUITECTURA_DATOS_Y_PERSISTENCIA.md', 'MATRIZ_TABLAS_BASES_DATOS_Y_ARQUITECTURA_FASE1.md'],
    53: ['HANDOVER_CONTINUIDAD_FASE_1.md'],
    55: ['FASE_2_API_REST_SPECIFICATION.md', 'DOSSIER_EJECUTIVO_FASE2_PASO1_API_REST.md'],
    56: ['FASE_2_PASO2_N8N_WORKFLOWS_Y_DESPLIEGUE.md'],
    57: ['FASE_2_PASO3_INTEGRACION_WEBHOOKS_MCP.md'],
    58: ['FASE_2_PASO4_GATEKEEPER2_CERTIFICACION.md', 'FASE_2_DOCUMENTO_E_INFORME_DETALLADO_COMPLETO.md'],
    59: ['FASE_3_PASO1_AGENTE_CUSTOMER_CARE_OCS.md'],
    60: ['FASE_3_PASO2_PASARELA_FINANCIERA_C2P.md'],
    61: ['FASE_3_PASO3_GESTION_EMERGENCIAS_EIR.md'],
    62: ['FASE_3_PASO4_RETENCION_CHURN_ML.md'],
    63: ['FASE_3_PASO5_GATEKEEPER3_CERTIFICACION.md', 'FASE_3_DOCUMENTO_E_INFORME_DETALLADO_COMPLETO.md'],
    64: ['FASE_4_PASO1_SISTEMA_DISENO_UI_UX_AX.md'],
    67: ['RECORDATORIO_CONTINUACION_FASE4.md'],
}

content = bitacora_path.read_text(encoding='utf-8')
pattern = r'(?m)^(## (?:📌 |🏛️ |📘 )?CAP[ÍI]TULO \d+.*|## Capítulo \d+.*)'
splits = re.split(pattern, content)

compiled_text = []
# Preámbulo (Portada, índices y tablas iniciales de la bitácora)
compiled_text.append(splits[0].strip())

total_included_docs = 0

for i in range(1, len(splits), 2):
    header = splits[i].strip()
    body = splits[i+1].strip()
    
    m = re.search(r'CAP[ÍI]TULO\s+(\d+)|Capítulo\s+(\d+)', header, re.IGNORECASE)
    cap_num = int(m.group(1) or m.group(2)) if m else None
    
    compiled_text.append("\n\n---\n\n" + header + "\n\n" + body)
    
    if cap_num and cap_num in canonical_mapping:
        for doc_name in canonical_mapping[cap_num]:
            doc_file = docs_dir / doc_name
            if doc_file.exists():
                doc_content = doc_file.read_text(encoding='utf-8').strip()
                compiled_text.append(f"\n\n### 📑 DOCUMENTO ASOCIADO AL CAPÍTULO {cap_num}: `{doc_name}`\n\n> **Origen:** `docs/{doc_name}` | **Inclusión Completa Oficial**\n\n" + doc_content)
                total_included_docs += 1
            else:
                print(f"ADVERTENCIA: No se encontró {doc_file}")

full_content = "\n".join(compiled_text)
full_book_path.write_text(full_content, encoding='utf-8')

print(f"Libro Maestro compilado exitosamente:")
print(f"  Ruta: {full_book_path}")
print(f"  Líneas: {len(full_content.splitlines())}")
print(f"  Tamaño: {len(full_content.encode('utf-8')) / 1024:.1f} KB")
print(f"  Documentos .md incrustados en su totalidad: {total_included_docs}")
