# 📘 Manual de Despliegue e Instalación On-Premise — CORE_MOVILNET
**Proyecto:** AI_Movilnet_300926 / Core PWA Swarm L5  
**Cliente:** Telecomunicaciones Movilnet C.A.  
**Destinatario:** Gerencia de Infraestructura, Operaciones TI y Seguridad de la Información  
**Versión del Paquete:** `CORE_MOVILNET_EXPORT_151026`  
**Sello Criptográfico SHA-256 del Paquete:** `be6fe911cd005f5882d1ee3ff2b8d659757e47345a97bbc411055f69bffec9ea`  
**Fecha de Emisión:** 15 de Octubre de 2026  

---

## 1. Arquitectura y Visión General del Sistema

El sistema **CORE_MOVILNET** es una plataforma de telecomunicaciones de alta disponibilidad (Carrier-Grade) diseñada para atender a más de 4.000.000 de abonados (prefijos `0416` y `0426`). Integra un núcleo de microservicios Python con arquitectura limpia, un motor de consenso y reglas departamentales, agentes de inteligencia artificial (Swarm L5), persistencia híbrida (SQLite WAL para ultra-baja latencia y PostgreSQL 16 para trazabilidad analítica), orquestación con n8n y túneles de borde seguros Cloudflare Zero-Trust.

```mermaid
flowchart TD
    subgraph Edge ["🌐 Capa de Borde y Acceso"]
        CF["Cloudflare Zero-Trust Tunnel / Nginx SSL"]
        PWA["PWA Clientes & Agentes (HTML5 / Web Workers)"]
        WPP["WhatsApp Meta Cloud / Telegram Bot"]
    end

    subgraph Core ["⚙️ Núcleo de Aplicación (Host / Docker)"]
        API["Core API & FastPath Router (:8010)"]
        FSM["Motor de Estados FSM & Reglas Departamentales"]
        MCP["Servidores MCP (Telco, Geo, C2P, EIR)"]
        AI["Swarm Subagentes (Customer Care, NOC, Retention)"]
    end

    subgraph Data ["💾 Capa de Persistencia y Automatización"]
        SQLITE[("SQLite WAL: local_movilnet.db\n1.239 Registros / Agentes")]
        POSTGRES[("PostgreSQL 16: ids_postgres_db (:5433)\nDecisiones & Notebook Sources")]
        N8N["Instancia n8n (10 Workflows / Google Suite)"]
    end

    CF --> API
    PWA --> API
    WPP --> N8N
    N8N --> API
    API --> FSM
    FSM --> MCP
    MCP --> AI
    API --> SQLITE
    API --> POSTGRES
```

---

## 2. Requerimientos de Hardware y Software en Servidores del Cliente

### 2.1. Especificaciones de Hardware Recomendadas

| Componente | Requisito Mínimo (Entorno Staging/QA) | Requisito Recomendado (Producción On-Premise) |
| :--- | :--- | :--- |
| **Arquitectura** | x86_64 o ARM64 (Apple Silicon / Graviton) | x86_64 Intel Xeon / AMD EPYC |
| **CPU** | 4 Cores Físicos (2.4 GHz+) | 8 Cores / 16 Hilos |
| **Memoria RAM** | 8 GB DDR4 | 16 GB - 32 GB DDR4 ECC |
| **Almacenamiento** | 50 GB SSD NVMe | 200 GB SSD NVMe (RAID 1 / RAID 10) |
| **Red** | Interfaz 1 Gbps LAN | Doble Interfaz 10 Gbps redundante |

### 2.2. Sistema Operativo y Software Base Requerido

- **Sistema Operativo:** Ubuntu Server 22.04 LTS / 24.04 LTS, Debian 12, RHEL 9 o macOS Sonoma/Sequoia.
- **Docker Engine:** Versión 24.0.0 o superior con plugin `docker-compose-v2`.
- **Python:** Versión 3.11.x (o superior) con `pip` y `venv`.
- **SQLite3:** Versión 3.39.0 o superior (con soporte para WAL y JSON1).
- **PostgreSQL Client Tools:** `psql` versión 16.
- **Utilidades de Sistema:** `curl`, `rsync`, `tar`, `shasum` (o `sha256sum`), `openssl`.

---

## 3. Estructura del Paquete de Migración

Al descomprimir `CORE_MOVILNET_EXPORT_151026.tar.gz`, el equipo encontrará la siguiente estructura desacoplada:

