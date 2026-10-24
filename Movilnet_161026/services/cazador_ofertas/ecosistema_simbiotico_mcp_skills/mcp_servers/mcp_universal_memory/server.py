#!/usr/bin/env python3
"""
mcp_universal_memory: Servidor MCP de Memoria SQLite FTS5 con Inyección Presupuestada.
Permite consultar y almacenar conocimiento histórico sin saturar la ventana de contexto (Lost in the Middle).
"""
import sys
import os
import sqlite3
import json
import argparse
from typing import Dict, Any, List, Optional

DB_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "memory_fts5.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "schema.sql")

class UniversalMemoryEngine:
    def __init__(self, db_path: str = DB_DEFAULT_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                self.conn.executescript(f.read())
        else:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_records (
                    id TEXT PRIMARY KEY,
                    layer TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    importance REAL DEFAULT 0.5,
                    estimated_tokens INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts5 USING fts5(
                    id UNINDEXED, layer, entity_id, title, content, tags
                );
            """)
        self.conn.commit()

    def store(self, layer: str, entity_id: str, title: str, content: str, tags: str = "", importance: float = 0.5) -> Dict[str, Any]:
        layer = layer.upper()
        if layer not in ("USER", "PROJECT", "DECISION", "SESSION"):
            raise ValueError(f"Capa no válida: {layer}. Debe ser USER, PROJECT, DECISION o SESSION.")
        
        rec_id = f"MEM-{layer[:3]}-{abs(hash(title + entity_id)) % 1000000:06d}"
        tokens = int(len(content.split()) * 1.3) + 5
        
        with self.conn:
            self.conn.execute("""
                INSERT INTO memory_records (id, layer, entity_id, title, content, tags, importance, estimated_tokens)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content=excluded.content,
                    tags=excluded.tags,
                    importance=excluded.importance,
                    estimated_tokens=excluded.estimated_tokens,
                    updated_at=CURRENT_TIMESTAMP;
            """, (rec_id, layer, entity_id, title, content, tags, importance, tokens))
            self.conn.execute("DELETE FROM memory_fts5 WHERE id = ?", (rec_id,))
            self.conn.execute("""
                INSERT INTO memory_fts5 (id, layer, entity_id, title, content, tags)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (rec_id, layer, entity_id, title, content, tags))
            
        return {"id": rec_id, "layer": layer, "estimated_tokens": tokens, "status": "stored"}

    def query_budgeted(self, query: str, token_budget: int = 400) -> Dict[str, Any]:
        """Consulta FTS5 con ranking BM25 y límite estricto de tokens inyectados."""
        clean_q = "".join(c if c.isalnum() or c.isspace() else " " for c in query).strip()
        if not clean_q:
            return {"tokens_used": 0, "records": [], "count": 0}
            
        terms = clean_q.split()
        fts_query = " OR ".join(f'"{t}"*' for t in terms)
        
        try:
            cursor = self.conn.execute("""
                SELECT m.id, m.layer, m.entity_id, m.title, m.content, m.tags, m.importance, m.estimated_tokens,
                       bm25(memory_fts5) AS bm25_rank
                FROM memory_fts5 f
                JOIN memory_records m ON f.id = m.id
                WHERE memory_fts5 MATCH ?
                ORDER BY (bm25(memory_fts5) * (1.5 - m.importance)) ASC
                LIMIT 10;
            """, (fts_query,))
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            return {"tokens_used": 0, "records": [], "count": 0}

        selected_records = []
        tokens_accumulated = 0
        
        for r in rows:
            rec_tokens = r["estimated_tokens"] or (int(len(r["content"].split()) * 1.3) + 5)
            if tokens_accumulated + rec_tokens <= token_budget:
                tokens_accumulated += rec_tokens
                selected_records.append({
                    "id": r["id"],
                    "layer": r["layer"],
                    "entity_id": r["entity_id"],
                    "title": r["title"],
                    "content": r["content"],
                    "tokens": rec_tokens,
                    "relevance_score": round(float(r["bm25_rank"]), 4)
                })
            else:
                break
                
        return {
            "token_budget": token_budget,
            "tokens_used": tokens_accumulated,
            "tokens_saved": max(0, 1500 - tokens_accumulated),
            "count": len(selected_records),
            "records": selected_records
        }

    def seed_initial_knowledge(self):
        """Inyecta conocimiento fundamental de arquitectura y reglas."""
        self.store(
            layer="DECISION",
            entity_id="GLOBAL-01",
            title="Invariante de Margen Bruto >= 35%",
            content="Ningún producto, servicio o cupón puede operar con margen de contribución inferior al 35%.",
            tags="finanzas margen regla_invariante"
        )
        self.store(
            layer="DECISION",
            entity_id="GLOBAL-02",
            title="Radar Espacial de 3 Zonas",
            content="La proximidad se evalúa en 3 anillos concéntricos: Zona 1 <= 500m, Zona 2 <= 1km, Zona 3 <= 3km.",
            tags="geofencing proximidad gps postgis"
        )
        self.store(
            layer="DECISION",
            entity_id="GLOBAL-03",
            title="Idempotencia en Canjes y Cobros",
            content="Todo canje de cupón o débito de saldo exige Idempotency-Key única para evitar cobros dobles.",
            tags="seguridad idempotencia transacciones"
        )

# Protocolo MCP Stdio
def run_mcp_stdio():
    engine = UniversalMemoryEngine()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "tools/list":
                tools = [
                    {
                        "name": "query_memory",
                        "description": "Consulta memoria histórica con ranking BM25 e inyección presupuestada en tokens.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Término o pregunta de búsqueda"},
                                "token_budget": {"type": "integer", "default": 400, "description": "Límite máximo de tokens a devolver"}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "store_memory",
                        "description": "Almacena una decisión o estado en la memoria permanente indexada.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "layer": {"type": "string", "enum": ["USER", "PROJECT", "DECISION", "SESSION"]},
                                "entity_id": {"type": "string"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "tags": {"type": "string"},
                                "importance": {"type": "number", "default": 0.5}
                            },
                            "required": ["layer", "entity_id", "title", "content"]
                        }
                    }
                ]
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}) + "\n")
                sys.stdout.flush()
                
            elif method == "tools/call":
                params = req.get("params", {})
                name = params.get("name")
                args = params.get("arguments", {})
                
                if name == "query_memory":
                    res = engine.query_budgeted(args.get("query", ""), args.get("token_budget", 400))
                    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False)}]}}) + "\n")
                elif name == "store_memory":
                    res = engine.store(
                        layer=args.get("layer"),
                        entity_id=args.get("entity_id"),
                        title=args.get("title"),
                        content=args.get("content"),
                        tags=args.get("tags", ""),
                        importance=float(args.get("importance", 0.5))
                    )
                    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False)}]}}) + "\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mcp-universal-memory server")
    parser.add_argument("--test", action="store_true", help="Ejecutar autoverificación formal con aserciones")
    parser.add_argument("--seed", action="store_true", help="Sembrar conocimiento inicial")
    args = parser.parse_args()
    
    if args.test:
        test_db = "/tmp/test_universal_memory.db"
        if os.path.exists(test_db):
            os.remove(test_db)
        eng = UniversalMemoryEngine(test_db)
        eng.seed_initial_knowledge()
        
        # Test 1: Inserción y conteo
        s_res = eng.store("PROJECT", "PROJ-01", "Monorepo Cazador", "Estructura monorepo con Next.js y FastAPI.")
        assert s_res["status"] == "stored", "Fallo al almacenar memoria"
        
        # Test 2: Búsqueda con límite de tokens
        q_res = eng.query_budgeted("geofencing radar", token_budget=150)
        assert q_res["count"] > 0, "No encontró registros relevantes en FTS5"
        assert q_res["tokens_used"] <= 150, f"Excedió el presupuesto: {q_res['tokens_used']} > 150"
        
        # Test 3: Capa no válida
        try:
            eng.store("INVALIDA", "E1", "T", "C")
            assert False, "Debió rechazar capa inválida"
        except ValueError:
            pass
            
        print("✅ UniversalMemoryEngine: 3/3 Tests PASSED [Exit code: 0]")
        sys.exit(0)
    elif args.seed:
        eng = UniversalMemoryEngine()
        eng.seed_initial_knowledge()
        print(f"Semillas inyectadas exitosamente en {DB_DEFAULT_PATH}")
    else:
        run_mcp_stdio()
