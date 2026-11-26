"""Cadeia de validação da prova de pagamento. Fail-closed em todo passo.

Ordem deliberada, cada passo aborta o anterior:

    1. quote      preço e corpo provados por HMAC (A-07)
    2. estrutura  payload é dict, versão 2, campos presentes
    3. oferta     scheme, network, asset, payTo na allowlist (A-05, A-06)
    4. janela     validAfter/validBefore do EIP-3009
    5. nonce jti  a cotação não pode ser reusada (A-02)
    6. /verify    o facilitador decide a assinatura (A-01)
    7. nonce auth a assinatura não pode ser reusada (A-03)

O `auth` é reivindicado DEPOIS do `/verify` de propósito: falha transitória do
facilitador não deve queimar a assinatura do agente. A corrida entre duas
requisições com a mesma assinatura é resolvida pelo `claim` atômico, que roda
antes do `/settle`.

Nunca compare mensagem de erro do facilitador: case por `errorReason` (A-11).
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from src.payments import config, nonce, quote

_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
_BYTES32 = re.compile(r"^0x[0-9a-fA-F]{64}$")
_DIGITS = re.compile(r"^[0-9]{1,20}$")

FACILITATOR_TIMEOUT = 10


class VerifyError(Exception):
    """Falha de pagamento. O `code` é estável e casa com `channel.ERROR_HINTS`."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Proof:
    """Prova já validada, pronta para liquidação. Imutável."""

    payer: str
    route: str
    value: int
    jti: str
    auth_nonce: str
    payload: dict[str, Any]
    requirements: dict[str, Any]


class Facilitator(Protocol):
    def verify(self, payload: dict, requirements: dict) -> dict: ...
    def settle(self, payload: dict, requirements: dict) -> dict: ...


# --- Facilitador HTTP ------------------------------------------------------

