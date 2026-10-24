# 📜 CONVERSACIÓN MAESTRA — CLIENTE 28: CAZADOR DE OFERTAS MOVILNET (:8030)
### Memoria Técnica Unificada y Registro de Hitos de Montaje

---

## 📌 Identificación del Proyecto
* **Cliente:** Cliente 28 — Cazador de Ofertas Movilnet (Super-App B2C Proximidad & Cuponería)
* **Arquetipo de Negocio:** Híbrido (`physical_inventory` + `financial_and_saas`)
* **Puerto Asignado:** `:8030` (Core REST API + PWA Mobile Zero-Rating)
* **Directorio Raíz:** `/Users/personal/Desktop/IDS_CORE/pruebas_clientes/28_Cazador_Ofertas/`
* **Sellos de Calidad:**
  * `CERT-CAZADOR-PENTARCHY-20261018-SHA256`
  * `CERT-CAZADOR-ESTACION2-ORM-PERSISTENCE-20261018`
  * `CERT-CAZADOR-ESTACION3-SIMBIOSIS-20261018`
  * `CERT-CAZADOR-ESTACION4-DEFLECTOR-20261018`
  * `CERT-CAZADOR-ESTACION5-OMNIBOX-20261018`

---

## 🧭 Hitos Culminados por Estación

### Estación 1: Gobernanza, Modelado Conceptual y Autopsia Forense
* **Especificación:** [`specs/cazador_7_pillars.yaml`](specs/cazador_7_pillars.yaml)
* **Autopsia ScoutIQ:** [`documentos/AUTOPSIA_SCOUTIQ_5_TABLAS_CAZADOR.md`](documentos/AUTOPSIA_SCOUTIQ_5_TABLAS_CAZADOR.md) (Scorecard 98/100).
* **Blueprint Maestro:** [`documentos/MASTER_BLUEPRINT_CAZADORES_OFERTAS.md`](documentos/MASTER_BLUEPRINT_CAZADORES_OFERTAS.md).
* **Matriz de Reglas e I/O:** [`documentos/MATRIZ_REGLAS_ACTORES_Y_PIPELINE_IO.md`](documentos/MATRIZ_REGLAS_ACTORES_Y_PIPELINE_IO.md).

### Estación 2: Persistencia Dual PostGIS/SQLite y Repositorios Hexagonales
* **Modelos ORM:** [`src/infrastructure/persistence/models/`](src/infrastructure/persistence/models/) (`comercio`, `oferta`, `cupon`, `billing`, `boveda`).
* **Repositorios Tipados:** [`src/infrastructure/persistence/repositories/`](src/infrastructure/persistence/repositories/).
* **DDL y Migrador CLI:** [`src/infrastructure/persistence/ddl/migrate.py`](src/infrastructure/persistence/ddl/migrate.py) con soporte SQLite y PostgreSQL PostGIS.
* **Pruebas:** [`tests/test_persistence_layer.py`](tests/test_persistence_layer.py) (7/7 tests passed).

### Estación 3: Dominio Puro y Motores Simbióticos Conectados
* **Servicio de Aplicación:** [`src/application/cazador_service.py`](src/application/cazador_service.py) conectado bidireccionalmente a repositorios ORM y 4 motores MCP (`mcp_spatial_radar`, `mcp_crypto_token_vault`, `mcp_idempotent_gateway`, `mcp_universal_memory`).
* **Control de Acaparamiento:** Máximo 3 cupones activos simultáneos por usuario liberados al canjear en caja POS.
* **Pruebas:** [`tests/test_estacion3_simbiosis.py`](tests/test_estacion3_simbiosis.py) (4/4 tests passed).

### Estación 4: Core Backend API REST y Deflector Zero-Rating
* **DTOs y Routers Modulares:** Desacoplamiento total en [`src/infrastructure/dtos/`](src/infrastructure/dtos/) y [`src/infrastructure/routers/`](src/infrastructure/routers/).
* **Servicio Deflector y Magic Links:** [`src/infrastructure/deflector/magic_link_service.py`](src/infrastructure/deflector/magic_link_service.py) con firma HMAC-SHA256, cabeceras `X-Movilnet-Zero-Rating: active`, webhooks WhatsApp y SMS SMPP conciso ($\le 160$ car.).
* **Invariante Cero Alucinación B2C:** Respuestas fundamentadas al 100% en el catálogo real sin ofertas falsas.
* **Pruebas:** [`tests/test_estacion4_api_deflector.py`](tests/test_estacion4_api_deflector.py) (10/10 tests passed).

### Estación 5: Frontend PWA Mobile-First, Terminal POS y Empaquetado OmniBox
* **PWA Mobile-First:** [`frontend/manifest.json`](frontend/manifest.json) (`display: standalone`, tema `#020617`), Service Worker offline [`frontend/sw.js`](frontend/sw.js) e iconos SVG vectoriales.
* **Interfaz Enriquecida:** [`frontend/index.html`](frontend/index.html) con mapa Leaflet de 3 anillos, detección automática de Magic Links, contador dinámico TOTP QR (60s), Terminal POS de caja con quema de huellas, simulador de Carrier Billing y métricas en vivo.
* **Bundle Nativo macOS:** [`Cazador_Ofertas.app`](Cazador_Ofertas.app) (`Contents/Info.plist` + `Contents/MacOS/launcher`).
* **Scripts Cero Terminal:** [`🚀_INICIAR_CAZADOR_OFERTAS.command`](%F0%9F%9A%80_INICIAR_CAZADOR_OFERTAS.command) y [`🛑_DETENER_CAZADOR_OFERTAS.command`](%F0%9F%9B%91_DETENER_CAZADOR_OFERTAS.command).
* **Pruebas:** [`tests/test_estacion5_pwa_omnibox.py`](tests/test_estacion5_pwa_omnibox.py) (6/6 tests passed).

### Estación 6: Automatización Omnicanal con N8N (WhatsApp, Telegram y PWA)
* **Flujo N8N Oficial:** [`n8n/cazador_ofertas_n8n_workflow.json`](n8n/cazador_ofertas_n8n_workflow.json) con topología de 11 nodos conectando WhatsApp, Telegram y PWA.
* **Manual Operativo N8N:** [`n8n/README_N8N.md`](n8n/README_N8N.md) con guía de importación en 1 clic y pruebas de webhook con curl.
* **Endpoints Ampliados:** `POST /api/deflector/n8n` (Gateway Omnicanal), `POST /api/deflector/telegram` y `POST /api/deflector/pwa`.
* **Pruebas:** [`tests/test_estacion4_api_deflector.py`](tests/test_estacion4_api_deflector.py) (14/14 tests passed).
* **Bitácora Dedicada:** [`documentos/BITACORA_HISTORICA_CAZADOR_OFERTAS.md`](documentos/BITACORA_HISTORICA_CAZADOR_OFERTAS.md) (Registro exhaustivo de 9 capítulos).
* **Balance Oficial Consolidado:** **48/48 tests passed (100% Pass, Exit code: 0)**.

---

## 🏆 Certificación de Culminación
La suite completa de **Cazador de Ofertas Movilnet** ha recorrido y aprobado exitosamente las Estaciones de la Pentarquía Soberana IDS_CORE más la Automatización Omnicanal N8N, contando con 48 pruebas unitarias al 100% de aprobación y 43 archivos Python libres de errores sintácticos.

