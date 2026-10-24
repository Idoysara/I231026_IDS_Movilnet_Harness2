#!/bin/bash
# ==============================================================================
# Lanzador 1-Clic: Servidor Autónomo de Despacho Multimodal (:8025)
# Telecomunicaciones Movilnet C.A. — Gobernanza: Universal Best Practices
# ==============================================================================

set -e

# Ubicación del script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "================================================================================"
echo "🚀 INICIANDO MÓDULO AUTÓNOMO DE DESPACHO MULTIMODAL MOVILNET"
echo "================================================================================"
echo "📍 Directorio: $DIR"
echo "🔌 Puerto HTTP: :8025"
echo "🗄️ Base de Datos: multimodal_vault.db (SQLite WAL)"
echo "📁 Raíz de Bóvedas: $DIR/vaults"
echo "================================================================================"

# Inicializar tablas DDL
python3 scripts/init_multimodal_db.py

# Iniciar servidor
python3 service/server.py --port 8025
