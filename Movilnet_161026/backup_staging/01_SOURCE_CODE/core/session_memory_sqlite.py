#!/usr/bin/env python3
"""
core/session_memory_sqlite.py — Memoria Conversacional Multi-Turno Resiliente (RAM + SQLite WAL)
================================================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilar I, II, III, IV)
Propósito: Gestor de contexto multi-turno con persistencia híbrida en RAM (O(1)) y SQLite WAL.
"""

from __future__ import annotations

import sys
import time
import json
import sqlite3
import threading
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union


class SessionMemory:
    """
    Gestor de contexto multi-turno por sesión y abonado con TTL de 30 minutos.
    Retiene el historial de interacciones recientes para coherencia contextual
    con respaldo resiliente en SQLite (WAL mode) y memoria RAM thread-safe.
    """

    def __init__(
        self,
        session_ttl_seconds: float = 1800.0,
        max_turns: int = 10,
        db_path: Optional[Union[str, Path]] = None
    ):
        self.session_ttl = float(session_ttl_seconds)
        self.max_turns = int(max_turns)
        self.db_path = Path(db_path) if db_path else None
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

        if self.db_path:
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        """Inicializa la tabla user_sessions en SQLite si se configuró db_path."""
        try:
            if not self.db_path.parent.exists():
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        created_at REAL NOT NULL,
                        last_activity REAL NOT NULL,
                        turns_json TEXT NOT NULL,
                        context_json TEXT NOT NULL
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_sessions_activity 
                    ON user_sessions(last_activity);
                """)
                conn.commit()
        except Exception:
            # En caso de error de acceso a disco, opera en modo degradado RAM (Pilar IV)
            pass

    def _persist_to_sqlite(self, session: Dict[str, Any]) -> None:
        """Persiste de forma asíncrona o protegida la sesión en SQLite."""
        if not self.db_path:
            return
        try:
            with sqlite3.connect(str(self.db_path), timeout=2.0) as conn:
                conn.execute("""
                    INSERT INTO user_sessions (session_id, created_at, last_activity, turns_json, context_json)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        last_activity=excluded.last_activity,
                        turns_json=excluded.turns_json,
                        context_json=excluded.context_json;
                """, (
                    session["session_id"],
                    session["created_at"],
                    session["last_activity"],
                    json.dumps(session.get("turns", [])),
                    json.dumps(session.get("context", {}))
                ))
                conn.commit()
        except Exception:
            pass

    def _load_from_sqlite(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Intenta recuperar una sesión desde SQLite si no está en RAM."""
        if not self.db_path:
            return None
        try:
            with sqlite3.connect(str(self.db_path), timeout=2.0) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, created_at, last_activity, turns_json, context_json
                    FROM user_sessions WHERE session_id = ?;
                """, (session_id,))
                row = cursor.fetchone()
                if row:
                    sess_id, created_at, last_activity, turns_json, context_json = row
                    now = time.time()
                    if now - last_activity < self.session_ttl:
                        return {
                            "session_id": sess_id,
                            "created_at": float(created_at),
                            "last_activity": float(last_activity),
                            "turns": json.loads(turns_json),
                            "context": json.loads(context_json)
                        }
                    else:
                        # Sesión expirada en SQLite
                        cursor.execute("DELETE FROM user_sessions WHERE session_id = ?;", (session_id,))
                        conn.commit()
        except Exception:
            pass
        return None

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Recupera o inicializa la sesión multi-turno."""
        with self._lock:
            now = time.time()
            if session_id in self._sessions:
                sess = self._sessions[session_id]
                if now - sess["last_activity"] < self.session_ttl:
                    sess["last_activity"] = now
                    return sess
                else:
                    del self._sessions[session_id]

            # Si no está en RAM, buscar en SQLite
            db_sess = self._load_from_sqlite(session_id)
            if db_sess:
                db_sess["last_activity"] = now
                self._sessions[session_id] = db_sess
                return db_sess

            # Nueva sesión
            new_sess: Dict[str, Any] = {
                "session_id": session_id,
                "created_at": now,
                "last_activity": now,
                "turns": [],
                "context": {}
            }
            self._sessions[session_id] = new_sess
            self._persist_to_sqlite(new_sess)
            return new_sess

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None
    ) -> None:
        """Agrega un turno de conversación limitando al umbral max_turns."""
        with self._lock:
            sess = self.get_session(session_id)
            sess["turns"].append({
                "role": role,
                "content": content,
                "intent": intent,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            if len(sess["turns"]) > self.max_turns:
                sess["turns"] = sess["turns"][-self.max_turns:]
            sess["last_activity"] = time.time()
            self._persist_to_sqlite(sess)

    def set_context_var(self, session_id: str, key: str, value: Any) -> None:
        """Establece una variable de estado en el contexto de la sesión."""
        with self._lock:
            sess = self.get_session(session_id)
            sess["context"][key] = value
            self._persist_to_sqlite(sess)

    def get_context_var(self, session_id: str, key: str, default: Any = None) -> Any:
        """Obtiene una variable de estado del contexto de la sesión."""
        with self._lock:
            sess = self.get_session(session_id)
            return sess["context"].get(key, default)

    def clear_session(self, session_id: str) -> None:
        """Elimina una sesión activa de RAM y de SQLite."""
        with self._lock:
            self._sessions.pop(session_id, None)
            if self.db_path:
                try:
                    with sqlite3.connect(str(self.db_path), timeout=2.0) as conn:
                        conn.execute("DELETE FROM user_sessions WHERE session_id = ?;", (session_id,))
                        conn.commit()
                except Exception:
                    pass

    def active_sessions_count(self) -> int:
        """Retorna el número de sesiones activas en RAM."""
        with self._lock:
            return len(self._sessions)


def _run_self_tests() -> None:
    """Auto-verificación formal del gestor de memoria multi-turno (Pilar II y V)."""
    import tempfile
    print("=" * 80)
    print("🧪 [TEST]: Auto-verificación de core/session_memory_sqlite.py")
    print("=" * 80)

    # 1. Test memoria volátil pura (RAM)
    mem_ram = SessionMemory(session_ttl_seconds=1.0, max_turns=3)
    s1 = mem_ram.get_session("sess-001")
    assert s1["session_id"] == "sess-001"
    assert len(s1["turns"]) == 0
    print("  [PASS] Creación de sesión en RAM validada.")

    # 2. Test adición de turnos y poda por max_turns
    mem_ram.add_turn("sess-001", "user", "Hola")
    mem_ram.add_turn("sess-001", "agent", "Hola, ¿en qué puedo ayudarte?")
    mem_ram.add_turn("sess-001", "user", "Consulta de saldo", intent="BALANCE_QUERY")
    mem_ram.add_turn("sess-001", "agent", "Tu saldo es Bs. 150")

    s1_updated = mem_ram.get_session("sess-001")
    assert len(s1_updated["turns"]) == 3, f"Debió acotar a 3 turnos, tiene {len(s1_updated['turns'])}"
    assert s1_updated["turns"][0]["content"] == "Hola, ¿en qué puedo ayudarte?"
    assert s1_updated["turns"][2]["content"] == "Tu saldo es Bs. 150"
    print("  [PASS] Historial de turnos y poda max_turns correcta.")

    # 3. Test variables de contexto
    mem_ram.set_context_var("sess-001", "auth_level", "VIP")
    assert mem_ram.get_context_var("sess-001", "auth_level") == "VIP"
    assert mem_ram.get_context_var("sess-001", "inexistente", default="DEFAULT") == "DEFAULT"
    print("  [PASS] Manejo de variables de contexto verificado.")

    # 4. Test persistencia y recuperación en SQLite WAL
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = Path(tmp_dir) / "test_sessions.db"
        mem_sqlite = SessionMemory(session_ttl_seconds=60.0, max_turns=5, db_path=test_db)
        mem_sqlite.add_turn("sess-persist", "user", "Turno 1")
        mem_sqlite.add_turn("sess-persist", "agent", "Respuesta 1")
        mem_sqlite.set_context_var("sess-persist", "origin", "pwa_test")

        # Crear nueva instancia apuntando a la misma DB sin nada en RAM
        mem_sqlite_recovered = SessionMemory(session_ttl_seconds=60.0, max_turns=5, db_path=test_db)
        recovered = mem_sqlite_recovered.get_session("sess-persist")
        assert len(recovered["turns"]) == 2, "Fallo al recuperar turnos desde SQLite WAL"
        assert mem_sqlite_recovered.get_context_var("sess-persist", "origin") == "pwa_test"
        print("  [PASS] Persistencia dual SQLite WAL y recuperación 100% exitosa.")

    # 5. Test Expiración TTL
    mem_exp = SessionMemory(session_ttl_seconds=0.05)
    mem_exp.add_turn("sess-exp", "user", "Mensaje temporal")
    time.sleep(0.06)
    sess_renewed = mem_exp.get_session("sess-exp")
    assert len(sess_renewed["turns"]) == 0, "La sesión debió haber expirado"
    print("  [PASS] Expiración TTL multi-turno comprobada.")

    print("=" * 80)
    print("🏆 [RESULTADO]: 100% PASS (0 fallos en Memoria Conversacional)")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Memoria Conversacional Multi-Turno Resiliente")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación formal del módulo")
    args = parser.parse_args()

    if args.test or len(sys.argv) == 1:
        _run_self_tests()
