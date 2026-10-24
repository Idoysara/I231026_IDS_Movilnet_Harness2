# ==============================================================================
# Dockerfile Multi-Stage — AI_Movilnet_300926
# Telecomunicaciones Movilnet C.A. — 4.000.000 de Abonados (0416 / 0426)
# ==============================================================================

# Etapa 1: Builder / Dependencias
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Etapa 2: Imagen Final Hardened / Non-Root
FROM python:3.11-slim AS runner

LABEL maintainer="Gerencia de Tecnología Movilnet C.A. <arquitectura.ti@movilnet.com.ve>"
LABEL description="AI_Movilnet_300926 Core API & Swarm L5 Microservice"
LABEL version="1.0.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    APP_ENV=production \
    PATH="/home/movilnet/.local/bin:$PATH"

RUN groupadd -g 1001 movilnet && \
    useradd -u 1001 -g movilnet -s /bin/bash -m movilnet

WORKDIR /app

# Copiar dependencias de builder
COPY --from=builder /root/.local /home/movilnet/.local

# Copiar código fuente
COPY --chown=movilnet:movilnet api/ /app/api/
COPY --chown=movilnet:movilnet core/ /app/core/
COPY --chown=movilnet:movilnet db/ /app/db/
COPY --chown=movilnet:movilnet mcp/ /app/mcp/
COPY --chown=movilnet:movilnet ui/ /app/ui/
COPY --chown=movilnet:movilnet reports/ /app/reports/
COPY --chown=movilnet:movilnet scripts/ /app/scripts/
COPY --chown=movilnet:movilnet services/ /app/services/

RUN chmod -R 775 /app/db /app/reports /app/services && \
    chown -R movilnet:movilnet /app /home/movilnet

USER movilnet

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request, os; p = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{p}/health', timeout=3)" || exit 1

CMD ["python3", "api/service.py"]