```text
backup_staging/
├── 01_SOURCE_CODE/                 # Código fuente limpio del Core, APIs, PWA y tests
├── 02_DATABASES_AND_STATE/        # Dumps SQLite consistentes, PostgreSQL y esquemas DDL
├── 03_N8N_WORKFLOWS_AND_CREDS/    # 10 Flujos JSON listos para importar e inventario de credenciales
├── 04_AI_AGENTS_AND_MCP/          # Configuración de subagentes, Skills (.md), MCP servers y reglas
├── 05_INFRASTRUCTURE_AND_NETWORK/ # Binarios Cloudflared, scripts guardian, Dockerfiles
├── 06_SECRETS_BACKUP/             # Variables de entorno .env, plantillas y protocolos de rotación
└── 07_DEPLOYMENT_SCRIPTS/         # Lanzadores autónomos (.command / .sh)
```

---

## 4. Guía de Instalación Paso a Paso

### Paso 1: Verificación de Integridad del Archivo Maestro

Antes de descomprimir, certifique matemáticamente que el archivo no ha sido alterado ni truncado:

```bash
# En Linux:
sha256sum CORE_MOVILNET_EXPORT_151026.tar.gz

# En macOS:
shasum -a 256 CORE_MOVILNET_EXPORT_151026.tar.gz
```

> [!IMPORTANT]
> El hash obtenido DEBE coincidir exactamente con:  
> `be6fe911cd005f5882d1ee3ff2b8d659757e47345a97bbc411055f69bffec9ea`  
> Si el hash no coincide, descarte el archivo y contacte al equipo emisor.

### Paso 2: Descompresión y Organización del Directorio

```bash
# Crear directorio de trabajo en el servidor
sudo mkdir -p /opt/movilnet/core_production
sudo chown -R $USER:$USER /opt/movilnet

# Extraer el contenido
tar -xzvf CORE_MOVILNET_EXPORT_151026.tar.gz -C /opt/movilnet/core_production
cd /opt/movilnet/core_production
```

### Paso 3: Aprovisionamiento de Variables de Entorno y Secretos

1. Copie la configuración de entorno a la raíz del código fuente:
   ```bash
   cp 06_SECRETS_BACKUP/.env 01_SOURCE_CODE/.env
   chmod 600 01_SOURCE_CODE/.env
   ```
2. Edite `01_SOURCE_CODE/.env` para ajustar los valores propios de su red e infraestructura:
   ```ini
   # Núcleo API
   PORT=8010
   HOST=0.0.0.0
   APP_ENV=production

   # Base de Datos PostgreSQL
   DATABASE_URL=postgresql://ids_user:ids_secure_password_2026@127.0.0.1:5433/ids_ag_nblm_stich
   POSTGRES_USER=ids_user
   POSTGRES_PASSWORD=ids_secure_password_2026
   POSTGRES_DB=ids_ag_nblm_stich
   POSTGRES_PORT=5433

   # IA y Modelos Externos
   GEMINI_API_KEY=AIzaSy...TuClaveAqui...
   GEMINI_MODEL=gemini-2.5-flash

   # n8n Cloud / On-Premise
   N8N_BASE_URL=https://n8n.lpgtec.net
   N8N_API_KEY=TuApiKeyN8n
   N8N_MCP_URL=https://n8n.lpgtec.net/mcp-server/http
   N8N_MCP_TOKEN=TuTokenMCP
   ```

### Paso 4: Restauración de Bases de Datos

#### 4.1. Base de Datos SQLite (Transacciones y Clientes Locales)
La base SQLite ya viene pre-cargada con el dataset certificado de 1.239 registros de agentes comerciales y puntos de interés (POIs):
```bash
mkdir -p 01_SOURCE_CODE/db
cp 02_DATABASES_AND_STATE/local_movilnet.db 01_SOURCE_CODE/db/local_movilnet.db

# Verificar integridad del archivo SQLite
sqlite3 01_SOURCE_CODE/db/local_movilnet.db "PRAGMA integrity_check;"
# Debe responder: ok
```

#### 4.2. Base de Datos PostgreSQL (Docker Container)
Levante el contenedor de PostgreSQL 16 y restaure el volcado:
```bash
# Iniciar contenedor PostgreSQL en puerto 5433
docker run -d \
  --name ids_postgres_db \
  --restart unless-stopped \
  -e POSTGRES_USER=ids_user \
  -e POSTGRES_PASSWORD=ids_secure_password_2026 \
  -e POSTGRES_DB=ids_ag_nblm_stich \
  -p 5433:5432 \
  -v ids_movilnet_pgdata:/var/lib/postgresql/data \
  postgres:16-alpine

# Esperar 5 segundos a que la base inicie
sleep 5

# Restaurar esquema y datos de PostgreSQL
docker exec -i ids_postgres_db psql -U ids_user -d ids_ag_nblm_stich < 02_DATABASES_AND_STATE/postgres_ids_ag_nblm_stich_dump.sql

# Verificar tablas creadas
docker exec -it ids_postgres_db psql -U ids_user -d ids_ag_nblm_stich -c "\dt"
```

