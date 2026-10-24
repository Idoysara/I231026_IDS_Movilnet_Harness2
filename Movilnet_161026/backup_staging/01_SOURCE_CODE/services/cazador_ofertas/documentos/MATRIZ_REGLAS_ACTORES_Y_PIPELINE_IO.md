# 🏛️ MATRIZ MAESTRA DE REGLAS DE NEGOCIO, ACTORES Y PIPELINE I/O
## Cazador de Ofertas Movilnet (`Cliente 28 — IDS_CORE v5.85.0`)
**Sellos Criptográficos:** `CERT-CAZADOR-SIMULATOR-TRAFFIC-20261018` | `CERT-CAZADOR-SCRAPER-PROMOS-20261018` | `CERT-CAZADOR-N8N-OMNICHANNEL-20261018` | `CERT-CAZADOR-PENTARCHY-20261018-SHA256`  
**Directiva de Cero Alucinación B2C:** `INVARIANTE-GROUNDING-REAL-B2C-OFERTAS`

---

## 1. REGLAS POR NIVEL Y ACTOR DEL SISTEMA

### A. Reglas Globales (Gobernanza IDS_CORE y Antigravity)
1. **Directiva Suprema de Prioridad 0 (Verificación Empírica Factual):**
   > *"Lo que la terminal no haya confirmado con `exit code 0` y 0 fallos, NO EXISTE ni puede declararse como exitoso."*
   Toda funcionalidad, regla o endpoint cuenta obligatoriamente con suites de pruebas unitarias (`pytest`) con el 100% aprobado.
2. **Zero-Collision & Aislamiento Estricto:**
   Puerto exclusivo `:8030` (FastAPI Core + PWA) y `:3005` (PWA Standalone). Aislamiento total de memoria, bases de datos y puertos respecto a los otros 27 clientes de `IDS_CORE`.
3. **Zero-PII & Privacidad Criptográfica:**
   Prohibido almacenar en texto plano coordenadas GPS crudas históricas de los usuarios. Las coordenadas solo se usan en memoria volátil (<30ms) para calcular distancias esféricas y se destruyen; únicamente se persisten huellas de transacciones criptográficas.
4. **Pureza AST de Dominio:**
   El paquete `src/domain/` debe parsearse con `ast.parse()` con 0 `SyntaxError` y sin dependencias de frameworks web (`FastAPI`, `Flask`) ni drivers de bases de datos.

### B. Reglas del Proyecto (Plataforma Cazador)
1. **Invariante de Cero Alucinación B2C (Zero-Hallucination Grounding Guard):**
   **Queda terminantemente prohibido a cualquier LLM, motor, bot conversacional o API proponer, inventar o alucinar ofertas, precios, descuentos o comercios sintéticos que no residan físicamente en el catálogo auditado.**
   Si en una zona geográfica o categoría no existen ofertas activas, el sistema ejecuta obligatoriamente un **Fallo Limpio (Clean Fail)** informando con total transparencia: *"No hay ofertas registradas en este radio"*, negándose a rellenar con datos ficticios.
2. **Regla de Proximidad de los 3 Anillos:**
   Ninguna oferta fuera de 3,000 metros aparece en el radar:
   $$\text{Anillo}(d) = \begin{cases} 
   \text{Zona 1 (Inmediata)}, & d \le 500\text{m} \\ 
   \text{Zona 2 (Vecindario)}, & 500\text{m} < d \le 1000\text{m} \\ 
   \text{Zona 3 (Urbana)}, & 1000\text{m} < d \le 3000\text{m} 
   \end{cases}$$
3. **Regla de Transparencia de Ahorro:**
   Toda oferta expuesta debe computar y mostrar al usuario: Precio Regular (VES), Precio de Oferta (VES), Ahorro Neto (VES) y Descuento Porcentual real.
4. **Regla de Zero-Rating de Datos:**
   La PWA debe ser accesible sin consumo del cupo de navegación de datos móviles del abonado en la red de Movilnet.
5. **Regla del Deflector de Mensajería:**
   WhatsApp, Telegram y SMS no son tiendas pesadas; emiten un *Magic Link* que abre la PWA nativa a 60 FPS con mapa interactivo Leaflet.

### C. Reglas del Proveedor / Comercio Aliado (B)
1. **Regla de Oro Financiera (Invariante II de David Díaz Robisco):**
   $$\text{Margen Bruto } = \frac{\text{Precio Oferta} - \text{Costo Directo}}{\text{Precio Oferta}} \ge 0.35 \quad (35\%)$$
   *Si el margen es menor al 35%, el motor rechaza la oferta inmediatamente con `DomainInvariantViolationError` para evitar que el comerciante venda a pérdida.*
2. **Regla de Conservación de Stock Físico (Doble Partida):**
   Cada cupón emitido decrementa atómicamente el stock disponible ($\text{Stock}_{t+1} = \text{Stock}_t - 1$). Si $\text{Stock}_t == 0$, la oferta pasa automáticamente a inactiva y desaparece del radar.
