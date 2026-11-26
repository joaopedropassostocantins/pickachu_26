"""Armazém de nonce: anti-replay (A-02) e anti-double-spend (A-03).

Duas famílias de nonce, porque são dois furos diferentes:

    jti   — o `j` da quote. Impede reusar a mesma cotação.
    auth  — o nonce EIP-3009 da autorização. Impede reusar a mesma assinatura.

O nonce EIP-3009 é validado pelo contrato USDC, mas só na liquidação. Entre o
verify e o settle existe uma janela em que a mesma assinatura passaria duas
vezes e o trabalho seria feito duas vezes. Por isso o registro é local.

Atomicidade: `INSERT` puro, sem `OR IGNORE`. Conflito de chave primária é a
resposta de replay, e ela vem do banco, não da aplicação.

Backends: `MemoryNonce` (teste) e `SqlNonce` (SQLite/D1). Ambos síncronos.
"""
from __future__ import annotations

import re
import sqlite3
import threading
import time
from typing import Protocol

DEFAULT_TTL = 600          # folga sobre o TTL máximo da quote (300s)
MAX_ENTRIES = 200_000
_KEY = re.compile(r"^(jti|auth):[A-Za-z0-9]{16,80}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS spent_nonce (
  key        TEXT PRIMARY KEY,
  resource   TEXT NOT NULL,
  payer      TEXT NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nonce_payer ON spent_nonce (payer, expires_at);
CREATE INDEX IF NOT EXISTS idx_nonce_expiry ON spent_nonce (expires_at);
"""


class NonceError(ValueError):
    """Chave ou TTL inválido."""


class NonceStore(Protocol):
    def claim(self, key: str, resource: str, payer: str, ttl: int = DEFAULT_TTL) -> bool: ...
    def count_for(self, payer: str, window: int) -> int: ...
    def sweep(self, now: int | None = None) -> int: ...


def make_key(kind: str, value: str) -> str:
    """Monta e valida a chave composta. `kind` em {jti, auth}."""
    if kind not in {"jti", "auth"}:
        raise NonceError(f"tipo de nonce inválido: {kind!r}")
    key = f"{kind}:{value}"
    _validate_key(key)
    return key


def _validate_key(key: str) -> None:
    """Validação na fronteira de escrita: `claim` também passa por aqui."""
    if not isinstance(key, str) or not _KEY.match(key):
        raise NonceError(f"nonce malformado: {key!r}")


def _check_ttl(ttl: int) -> None:
    if not isinstance(ttl, int) or isinstance(ttl, bool) or not 0 < ttl <= 3600:
        raise NonceError(f"ttl inválido: {ttl!r}")


def _expiry(ttl: int, now: int | None = None) -> int:
    return (now if now is not None else int(time.time())) + ttl


# --- Backend em memória ----------------------------------------------------

class MemoryNonce:
    """Backend de teste. Thread-safe, com teto de entradas."""

    def __init__(self, max_entries: int = MAX_ENTRIES) -> None:
        self._data: dict[str, tuple[str, str, int]] = {}
        self._lock = threading.Lock()
        self._max = max_entries

    def claim(self, key: str, resource: str, payer: str, ttl: int = DEFAULT_TTL) -> bool:
        _validate_key(key)
        _check_ttl(ttl)
        now = int(time.time())
        with self._lock:
            existing = self._data.get(key)
            if existing and existing[2] > now:
                return False
            # Só ocupa espaço novo se a chave não existir (mesmo expirada).
            if existing is None and len(self._data) >= self._max:
                self._sweep_locked(now)
                if len(self._data) >= self._max:
                    return False            # fail-closed: cheio recusa
            self._data[key] = (resource, payer, _expiry(ttl, now))
            return True

    def count_for(self, payer: str, window: int) -> int:
        now = int(time.time())
        with self._lock:
            return sum(
                1 for _, p, exp in self._data.values()
                if p == payer and exp > now and exp - now <= window
            )

    def sweep(self, now: int | None = None) -> int:
        with self._lock:
            return self._sweep_locked(now if now is not None else int(time.time()))

    def _sweep_locked(self, now: int) -> int:
        dead = [k for k, (_, _, exp) in self._data.items() if exp <= now]
        for k in dead:
            del self._data[k]
        return len(dead)


# --- Backend SQL -----------------------------------------------------------

class SqlNonce:
    """Backend durável (SQLite local, D1). Síncrono."""

    def __init__(self, conn: sqlite3.Connection, max_entries: int = MAX_ENTRIES) -> None:
        self._conn = conn
        self._max = max_entries
        self._conn.executescript(SCHEMA)

    def _count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM spent_nonce").fetchone()
        return int(row[0]) if row else 0

    def _insert(self, key: str, resource: str, payer: str, expires_at: int) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO spent_nonce (key, resource, payer, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (key, resource, payer, expires_at),
            )

    def claim(self, key: str, resource: str, payer: str, ttl: int = DEFAULT_TTL) -> bool:
        _validate_key(key)
        _check_ttl(ttl)
        now = int(time.time())
        expires_at = _expiry(ttl, now)

        try:
            self._insert(key, resource, payer, expires_at)
            return True
        except sqlite3.IntegrityError:
            pass

        row = self._conn.execute(
            "SELECT expires_at FROM spent_nonce WHERE key = ?", (key,)
        ).fetchone()
        if row and row[0] > now:
            return False                      # replay vivo

        try:
            with self._conn:
                self._conn.execute("DELETE FROM spent_nonce WHERE key = ?", (key,))
            self._insert(key, resource, payer, expires_at)
            return True
        except sqlite3.IntegrityError:
            return False                      # perdeu a corrida: fail-closed

    def count_for(self, payer: str, window: int) -> int:
        now = int(time.time())
        row = self._conn.execute(
            "SELECT COUNT(*) FROM spent_nonce "
            "WHERE payer = ? AND expires_at > ? AND expires_at - ? <= ?",
            (payer, now, now, window),
        ).fetchone()
        return int(row[0]) if row else 0

    def sweep(self, now: int | None = None) -> int:
        cutoff = now if now is not None else int(time.time())
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM spent_nonce WHERE expires_at <= ?", (cutoff,)
            )
        return cur.rowcount

    def claim_capped(
        self, key: str, resource: str, payer: str, ttl: int = DEFAULT_TTL
    ) -> bool:
        """`claim` com teto global. Chame este em produção."""
        if self._count() >= self._max:
            self.sweep()
            if self._count() >= self._max:
                return False
        return self.claim(key, resource, payer, ttl)


if __name__ == "__main__":
    store = MemoryNonce()
    key = make_key("jti", "0123456789abcdef")
    print(f"primeiro claim: {store.claim(key, 'scan', '0xabc')}")
    print(f"replay:         {store.claim(key, 'scan', '0xabc')}")
    print(f"sweep(now+601) remove {store.sweep(int(time.time()) + 601)}")
    print(f"após sweep:     {store.claim(key, 'scan', '0xabc')}")
    for bad in ("lixo", "auth:curto"):
        try:
            store.claim(bad, "scan", "0xabc")
        except NonceError as exc:
            print(f"chave inválida: {exc}")