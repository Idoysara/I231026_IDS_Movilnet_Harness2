# 🎯 Cliente 28: Cazador de Ofertas Movilnet (:8030)
### Super-App Soberana de Proximidad, Cuponería Dinámica TOTP y Facturación Carrier Billing 0416/0426

---

## 🏛️ 1. Resumen Ejecutivo
**Cazador de Ofertas Movilnet** es una plataforma soberana de geolocalización, radar de proximidad y cuponería comercial anti-fraude diseñada para operar sobre las líneas celulares Movilnet (`0416` y `0426`) bajo el régimen de exención de cobro de datos móviles (**Zero-Rating**).

### Arquetipo de Negocio Polimórfico:
* **Híbrido:** `physical_inventory` (inventario físico de comercios aliados) + `financial_and_saas` (cuponería digital, conciliación bancaria y Carrier Billing).

---

## 🛡️ 2. Invariantes Matemáticas y Reglas de Negocio
1. **Invariante II (David Díaz Robisco):** Todo producto o combo publicado debe satisfacer un **Margen Bruto de Contribución $\ge 35\%$**:
   $$\text{Margen Bruto} = \frac{\text{Precio Oferta} - \text{Costo Directo}}{\text{Precio Oferta}} \ge 0.35$$
2. **Invariante Fundamental de Cero Alucinación B2C:** Ninguna respuesta de búsqueda o propuesta conversacional puede inventar ofertas, precios o comercios ficticios. Todo resultado se fundamenta estrictamente en la base de datos verificada.
3. **Split Transaccional Inmutable:**
   * **20% Telco Movilnet:** Comisión por facturación y habilitación Zero-Rating.
   * **80% Comercio / Plataforma:** Liquidación neta para el comercio emisor.
4. **Bóveda Anti-Replay TOTP Rotativa (60s):**
   * El código dinámico QR rota cada 60 segundos con firma HMAC-SHA256 (`QRO-...`).
   * Al canjearse en la caja del comercio, la huella digital se quema atómicamente en la tabla `boveda_hashes_quemados`, imposibilitando ataques de captura de pantalla o doble canje.
5. **Control de Cuota Anti-Acaparamiento:**
   * Máximo **3 cupones activos simultáneos** por usuario Movilnet. La cuota se libera atómicamente cuando el cupón es canjeado en POS.

---

## 🏗️ 3. Topología y Arquitectura Hexagonal
El código se organiza en capas desacopladas sin monolitos:
```
pruebas_clientes/28_Cazador_Ofertas/
├── 🚀_INICIAR_CAZADOR_OFERTAS.command     # Lanzador de doble clic para el dueño
├── INSTRUCCIONES_DUENO.md                  # Manual sin tecnicismos
├── data/                                   # SQLite local y semillas demo
├── documentos/                             # Autopsia ScoutIQ, Blueprint y Matriz de Reglas
├── frontend/                               # PWA Mobile-First con mapa Leaflet y TOTP QR
├── specs/                                  # Especificación formal de los 7 Pilares YAML
├── src/                                    # Capas del dominio y microservicios
│   ├── domain/                             # Entidades, FSM inmutable e Invariantes puras
│   ├── application/                        # CazadorApplicationService (4 MCPs simbióticos)
│   └── infrastructure/
│       ├── persistence/                    # DDL PostGIS/SQLite, Modelos ORM y Repositorios
│       ├── dtos/                           # Esquemas tipados Pydantic v2
│       ├── deflector/                      # MagicLinkService HMAC y Zero-Rating
│       ├── routers/                        # Endpoints modulares REST (:8030)
│       └── app.py                          # Ensamblador central FastAPI
└── tests/                                  # 38 tests automatizados (100% Pass)
```

---

## ⚡ 4. Matriz de Endpoints RESTful (:8030)

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/health` | Monitoreo del servicio y métricas clave en vivo |
| `GET` | `/api/radar/ofertas` | Radar geoespacial de 3 anillos (500m, 1500m, 3000m) |
| `POST` | `/api/cupon/reclamar` | Emisión de cupón TOTP con firma HMAC (Cuota máx 3) |
| `POST` | `/api/cupon/canjear` | Validación y canje en caja POS con quema anti-replay |
| `GET` | `/api/cupon/usuario/{msisdn}` | Consulta de cupones emitidos por suscriptor |
| `POST` | `/api/billing/debitar` | Débito Carrier Billing idempotente (Split 20/80) |
| `GET` | `/api/billing/historial/{msisdn}`| Historial de cobros de saldo Movilnet |
| `GET` | `/api/comercios` | Catálogo de comercios aliados verificados |
| `GET` | `/api/ofertas` | Listado de ofertas promocionales activas |
| `POST` | `/api/ofertas` | Publicación de nueva oferta con validación de margen $\ge 35\%$ |
| `POST` | `/api/deflector/whatsapp` | Webhook de deflexión para WhatsApp con Magic Link Zero-Rating |
| `POST` | `/api/deflector/sms-smpp` | Webhook SMS conciso ($\le 160$ caracteres) |
| `POST` | `/api/deflector/telegram` | Webhook específico para Telegram con soporte WebApp Button |
| `POST` | `/api/deflector/pwa` | Endpoint para consultas y eventos directos de la PWA |
| `POST` | `/api/deflector/n8n` | Gateway Unificado Omnicanal para n8n Workflow Automation |
| `GET` | `/api/deflector/verificar-link`| Validación de firma de enlace y cabeceras Zero-Rating |

---

## 🔄 5. Flujo de Nodos N8N (Automatización Omnicanal)
El sistema incluye el workflow formal importable en [`n8n/cazador_ofertas_n8n_workflow.json`](n8n/cazador_ofertas_n8n_workflow.json) con documentación en [`n8n/README_N8N.md`](n8n/README_N8N.md), conectando los canales de WhatsApp, Telegram y PWA a través del Gateway `:8030/api/deflector/n8n`.

---

## 🧪 6. Evidencia de Certificación Militar
* **Comando:** `.venv/bin/pytest pruebas_clientes/28_Cazador_Ofertas/tests/ -v`
* **Resultado:** **`48 passed in 3.69s, 0 failed [Exit code: 0]`**
* **Pureza AST:** **43 archivos Python** con **0 SyntaxError**.