class HttpFacilitator:
    """Cliente do facilitador. Único egress autorizado do trilho."""

    def __init__(self, base_url: str, timeout: int = FACILITATOR_TIMEOUT) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def _post(self, path: str, payload: dict, requirements: dict) -> dict[str, Any]:
        body = json.dumps(
            {
                "x402Version": config.X402_VERSION,
                "paymentPayload": payload,
                "paymentRequirements": requirements,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            self._base + path,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                decoded = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise VerifyError("verify_failed") from exc
        if not isinstance(decoded, dict):
            raise VerifyError("verify_failed")
        return decoded

    def verify(self, payload: dict, requirements: dict) -> dict:
        return self._post("/verify", payload, requirements)

    def settle(self, payload: dict, requirements: dict) -> dict:
        return self._post("/settle", payload, requirements)


# --- Validação de estrutura ------------------------------------------------

def _field(source: dict, key: str, code: str = "invalid_payload") -> Any:
    value = source.get(key)
    if value is None or value == "":
        raise VerifyError(code)
    return value


def decode_signature(header: str) -> dict[str, Any]:
    """`PAYMENT-SIGNATURE` é base64 padrão de um PaymentPayload JSON."""
    if not header:
        raise VerifyError("invalid_payload")
    try:
        raw = __import__("base64").b64decode(header, validate=True)
        payload = json.loads(raw)
    except Exception as exc:
        raise VerifyError("invalid_payload") from exc
    if not isinstance(payload, dict):
        raise VerifyError("invalid_payload")
    return payload


def assert_offer(accepted: dict, route: str) -> int:
    """Confere a oferta escolhida contra a allowlist. Devolve o preço esperado."""
    if not isinstance(accepted, dict):
        raise VerifyError("invalid_payload")
    if accepted.get("scheme") != config.SCHEME:
        raise VerifyError("invalid_scheme")
    if accepted.get("network") != config.network():
        raise VerifyError("invalid_network")
    if str(accepted.get("asset", "")).lower() != config.asset().lower():
        raise VerifyError("invalid_asset")
    if str(accepted.get("payTo", "")).lower() != config.pay_to(route):
        raise VerifyError("recipient_mismatch")
    return config.price(route)


def assert_window(auth: dict, now: int) -> None:
    for key in ("validAfter", "validBefore"):
        if not _DIGITS.match(str(_field(auth, key, "invalid_exact_evm_payload"))):
            raise VerifyError("invalid_exact_evm_payload")
    after = int(auth["validAfter"])
    before = int(auth["validBefore"])
    if after > now:
        raise VerifyError("invalid_exact_evm_payload_authorization_valid_after")
    if before < now:
        raise VerifyError("invalid_exact_evm_payload_authorization_valid_before")
    if before - after > config.MAX_TIMEOUT_SECONDS * 10:
        raise VerifyError("invalid_exact_evm_payload")


# --- API -------------------------------------------------------------------

def authorize(
    *,
    route: str,
    body: bytes,
    quote_token: str,
    signature_header: str,
    store: nonce.NonceStore,
    facilitator: Facilitator,
    now: int | None = None,
) -> Proof:
    """Valida a prova inteira. Levanta `VerifyError` em qualquer falha."""
    current = int(now if now is not None else __import__("time").time())

    # 1. cotação
    try:
        claims = quote.check(quote_token, route, body)
    except quote.QuoteError as exc:
        raise VerifyError(exc.code) from exc

    # 2. estrutura
    payload = decode_signature(signature_header)
    if payload.get("x402Version") != config.X402_VERSION:
        raise VerifyError("invalid_x402_version")

    accepted = _field(payload, "accepted")
    inner = _field(payload, "payload")
    if not isinstance(inner, dict):
        raise VerifyError("invalid_payload")
    auth = _field(inner, "payload") if "payload" in inner else _field(inner, "authorization")

    # 3. oferta
    expected = assert_offer(accepted, route)

    # 4. valor e janela
    if not _DIGITS.match(str(_field(auth, "value", "invalid_exact_evm_payload"))):
        raise VerifyError("invalid_exact_evm_payload")
    value = int(auth["value"])
    if value < expected:
        raise VerifyError("value_mismatch")
    if int(str(accepted.get("value") or accepted.get("maxAmountRequired") or 0)) != value:
        raise VerifyError("value_mismatch")
    if str(auth.get("to", "")).lower() != config.pay_to(route):
        raise VerifyError("recipient_mismatch")
    if not _ADDRESS.match(str(auth.get("from", ""))):
        raise VerifyError("invalid_exact_evm_payload")
    if not _BYTES32.match(str(auth.get("nonce", ""))):
        raise VerifyError("invalid_exact_evm_payload")
    assert_window(auth, current)

    # 5. jti
    try:
        jti_key = nonce.make_key("jti", claims["j"])
    except nonce.NonceError as exc:
        raise VerifyError("invalid_quote") from exc
    if not store.claim(jti_key, route, str(auth["from"]).lower()):
        raise VerifyError("duplicate_nonce")

    # 6. facilitador
    verdict = facilitator.verify(payload, accepted)
    if not verdict.get("isValid"):
        raise VerifyError(str(verdict.get("invalidReason") or "verify_failed"))

    # 7. nonce da assinatura
    try:
        auth_key = nonce.make_key("auth", str(auth["nonce"])[2:])
    except nonce.NonceError as exc:
        raise VerifyError("invalid_exact_evm_payload") from exc
    if not store.claim(auth_key, route, str(auth["from"]).lower()):
        raise VerifyError("duplicate_nonce")

    return Proof(
        payer=str(auth["from"]).lower(),
        route=route,
        value=value,
        jti=claims["j"],
        auth_nonce=str(auth["nonce"]).lower(),
        payload=payload,
        requirements=accepted,
    )


def settle_and_confirm(proof: Proof, facilitator: Facilitator) -> str:
    """Liquida e devolve o hash. Só aqui o trabalho pode ser entregue."""
    result = facilitator.settle(proof.payload, proof.requirements)
    reason = str(result.get("errorReason") or "")
    tx = str(result.get("transaction") or "")

    if reason == "settlement_pending":
        if not tx:
            raise VerifyError("settlement_pending")
    if not result.get("success"):
        raise VerifyError(reason or "settle_failed")
    if not tx:
        raise VerifyError("settle_failed")
    return tx


# --- Demonstração ----------------------------------------------------------

if __name__ == "__main__":
    import os
    import sqlite3
    import time

    os.environ.setdefault(quote.KEY_ENV, quote.genkey())
    config.assert_integrity()

    class StubFacilitator:
        def __init__(self, ok: bool = True) -> None:
            self.ok = ok
            self.settled = 0

        def verify(self, payload, requirements):
            return {"isValid": self.ok, "payer": payload["payload"]["authorization"]["from"],
                    "invalidReason": None if self.ok else "insufficient_funds"}

        def settle(self, payload, requirements):
            self.settled += 1
            return {"success": True, "transaction": "0x" + "ab" * 32, "network": config.network()}

    def build(route: str = "scan", value: int | None = None) -> tuple[bytes, str, str]:
        body = b'{"code":"x"}'
        now = int(time.time())
        auth = {
            "from": "0x" + "aa" * 20,
            "to": config.pay_to(route),
            "value": str(value if value is not None else config.price(route)),
            "validAfter": str(now - 5),
            "validBefore": str(now + 100),
            "nonce": "0x" + os.urandom(32).hex(),
        }
        payload = {
            "x402Version": config.X402_VERSION,
            "accepted": config.accepts(route, "https://x.invalid")[0],
            "payload": {"signature": "0xdead", "authorization": auth},
        }
        import base64
        header = base64.b64encode(json.dumps(payload).encode()).decode()
        return body, quote.issue(route, body), header

    store = nonce.MemoryNonce()
    fac = StubFacilitator()

    body, qt, sig = build()
    proof = authorize(route="scan", body=body, quote_token=qt, signature_header=sig,
                      store=store, facilitator=fac)
    print(f"ok: payer {proof.payer[:8]}… valor {proof.value}")
    print(f"settle: {settle_and_confirm(proof, fac)[:12]}…")

    for label, kwargs in [
        ("replay da cotação", dict(quote_token=qt, signature_header=sig)),
        ("reuso em outra rota", dict(quote_token=qt, signature_header=sig, route="verify")),
    ]:
        try:
            authorize(route=kwargs.pop("route", "scan"), body=body, store=store,
                      facilitator=fac, **kwargs)
            print(f"{label}: PASSOU (errado)")
        except VerifyError as exc:
            print(f"{label}: {exc.code}")

    body2, qt2, sig2 = build(value=config.price("scan") - 1)
    try:
        authorize(route="scan", body=body2, quote_token=qt2, signature_header=sig2,
                  store=store, facilitator=fac)
    except VerifyError as exc:
        print(f"subpagamento: {exc.code}")

    body3, qt3, sig3 = build()
    try:
        authorize(route="scan", body=body3, quote_token=qt3, signature_header=sig3,
                  store=store, facilitator=StubFacilitator(ok=False))
    except VerifyError as exc:
        print(f"facilitador recusa: {exc.code}")