#!/usr/bin/env python3
"""
core/cache_l1.py — Caché L1 en Memoria RAM de Ultra-Baja Latencia
================================================================
Proyecto: Telecomunicaciones Movilnet C.A. — Core PWA Swarm L5
Gobernanza: Universal Best Practices Engineering Rule (Pilar I, II, III, IV)
Propósito: Acelerador L1 thread-safe con TTL para respuestas deterministas O(1) <0.1ms.
"""

from __future__ import annotations

import sys
import time
import threading
import argparse
from typing import Dict, Any, Optional, Tuple


class L1SessionCache:
    """
    Caché L1 thread-safe con tiempo de expiración (TTL) en memoria RAM.
    Permite responder en O(1) con latencias < 0.1ms a consultas repetitivas de saldo y datos.
    """

    def __init__(self, default_ttl_seconds: float = 60.0, max_entries: int = 5000):
        self.default_ttl = float(default_ttl_seconds)
        self.max_entries = int(max_entries)
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor si existe y no ha expirado; de lo contrario retorna None."""
        with self._lock:
            if key not in self._cache:
                return None
            expires_at, val = self._cache[key]
            if time.time() > expires_at:
                del self._cache[key]
                return None
            return val

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Almacena un valor con TTL específico o el valor por defecto."""
        ttl = float(ttl_seconds) if ttl_seconds is not None else self.default_ttl
        with self._lock:
            # Control de tamaño para prevenir fugas de memoria
            if len(self._cache) >= self.max_entries and key not in self._cache:
                now = time.time()
                keys_to_del = [k for k, (exp, _) in self._cache.items() if now > exp]
                for k in keys_to_del:
                    del self._cache[k]
                # Si sigue saturado, descartar la clave más antigua
                if len(self._cache) >= self.max_entries:
                    first_key = next(iter(self._cache))
                    del self._cache[first_key]

            self._cache[key] = (time.time() + ttl, value)

    def invalidate(self, key: str) -> None:
        """Invalida inmediatamente una clave específica."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Limpia la totalidad de la caché L1."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Retorna la cantidad actual de entradas en caché."""
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """Verifica si la clave existe y no ha expirado."""
        return self.get(key) is not None


def _run_self_tests() -> None:
    """Auto-verificación formal del módulo con aserciones y pruebas concurrentes (Pilar II y V)."""
    print("=" * 80)
    print("🧪 [TEST]: Auto-verificación de core/cache_l1.py")
    print("=" * 80)

    # 1. Test básico get y set
    cache = L1SessionCache(default_ttl_seconds=2.0, max_entries=5)
    cache.set("k1", "valor1")
    assert cache.get("k1") == "valor1", "Fallo al recuperar valor almacenado"
    assert cache.size() == 1
    assert "k1" in cache
    assert cache.get("no_existe") is None
    print("  [PASS] Set y Get básico validado.")

    # 2. Test TTL y expiración
    cache.set("k_fast", "temp", ttl_seconds=0.05)
    assert cache.get("k_fast") == "temp"
    time.sleep(0.06)
    assert cache.get("k_fast") is None, "El valor con TTL vencido debió retornar None"
    print("  [PASS] Expiración TTL validada con éxito.")

    # 3. Test Invalidación y Clear
    cache.set("k2", "valor2")
    cache.invalidate("k2")
    assert cache.get("k2") is None
    cache.set("k3", "valor3")
    cache.set("k4", "valor4")
    assert cache.size() >= 2
    cache.clear()
    assert cache.size() == 0
    print("  [PASS] Invalidación puntual y limpieza total (clear) validadas.")

    # 4. Test Capacidad y Evicción LRU/FIFO
    small_cache = L1SessionCache(default_ttl_seconds=10.0, max_entries=3)
    small_cache.set("a", 1)
    small_cache.set("b", 2)
    small_cache.set("c", 3)
    assert small_cache.size() == 3
    small_cache.set("d", 4)  # Debe provocar evicción
    assert small_cache.size() == 3
    assert small_cache.get("d") == 4
    print("  [PASS] Límite de capacidad y evicción de entradas saturadas validado.")

    # 5. Test Concurrente Multi-Hilo (Thread-Safety)
    threads = []
    concurrency_errors = []

    def worker(worker_id: int):
        try:
            for i in range(50):
                k = f"thread_{worker_id}_key_{i % 5}"
                cache.set(k, f"val_{worker_id}_{i}", ttl_seconds=1.0)
                val = cache.get(k)
                if val is not None and not val.startswith(f"val_{worker_id}_"):
                    concurrency_errors.append(f"Lectura cruzada corrupta en hilo {worker_id}")
                if i % 10 == 0:
                    cache.invalidate(k)
        except Exception as e:
            concurrency_errors.append(str(e))

    for w in range(8):
        t = threading.Thread(target=worker, args=(w,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(concurrency_errors) == 0, f"Errores en prueba de concurrencia: {concurrency_errors}"
    print("  [PASS] Concurrencia Thread-Safe (8 hilos en paralelo) 100% exitosa.")

    print("=" * 80)
    print("🏆 [RESULTADO]: 100% PASS (0 fallos en Caché L1)")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Acelerador Caché L1 en Memoria RAM")
    parser.add_argument("--test", action="store_true", help="Ejecuta auto-verificación formal del módulo")
    args = parser.parse_args()

    if args.test or len(sys.argv) == 1:
        _run_self_tests()
