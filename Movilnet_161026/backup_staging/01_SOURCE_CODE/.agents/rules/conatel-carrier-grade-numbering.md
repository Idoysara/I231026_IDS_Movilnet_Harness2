# 📡 Regla Carrier-Grade: Taxonomía y Clasificación de Tráfico CONATEL (UIT-T E.164)

Esta directiva rige el tratamiento, validación, ingesta y enrutamiento de todo número telefónico (MSISDN) en el ecosistema Movilnet 4GMAX, conforme al Plan Nacional de Numeración de CONATEL (Providencia Administrativa N° 096 y UIT-T E.164).

---

## 🏛️ 1. Taxonomía Oficial de Numeración en Venezuela (10 Dígitos: `0` + 3 Prefijo + 7 Abonado)

### A. Telefonía Celular (Móvil)
* **`0416` / `0426` ➔ Telecomunicaciones Movilnet C.A.:** Red móvil oficial del Estado. Únicos prefijos autorizados para consultar saldo, megas y contratos directamente en la base de datos ODA de Movilnet.
* **`0414` / `0424` ➔ Telefónica Movistar Venezuela (Telcel C.A.):** Competencia directa.
* **`0412` ➔ Corporación Digitel C.A.:** Competencia directa.

### B. Telefonía Fija Tradicional y Zonal (Geográfica)
* **`0212` ➔ Gran Caracas:** Distrito Capital, Miranda y La Guaira (Vargas).
* **`02XX` Regionales:**
  * **Central:** `0241` a `0245` (Carabobo), `0243`/`0244` (Aragua), `0246`/`0249` (Guárico), `0247` (Apure), `0248` (Amazonas).
  * **Centro-Occidente:** `0251`/`0252`/`0257` (Lara), `0253`/`0254` (Yaracuy), `0255`/`0256` (Portuguesa), `0258` (Cojedes).
  * **Zulia & Falcón:** `0261` a `0267` (Zulia), `0268`/`0269` (Falcón).
  * **Los Andes:** `0271`/`0272` (Trujillo), `0273` (Barinas), `0274`/`0275` (Mérida), `0276` a `0278` (Táchira).
  * **Oriente & Guayana:** `0281` a `0284` (Anzoátegui), `0285`/`0286`/`0288`/`0289` (Bolívar), `0287` (Delta Amacuro), `0291`/`0292` (Monagas), `0293`/`0294` (Sucre), `0295` (Nueva Esparta).
* **Operadores:** CANTV (incumbente) y operadores locales con red física o HFC.

### C. Telefonía IP (VoIP) de los ISPs (FTTH / GPON) y Servicios No Geográficos
1. **ISPs de Fibra Óptica (NetUno, Inter, Fibex, Airtek, Thundernet, Vnet, Supercable):**
   * CONATEL no otorga prefijos "03xx" ni móviles para VoIP residencial.
   * Los ISPs operan bajo habilitación de **Telefonía Fija Local sobre redes de datos/IP** recibiendo sub-bloques numéricos dentro de los mismos códigos geográficos **`02XX`** (ej. NetUno Voz en Caracas `0212`, Airtek en Maracaibo `0261`).
2. **Códigos No Geográficos Nacionales (Servicios Especiales / VoIP PBX / Contact Centers):**
   * **`0800` ➔ Cobro Revertido Automático (Toll-Free):** 100% gratuito para el usuario, costeado por la empresa (soporte y atención de ISPs y operadoras).
   * **`0500` ➔ Acceso Universal con Cobro Compartido:** El usuario paga costo local; estándar para PBX IP empresariales, banca e ISPs.
   * **`0501` ➔ Acceso Universal con Cobro Total al Usuario.**
   * **`0900` ➔ Servicios de Tarificación Adicional.**

---

## 🚫 2. Guardarraíles Inviolables de Dominio (Zero-Hallucination)

1. **Prohibición Absoluta de Sembrado Forzado en Base de Datos:**
   Queda estrictamente prohibido que cualquier script, webhook o test cree o inserte en la base de datos de Movilnet ODA un número con prefijo `0414`, `0424`, `0412`, `02XX` o `0500/0800` como si fuera un abonado activo de Movilnet.
2. **Enrutamiento Mandatorio por Tipo de Tráfico (`CarrierFunnelClassifier`):**
   * **Móviles Competencia (`0414`, `0424`, `0412`):** Se interceptan de inmediato hacia la ruta comercial `FUNNEL_MARKETING_PORTABILIDAD` (oferta de bienvenida: eSIM gratis + bono de 10 GB).
   * **Fijas CANTV / ISPs (`02XX`):** Se orientan con pedagogía institucional hacia los planes móviles y datos celulares de Movilnet 4GMAX.
   * **VoIP Especiales (`0500`, `0800`):** Se gestionan como líneas corporativas/institucionales.
3. **Regla del 100% Pass en Pruebas:**
   Toda modificación en los extractores de payloads o enrutadores debe mantener aprobada la suite completa de pruebas (`pytest tests/`) y cero hallazgos documentales.