3. **Regla de Canje en Caja POS (<0.5 segundos):**
   El comercio valida el cupón con un módulo web liviano sin requerir hardware dedicado. La verificación offline-first evalúa la firma HMAC localmente.
4. **Regla de Split del 80% Neto:**
   El comercio recibe el 80% de los fondos transaccionados a través de la plataforma, liquidables quincenalmente en bolívares.
5. **Regla de RIF Fiscal Verificado:**
   Solo pueden emitir ofertas comercios con RIF formal (`J-`, `V-`, `G-`) registrado en el SENIAT.

### D. Reglas del Usuario / Consumidor (C)
1. **Límite de Acaparamiento:**
   Máximo **3 cupones activos simultáneos** en estado `EMITIDO` por usuario. Si el usuario intenta reclamar un 4to sin canjear los anteriores, el sistema bloquea la emisión.
2. **Caducidad Dinámica TOTP (60 Segundos):**
   El código QR y el token rotan cada 60 segundos ($T_{\text{step}} = \lfloor t_{\text{epoch}} / 60 \rfloor$). Una captura de pantalla vieja queda invalidada.
3. **No Transferibilidad del Cupón:**
   El cupón está sellado criptográficamente para la tupla inmutable $(\text{UUID}, \text{MSISDN\_Usuario}, \text{Comercio\_ID})$. El cajero no puede canjear el cupón si el número presentado no coincide con la línea del titular.
4. **Auto-Liberación de Stock por Vencimiento:**
   Si un cupón en estado `EMITIDO` no es canjeado antes del cierre del día (23:59:59), pasa automáticamente a estado `EXPIRADO` y el stock se restituye al comercio.
5. **Facilidad Carrier Billing:**
   Los usuarios activan el Pase Cazador VIP (95 VES / $1.50) descontado directamente de su saldo prepago o pospago, sin tarjetas bancarias.

### E. Reglas de la Telco (Movilnet 0416 / 0426)
1. **Filtro Exclusivo de MSISDN:**
   Solo se admiten números pertenecientes a Movilnet: $\{0416, 0426, 58416, 58426, +58416, +58426\}$. Operadoras ajenas (Digitel 0412 o Movistar 0414/0424) son rechazadas con error HTTP 422.
2. **Garantía de Idempotencia de Facturación (Anti-Doble Cobro):**
   Toda transacción exige `IdempotencyKey = SHA256(MSISDN + Monto + TimestampVentana)`. Si la red 3G/4G parpadea y el teléfono reintenta, el sistema devuelve el recibo anterior sin debitar saldo dos veces.
3. **Split Transaccional Inviolable (20% Telco):**
   $$\text{Comisión Telco} = \text{Monto Total} \times 0.20 \quad (\text{Movilnet})$$
   $$\text{Neto Comercio/Plataforma} = \text{Monto Total} \times 0.80$$
4. **Opt-In para Alertas SMS de Proximidad:**
   Solo se emiten notificaciones masivas SMPP a usuarios que hayan marcado explícitamente `optin_sms_proximidad = TRUE`.

---

## 2. MATRIZ DE TRANSFORMACIÓN (INPUTS $\longleftrightarrow$ PROCESOS $\longleftrightarrow$ BD $\longleftrightarrow$ OUTPUTS)