### Paso 5: Instalación del Entorno Virtual de Python y Dependencias

```bash
cd /opt/movilnet/core_production/01_SOURCE_CODE

# Crear entorno virtual aislado
python3.11 -m venv venv
source venv/bin/activate

# Actualizar pip e instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Verificar que no existen conflictos de dependencias
pip check
```

### Paso 6: Configuración e Importación de Flujos de n8n

1. Ingrese a la consola web de su servidor n8n (ej. `https://n8n.tu-empresa.com`).
2. Cree o verifique las credenciales necesarias (Postgres, Google Cloud OAuth2, Meta WhatsApp Token).
3. Importe los flujos JSON desde la carpeta `03_N8N_WORKFLOWS_AND_CREDS/`:
   - `viki_lpgtec_v2_ids_instant_dispatch.json` (Flujo Principal de Despacho)
   - `viki_lpgtec_v2_ids_aaa_certified.json`
   - `viki_lpgtec_v2_ids_with_google_suite.json`
   - `movilnet_whatsapp_ai_workflow.json`
   - `movilnet_c2p_payment_workflow.json`
   - `movilnet_incident_eir_lock_workflow.json`
4. Active los flujos conmutando el interruptor `Active` en la interfaz de n8n.
5. Configure la URL del Webhook Ingest en el Core para recibir eventos en:  
   `http://<IP_SERVIDOR>:8010/api/v1/n8n/webhook-ingest`

### Paso 7: Publicación Segura (Cloudflare Tunnel o Nginx In-House)

#### Opción A: Mediante Cloudflare Zero-Trust Tunnel (Incluido)
El paquete incluye el binario y el guardián de túnel automático:
```bash
cd /opt/movilnet/core_production/01_SOURCE_CODE
# Ejecutar guardián de túnel Cloudflare
python3 scripts/tunnel_cloudflare_guardian.py --port 8010
```
El túnel generará una URL pública segura (ej. `https://*.trycloudflare.com`) con HTTPS sin necesidad de abrir puertos en el firewall perimetral.

#### Opción B: Mediante Nginx Reverse Proxy Propio
Si dispone de certificados SSL propios de Movilnet:
```nginx
server {
    listen 443 ssl http2;
    server_name core.movilnet.com.ve;

    ssl_certificate /etc/ssl/certs/movilnet_wildcard.crt;
    ssl_certificate_key /etc/ssl/private/movilnet_wildcard.key;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Paso 8: Despliegue en Producción y Verificación de Salud

Inicie el servicio principal:
```bash
cd /opt/movilnet/core_production/01_SOURCE_CODE
source venv/bin/activate

# Iniciar servidor Uvicorn de alta concurrencia
python3 api/service.py
```

En otra terminal, verifique la salud del microservicio:
```bash
curl -s http://127.0.0.1:8010/api/v1/health | jq .
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "AI_Movilnet_300926_Core",
  "database": "connected",
  "agents_active": 6,
  "mcp_tools_registered": 12
}
```

---

## 5. Pruebas de Certificación del Despliegue (100% Pass)

Para certificar que el despliegue es completamente funcional y libre de anomalías, ejecute la suite de pruebas automatizadas:

```bash
cd /opt/movilnet/core_production/01_SOURCE_CODE
source venv/bin/activate

# Ejecutar suite de validación rápida
python3 -m pytest tests/test_system_config.py tests/test_phase1_db.py tests/test_all_mcp_suites.py -v
```

Todas las pruebas deben concluir en verde (`100% passed, 0 failures`).

---

## 6. Monitoreo, Mantenimiento y Respaldos Rutinarios

1. **Monitoreo de Procesos:**
   - La PWA administrativa se encuentra en: `http://localhost:8010/ui/dashboard/noc_dashboard.html`
   - El conversatorio en vivo de agentes se ubica en: `http://localhost:8010/ui/monitor/conversatorio.html`
2. **Respaldo Periódico de la Base SQLite:**
   ```bash
   sqlite3 /opt/movilnet/core_production/01_SOURCE_CODE/db/local_movilnet.db ".backup '/opt/backups/movilnet_$(date +%Y%m%d).db'"
   ```
3. **Respaldo Periódico de PostgreSQL:**
   ```bash
   docker exec ids_postgres_db pg_dump -U ids_user ids_ag_nblm_stich > /opt/backups/postgres_$(date +%Y%m%d).sql
   ```

---

## 7. Contacto y Soporte Técnico

Para dudas de arquitectura, soporte de integración o escalamiento:
- **Área:** Gerencia de Tecnología e Innovación — Movilnet C.A.
- **Canal de Arquitectura:** `arquitectura.ti@movilnet.com.ve`
- **Sello de Calidad:** Certificación Nivel 5 Antigravity Engineering
