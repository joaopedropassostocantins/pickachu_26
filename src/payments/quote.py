"""Quote assinada: amarra rota, preço, rede, corpo e validade ao token.

Sem esta trava, um agente paga a rota mais barata, guarda a prova e a reusa
na mais cara. O `accepts[]` do 402 é escolhido pelo cliente, então não serve
como fonte de verdade do preço.

Regras:
1. Preço sai de `config`, nunca do chamador.
2. HMAC-SHA256 com chave de 32 bytes ou mais, comparação em tempo constante.
3. Validade máxima de 300s, padrão de 120s.
4. `check` valida o MAC antes de decodificar: não parseia lixo.
5. A chave é lida a cada chamada, permitindo rotação sem restart.
6. Todo erro sai como `QuoteError`; nada de `ConfigError` ou `AttributeError`
   escapando para virar 500 num handler que só sabe responder 402.

O `jti` (campo `j`) é devolvido em `check` para o armazém de nonce usar como
chave de idempotência.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from src.payments import config

KEY_ENV = "PIKACHU_QUOTE_KEY"
MIN_KEY_BYTES = 32
TTL_DEFAULT = 120
TTL_MAX = 300
VERSION = 1


class QuoteError(Exception):
    """Quote inválida. O `code` é estável e casa com `channel.ERROR_HINTS`."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


# --- Chave -----------------------------------------------------------------

def _key() -> bytes:
    raw = os.getenv(KEY_ENV, "").strip()
    if not raw:
        raise QuoteError("invalid_quote")
    key = raw.encode("utf-8")
    if len(key) < MIN_KEY_BYTES:
        raise QuoteError("invalid_quote")
    return key


def assert_ready() -> None:
    """Chamado no boot: falha fechado se a chave não serve."""
    _key()


def key_fingerprint() -> str:
    """8 hex do SHA-256 da chave. Seguro para log e diagnóstico."""
    return hashlib.sha256(_key()).hexdigest()[:8]


def genkey() -> str:
    """Sugere uma chave nova para colar no .env."""
    return secrets.token_hex(MIN_KEY_BYTES)


# --- Codificação -----------------------------------------------------------

def _mac(key: bytes, raw: str) -> str:
    return hmac.new(key, raw.encode("ascii"), hashlib.sha256).hexdigest()


def _body_hash(body: bytes) -> str:
    """32 hex (128 bits). Com 16 hex a colisão por força bruta é viável."""
    return hashlib.sha256(body).hexdigest()[:32]


def _encode(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(raw: str) -> dict[str, Any]:
    padded = raw + "=" * (-len(raw) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(padded))
    except Exception as exc:
        raise QuoteError("invalid_quote") from exc
    if not isinstance(claims, dict):
        raise QuoteError("invalid_quote")
    return claims


def _price(route: str) -> int:
    """ConfigError vazando daqui viraria 500 no handler."""
    try:
        return config.price(route)
    except config.ConfigError as exc:
        raise QuoteError("invalid_quote") from exc


# --- API -------------------------------------------------------------------

def issue(route: str, body: bytes = b"", ttl: int = TTL_DEFAULT) -> str:
    """Emite quote. Preço e rede são resolvidos aqui, não pelo chamador."""
    if not 0 < ttl <= TTL_MAX:
        raise QuoteError("invalid_quote")
    payload = {
        "v": VERSION,
        "r": route,
        "p": _price(route),
        "n": config.network(),
        "h": _body_hash(body),
        "e": int(time.time()) + ttl,
        "j": secrets.token_hex(8),
    }
    raw = _encode(payload)
    return f"{raw}.{_mac(_key(), raw)}"


def check(token: str, route: str, body: bytes = b"") -> dict[str, Any]:
    """Valida a quote e devolve as claims. Levanta `QuoteError` em qualquer falha.

    Ordem deliberada: MAC antes de decodificar, rota antes de preço (mais
    diagnóstico), expiração antes do corpo (expirou é mais útil que corpo
    trocado).
    """
    if not token or token.count(".") != 1:
        raise QuoteError("invalid_quote")

    raw, _, mac = token.partition(".")
    if not hmac.compare_digest(_mac(_key(), raw), mac):
        raise QuoteError("invalid_quote")

    claims = _decode(raw)

    if claims.get("v") != VERSION:
        raise QuoteError("invalid_quote")
    if claims.get("n") != config.network():
        raise QuoteError("invalid_network")
    if claims.get("r") != route:
        raise QuoteError("invalid_quote")
    if claims.get("p") != _price(route):
        raise QuoteError("value_mismatch")
    if not isinstance(claims.get("e"), int) or claims["e"] < time.time():
        raise QuoteError("quote_expired")
    if claims.get("h") != _body_hash(body):
        raise QuoteError("quote_body_mismatch")
    if not isinstance(claims.get("j"), str) or len(claims["j"]) != 16:
        raise QuoteError("invalid_quote")

    return claims


if __name__ == "__main__":
    if not os.getenv(KEY_ENV):
        print(f"{KEY_ENV} ausente. Sugestão:\n\n{KEY_ENV}={genkey()}\n")
    else:
        print(f"chave presente, fingerprint {key_fingerprint()}")
        body = b'{"code":"x"}'
        token = issue("scan", body)
        print(f"\nquote: {token}")
        print(f"claims: {sorted(check(token, 'scan', body))}")
        try:
            check(token, "verify", body)
        except QuoteError as exc:
            print(f"reuso em outra rota: {exc.code}")
        try:
            check(token, "scan", b'{"code":"y"}')
        except QuoteError as exc:
            print(f"corpo trocado: {exc.code}")