| # | Flujo Operativo | Input (Entrada) | Algoritmos y Reglas Intermedias | Mutación en Base de Datos (Persistencia) | Output (Salida al Usuario / Sistema) |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Búsqueda en Radar GPS** | • `lat: float`<br>• `lon: float`<br>• `max_m: 3000`<br>• `categoria: opt` | 1. Bounding-Box Pruning.<br>2. Fórmula esférica de Haversine.<br>3. Clasificación en 3 Anillos (<500m, <1km, <3km).<br>4. **Guarda de Cero Alucinación B2C**: Filtrado exclusivo de ofertas físicas activas con stock > 0. | **Solo Lectura (`SELECT`):**<br>Consulta espacial sobre `comercios` (índice PostGIS GIST) y `JOIN` con `ofertas`. | JSON con 3 anillos estructurados, distancias calculadas en metros y tarjetas de ofertas ordenadas por proximidad. |
| **2** | **Reclamo de Cupón** | • `oferta_id: str`<br>• `msisdn: str` | 1. **Validación Grounding B2C**: Comprobación estricta de existencia en catálogo real.<br>2. Validación de prefijo `0416/0426`.<br>3. Comprobación de stock $>0$.<br>4. Firma HMAC-SHA256 (`CryptoTokenVault`). | **Transacción Atómica (`ACID`):**<br>• `UPDATE ofertas SET stock = stock - 1`<br>• `INSERT INTO cupones` con estado `EMITIDO`. | DTO con `cupon_uuid`, código dinámico legible (`QRO-A1B2...`), firma HMAC y contador de 60 segundos. |
| **3** | **Canje en Terminal POS** | • `cupon_id: str`<br>• `msisdn: str`<br>• `comercio_id: str`<br>• `firma_hmac: str` | 1. Validación de FSM (`EMITIDO` $\to$ `CANJEADO`).<br>2. Tolerancia de reloj $\pm 1$ ventana.<br>3. Verificación Anti-Replay.<br>4. Destrucción inmediata del hash. | **Transacción de Quema:**<br>• `UPDATE cupones SET estado = 'CANJEADO'`<br>• `INSERT INTO boveda_hashes_quemados`. | • **Éxito (200):** Descuento validado en caja.<br>• **Rechazo (409):** Cupón ya quemado o captura de pantalla expirada. |
| **4** | **Carrier Billing (Pase VIP)** | • `msisdn: str`<br>• `monto: 95.0 VES`<br>• `idempotency_key: str` | 1. Verificación de clave de idempotencia previa.<br>2. Token-Bucket de Rate Limiting.<br>3. Split transaccional (20% Telco / 80% Plataforma). | **Libro Mayor Inmutable:**<br>• `INSERT INTO transacciones_billing`<br>• Caché de respuesta en Redis por 24h. | Recibo oficial de cobro, desglose de split (19.00 VES Movilnet / 76.00 VES Plataforma) y activación del Pase VIP. |
| **5** | **Publicación de Ofertas (B2B)** | • `comercio_id: str`<br>• `precio_regular: float`<br>• `precio_oferta: float`<br>• `costo_directo: float` | 1. Validación de precio ($P_{\text{oferta}} < P_{\text{regular}}$).<br>2. Invariante II: $\text{Margen Bruto} \ge 35\%$.<br>3. Asignación de stock inicial auditado. | **Alta en Catálogo:**<br>`INSERT INTO ofertas` con campos `margen_pct` y `stock_disponible`. | Oferta certificada y publicada en el catálogo activo para visualización en el radar. |
| **6** | **Deflexión WhatsApp / SMS Zero-Rating** | • `remitente: str`<br>• `mensaje: str`<br>• `lat/lon: opt` | 1. Normalización de número venezolano a `0416/0426`.<br>2. Grounding Cero Alucinación.<br>3. Cálculo de Magic Link HMAC-SHA256 con vigencia de 24h.<br>4. Inyección cabeceras `X-Movilnet-Zero-Rating`. | **Solo Lectura (`SELECT`):**<br>Consulta a catálogo de ofertas y comercios verificados. | Mensaje enriquecido con enlace 1-Tap a la PWA sin costo de megas. |
| **7** | **Automatización Omnicanal N8N** | • Payload webhook WhatsApp / Telegram / PWA | 1. Normalizador de entrada en Code Node JS.<br>2. Filtro IF Movilnet.<br>3. Invocación Gateway `:8030/api/deflector/n8n`.<br>4. Switch por canal y formateo enriquecido (Inline WebApp Button para Telegram). | **Paso por Gateway Central:**<br>Interconexión HTTP REST con persistencia en el core de datos. | Respuesta multicanal contextual inmediata y redirección fluida a la PWA. |
| **8** | **Extracción Territorial y Pipeline BigQuery DTS** | • Consulta OSM Nominatim / Catálogo físico Caracas | 1. Bounding box Caracas.<br>2. Normalización WGS84 y RIF SENIAT.<br>3. Generación de esquemas duales y CSV para DTS. | **Persistencia Base:**<br>`INSERT / UPSERT INTO comercios` (35 comercios en SQLite y PostGIS). | Archivos `comercios_reales_venezuela.json` y `.csv` listos para ingesta en BigQuery DTS. |
| **9** | **Scraper de Promociones por Áreas de Negocio** | • Scraping web y sondeo de portales venezolanos | 1. Auditoría HTTP 200 en vivo.<br>2. Verificación Invariante II ($\text{Margen} \ge 35\%$).<br>3. Clasificación en 6 áreas comerciales. | **Persistencia de Ofertas:**<br>Carga de 23 promociones auditadas en catálogo físico. | Datasets `promociones_reales_venezuela.json` y `.csv` con 100% de cumplimiento de margen. |
| **10** | **Simulación Masiva y Conciliación Split 20/80** | • 100 abonados Movilnet sintéticos en Caracas | 1. Simulación de 200 búsquedas radar.<br>2. Simulación de 71 reclamos con cuota $\le 3$.<br>3. Simulación de 53 canjes POS (74.65% redención).<br>4. Bloqueo 100% de intentos de doble gasto.<br>5. Split 20% Movilnet / 80% Comercio. | **Persistencia Transaccional Masiva:**<br>• `cupones`: 247 registros.<br>• `transacciones_billing`: 162 registros.<br>• `boveda_hashes_quemados`: 183 registros. | Métricas ejecutivas en `simulacion_trafico_cazador.json` y conciliación en `.csv`. |

