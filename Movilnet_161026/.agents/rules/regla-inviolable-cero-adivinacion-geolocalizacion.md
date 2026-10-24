# 🛡️ REGLA INVIOLABLE: CERO ADIVINACIÓN DE GEOLOCALIZACIÓN Y PRECISIÓN SUB-5 METROS (<5m)

## 1. Principio Fundamental y Objetivo Soberano (/goal)
Esta directiva gobierna de forma obligatoria e incondicional **todo componente, modelo cognitivo de IA (Gemini/OpenRouter), pipeline FastPath, interceptor de webhooks y despachador de emergencias (911/SOS)** en el ecosistema Movilnet Core / PWA 4GMAX.

> **MANDATO INVIOLABLE:**
> **QUEDA TERMINANTEMENTE PROHIBIDO ADIVINAR, ALUCINAR O ASUMIR UBICACIONES GEOGRÁFICAS.**
> En cualquier situación —sea una emergencia crítica, una consulta de servicios, información, curiosidad o una conversación general— la geolocalización debe determinarse **SIEMPRE Y SIN EXCEPCIÓN** mediante los algoritmos geocadastrales y bases de datos espaciales con coordenadas WGS84 (`lat`, `lon`, `accuracy_meters`). El margen de error no puede superar los **5 metros**.

---

## 2. Invariante I — Resolución Determinista Catastral Sub-5m (`CadastralReverseGeocoder`)
1. **Prioridad Poligonal Urbana:** Toda coordenada WGS84 dentro del territorio nacional debe ser resuelta mediante el motor `core/cadastral_reverse_geocoder.py`.
2. **Jerarquía Espacial:**
   - **Micro-Sectores Urbanos:** Las cuadrículas y polígonos de micro-sectores (ejemplo: Los Palos Grandes vs Altamira en Chacao) tienen prioridad matemática absoluta sobre nombres genéricos de municipios o ciudades.
   - **Open Location Code (Plus Codes 11D):** Para cada punto geográfico se debe computar un Plus Code de 11 caracteres (ejemplo: `772MG524+RMH`), garantizando una cuadrícula de rescate de $\approx 3.5\text{ m} \times 2.8\text{ m}$.
   - **Caché Persistente SQLite WAL (`geo_reverse_cache`):** Indexación a 5 decimales ($\approx 1.1\text{ metros}$) para resolución en $<2\text{ ms}$ sin dependencias externas de red.
3. **Prohibición de Cruzar Sectores Vecinos:** Si las coordenadas corresponden a Los Palos Grandes, el sistema tiene estrictamente prohibido reportar Altamira o Plaza Francia, y viceversa.

---

## 3. Invariante II — Grounding Inmutable para Modelos Cognitivos LLM
1. **Inyección Obligatoria de Telemetría:** Cuando una interacción deba ser procesada por un modelo de lenguaje (Gemini / OpenRouter / Fallback Semántico), el prompt de sistema debe recibir obligatoriamente el bloque:
   ```text
   [GROUNDING_GEOESPACIAL_DETERMINISTA - CERO ALUCINACIÓN]:
   - Coordenadas WGS84: {lat}, {lon} (Precisión: ±{accuracy} m)
   - Plus Code (11D): {plus_code_11d}
   - Dirección Catastral Oficial: {display_address}
   - Sector / Urbanización: {urbanization}
   - Municipio / Parroquia / Estado: {municipality}, {parish}, {state}
   - Puntos de Referencia: {nearest_landmarks}
   - Enlace Google Maps: {google_maps_url}
   - Enlace Waze Paramédicos: {waze_url}
   ```
2. **Prohibición de Inventar ante Datos Faltantes:** Si el usuario pregunta por recomendaciones cercanas o servicios y **NO ha enviado coordenadas GPS**, el modelo tiene prohibido asumir Caracas o cualquier otra ciudad; debe solicitar amablemente y con cortesía su ciudad o zona.

---

## 4. Invariante III — Despacho de Emergencia y Rescate Paramédico 911
1. **Referencia Hablada Certificada (`spoken_emergency_reference`):** Todo despacho de emergencia 911 o SOS satelital generado por WhatsApp o PWA debe suministrar al usuario la frase textual exacta que debe transmitir a los paramédicos y cuerpos de seguridad.
2. **Navegación Dual para Unidades de Rescate:** Generación automática de coordenadas fijadas en Google Maps y enlace directo de navegación en Waze (`https://waze.com/ul?ll=lat,lon&navigate=yes`).
3. **Anulación Comercial:** Cero bloqueos de saldo o mensajes comerciales cuando se active el protocolo de auxilio.

---

## 5. Invariante IV — Intercepción Fast-Path Zero-Token (<15ms)
1. **Extracción Automática de Pines GPS:** Si el usuario comparte su pin por WhatsApp o el texto incluye `[UBICACION_GPS: lat=..., lon=...]`, el sistema debe extraer inmediatamente las variables de latitud y longitud.
2. **Respuesta Inmediata:** Consultas de ubicación propia ("dónde estoy?", "cuál es mi ubicación?") con coordenadas GPS se resuelven en el FastPath en $<15\text{ ms}$ y con **0 tokens consumidos**, reportando la dirección catastral certificada y los enlaces cartográficos.
