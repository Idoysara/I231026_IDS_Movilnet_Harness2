# 📦 GUÍA DE PORTABILIDAD MULTIPROYECTO: MÓDULO DE DESPACHO MULTIMODAL
**Proyecto:** Telecomunicaciones Movilnet C.A. — Módulo Autónomo de Despacho Multimodal  
**Gobernanza:** Universal Best Practices Engineering Rule (Pilares I y II)  
**Propósito:** Instrucciones paso a paso para extraer, reusar y desplegar este módulo en **cualquier otro proyecto o stack de software**.  

---

## 1. 🎯 Filosofía de Autonomía de Módulos (Pilar II)

El **Módulo de Despacho Multimodal** fue construido bajo la directriz estricta de **Cero Acoplamiento con el Core de Movilnet**. Esto significa que:
* No importa clases ni módulos del directorio padre (`core/`, `api/`, `db/`).
* Posee su propio motor de base de datos (`multimodal_vault.db`), su propio esquema de directorios (`vaults/`), sus propios modelos Pydantic y sus propias suites de pruebas.
* Puede funcionar como:
  1. **Microservicio REST Independiente:** Corriendo en un puerto dedicado (ej: `:8025`).
  2. **Biblioteca / Paquete Python:** Importado directamente mediante `from domain.models import ...`.
  3. **Contenedor Docker Hardened:** Desplegable en cualquier Kubernetes o servicio Cloud (Render, AWS, GCP, Fly.io).

---

## 2. 🚀 Cómo Reusar este Módulo en Otro Proyecto (En 3 Pasos)

### Paso 1: Copiar la Carpeta
Simplemente copia la carpeta completa `MODULO_DESPACHO_MULTIMODAL/` a la raíz de tu nuevo proyecto:
```bash
cp -r /Users/ismael/Desktop/121026_CORE_MOVILNET/Movilnet_161026/MODULO_DESPACHO_MULTIMODAL/ /ruta/a/tu/nuevo_proyecto/MODULO_DESPACHO_MULTIMODAL/
```

### Paso 2: Configurar las Variables de Entorno (`.env`)
En el nuevo proyecto, copia el archivo de ejemplo y ajusta los parámetros deseados:
```bash
cd /ruta/a/tu/nuevo_proyecto/MODULO_DESPACHO_MULTIMODAL/
cp .env.example .env
```
Edita `.env` para definir:
* `MULTIMODAL_PORT`: El puerto deseado (ej. `8025` o `9000`).
* `MULTIMODAL_SECRET_KEY`: Tu clave secreta para la generación de hashes ciegos de usuario.
* `MULTIMODAL_USER_QUOTA_BYTES`: Límite de almacenamiento por usuario (por defecto: `52428800` = 50 MB).

### Paso 3: Inicializar la Base de Datos y Arrancar
Ejecuta el script autónomo de inicialización y arranca el microservicio:
```bash
python3 scripts/init_multimodal_db.py --test
./INICIAR_MODULO_MULTIMODAL.command
```

---

## 3. 🔌 Modalidades de Integración en Sistemas Externos

### Modalidad A: Integración vía API REST (Cualquier Lenguaje: Node.js, Go, PHP, Java)
El servidor expone endpoints estándar JSON:

```bash
# 1. Verificar salud del servicio
curl http://localhost:8025/health

# 2. Inicializar o consultar la bóveda de un usuario
curl -X POST http://localhost:8025/api/v1/vault/init \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+584121234567"}'

# 3. Subir un archivo binario a la bóveda privada
curl -X POST http://localhost:8025/api/v1/media/upload \
  -F "phone_number=+584121234567" \
  -F "direction=INBOUND" \
  -F "file=@/ruta/a/comprobante.jpg"

# 4. Listar activos multimedia del usuario
curl http://localhost:8025/api/v1/vault/+584121234567/assets
```

---

### Modalidad B: Integración como Biblioteca Python Interna
Si tu backend ya está escrito en Python (FastAPI, Flask, Django):

```python
import sys
sys.path.append("/ruta/a/tu/nuevo_proyecto/MODULO_DESPACHO_MULTIMODAL")

from application.vault_service import VaultService
from application.media_processor import MediaProcessor
from infrastructure.database import get_multimodal_connection
from infrastructure.repository import MultimodalRepository

# Inicializar servicios
conn = get_multimodal_connection("./multimodal_vault.db")
repo = MultimodalRepository(conn)
vault_service = VaultService(repo, vault_root="./vaults", secret_key="mi_secreto")
media_processor = MediaProcessor(vault_service, repo)

# 1. Asegurar la bóveda del usuario
vault = vault_service.get_or_create_vault("+584121234567")
print(f"Bóveda activa: {vault.vault_id}, uso: {vault.quota_used_bytes} bytes")

# 2. Ingerir y almacenar un archivo
with open("nota_de_voz.ogg", "rb") as f:
    file_bytes = f.read()

asset = media_processor.ingest_file(
    phone_number="+584121234567",
    filename="nota_de_voz.ogg",
    file_bytes=file_bytes,
    direction="INBOUND"
)

print(f"Archivo guardado exitosamente. Asset ID: {asset.asset_id}")
```

---

### Modalidad C: Integración en n8n o Flujos de Automatización
Cualquier canvas de n8n puede interactuar con este módulo mediante un simple nodo **HTTP Request**:
* **Method:** `POST`
* **URL:** `http://127.0.0.1:8025/api/v1/multimodal/process`
* **Body Parameters:**
  ```json
  {
    "phone_number": "={{ $json.from }}",
    "media_type": "AUDIO",
    "media_url": "={{ $json.media_url }}",
    "mime_type": "audio/ogg"
  }
  ```

---

## 4. 🧪 Verificación de Aislamiento y Autonomía (100% PASS)

Para validar que el módulo funciona de forma completamente autónoma sin requerir el resto del repositorio, ejecuta:
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
**Criterio de Éxito:** 100% de pruebas aprobadas, 0 dependencias externas fallidas, tiempo de ejecución < 1.0 segundo.
