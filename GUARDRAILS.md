# 🛡️ GUARDRAILS & INVARIANTES DE OPERACIÓN — IDS_MOVILNET

Este documento establece las reglas invariantes no negociables de operación para el proyecto **IDS_Movilnet**, gobernado bajo la metodología **Google Harness²** ([arXiv:2610.14224](https://arxiv.org/abs/2610.14224)) y la directiva de excelencia técnica militar.

---

## 1. INVARIANTES CRÍTICOS DEL SISTEMA

### Invariante I: Elisión de Contexto Basada en Reglas (<2,000 Caracteres)
Toda salida de terminal, log de compilación, respuesta de OCR/STT o traza de pytest que supere los **2,000 caracteres** debe ser truncada mediante elisión controlada:
- Preservar los primeros **500 caracteres** (cabecera del comando y contexto).
- Insertar marcador: `... [N caracteres elididos por regla Harness²] ...`.
- Preservar los últimos **1,500 caracteres** (stack trace, causas de fallos y aserciones finales).
- **Prohibición**: Queda vetado volcar salidas crudas masivas que saturen la ventana de tokens del agente.

### Invariante II: Protocolo de Lectura por Lotes (Chunking Estricto)
- Ningún ciclo de lectura podrá exceder **15 archivos** o **600 líneas** por lote.
- Todo análisis exhaustivo de los 591 archivos Python del monorepo debe procesarse mediante iteración granular y mapeos estructurados.

### Invariante III: Pureza Sintáctica AST en Scripts Generados
- Todo script de Python generado o modificado por Harness² o sus subagentes debe pasar por validación de árbol de sintaxis abstracta (`ast.parse()`) antes de su ejecución.
- Si un script presenta un solo `SyntaxError`, la propuesta queda automáticamente invalidada y se activa el protocolo de reintento.

### Invariante IV: Aislamiento de Puertos de Telecomunicaciones y Servicios
- Cumplimiento estricto de la directiva `agy-port-guardian`.
- Puertos dedicados:
  - Servidor FastAPI Multimodal: `:8000` / `:8008`
  - Portal PWA / Móvil: `:3000` / `:5173`
  - Webhooks WhatsApp / N8N: `:5678` / `:8080`
- **Prohibición**: Queda estrictamente prohibido terminar procesos o colisionar con puertos asignados a otros proyectos (`IDS_CORE`, `DSSGPS`).

### Invariante V: Soberanía de Datos y Privacidad Zero-PII
- **Comprobantes y Vouchers Bancarios**: Las imágenes de pagos procesadas en `MODULO_DESPACHO_MULTIMODAL` deben ser analizadas en memoria RAM volátil (<30ms) y destruidas inmediatamente.
- **Telco Data**: Queda vetado almacenar o exponer en texto plano números telefónicos no enmascarados, tokens de API de WhatsApp, secretos de N8N o datos de suscriptores de `local_movilnet.db`.
- Los vectores y metadatos resultantes solo pueden fluir hacia las bóvedas encriptadas correspondientes.

### Invariante VI: Atribución Causal No Negociable
Toda mutación o ajuste a componentes debe recibir un veredicto empírico observable:
1. `helped`: El cambio mitigó directamente el fallo o aceleró la suite de tests.
2. `hurt`: El cambio introdujo una regresión.
3. `no observed effect`: El comportamiento permaneció inalterado.
4. `confounded`: Múltiples factores cambiaron simultáneamente sin aislar la causa raíz.
