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

import base64
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from src.payments import config, nonce, quote

_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
_BYTES32 = re.compile(r"^0x[0-9a-fA-F]{64}$")
_DIGITS = re.compile(r"^[0-9]{1,20}$")

FACILITATOR_TIMEOUT = 10
MAX_WINDOW_SECONDS = config.MAX_TIMEOUT_SECONDS * 10


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


# --- Leitura de campo ------------------------------------------------------

def _field(source: dict, key: str, code: str = "invalid_payload") -> Any:
    value = source.get(key)
    if value is None or value == "":
        raise VerifyError(code)
    return value


def _int_field(source: dict, key: str, code: str) -> int:
    """Converte exigindo dígitos. `"0.02"` é `value_mismatch`, não 500."""
    raw = str(_field(source, key, code))
    if not _DIGITS.match(raw):
        raise VerifyError(code)
    return int(raw)


def _price(route: str) -> int:
    try:
        return config.price(route)
    except config.ConfigError as exc:
        raise VerifyError("invalid_payload") from exc


def _claim(store: nonce.NonceStore, key: str, route: str, payer: str) -> bool:
    """Usa `claim_capped` quando o backend oferece; senão, `claim`."""
    claim = getattr(store, "claim_capped", None) or store.claim
    return claim(key, route, payer)


# --- Estrutura -------------------------------------------------------------

def decode_signature(header: str) -> dict[str, Any]:
    """`PAYMENT-SIGNATURE` é base64 padrão de um PaymentPayload JSON."""
    if not header:
        raise VerifyError("invalid_payload")
    try:
        payload = json.loads(base64.b64decode(header, validate=True))
    except Exception as exc:
        raise VerifyError("invalid_payload") from exc
    if not isinstance(payload, dict):
        raise VerifyError("invalid_payload")
    return payload


def extract_authorization(payload: dict) -> dict[str, Any]:
    """Aceita `payload.authorization` e a variante aninhada em `payload.payload`."""
    inner = _field(payload, "payload")
    if not isinstance(inner, dict):
        raise VerifyError("invalid_payload")
    if isinstance(inner.get("payload"), dict):
        inner = inner["payload"]
    auth = _field(inner, "authorization")
    if not isinstance(auth, dict):
        raise VerifyError("invalid_payload")
    return auth


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
    return _price(route)


def assert_window(auth: dict, now: int) -> None:
    after = _int_field(auth, "validAfter", "invalid_exact_evm_payload")
    before = _int_field(auth, "validBefore", "invalid_exact_evm_payload")
    if after > now:
        raise VerifyError("invalid_exact_evm_payload_authorization_valid_after")
    if before < now:
        raise VerifyError("invalid_exact_evm_payload_authorization_valid_before")
    if before - after > MAX_WINDOW_SECONDS:
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
    current = int(now if now is not None else time.time())

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
    if not isinstance(accepted, dict):
        raise VerifyError("invalid_payload")
    auth = extract_authorization(payload)

    # 3. oferta
    expected = assert_offer(accepted, route)

    # 4. valor, destino, identidade e janela
    value = _int_field(auth, "value", "invalid_exact_evm_payload")
    if value < expected:
        raise VerifyError("value_mismatch")

    accepted_value = str(accepted.get("value") or accepted.get("maxAmountRequired") or "")
    if not _DIGITS.match(accepted_value) or int(accepted_value) != value:
        raise VerifyError("value_mismatch")

    if str(auth.get("to", "")).lower() != config.pay_to(route):
        raise VerifyError("recipient_mismatch")
    if not _ADDRESS.match(str(auth.get("from", ""))):
        raise VerifyError("invalid_exact_evm_payload")
    if not _BYTES32.match(str(auth.get("nonce", ""))):
        raise VerifyError("invalid_exact_evm_payload")
    assert_window(auth, current)

    payer = str(auth["from"]).lower()

    # 5. jti
    try:
        jti_key = nonce.make_key("jti", claims["j"])
    except nonce.NonceError as exc:
        raise VerifyError("invalid_quote") from exc
    if not _claim(store, jti_key, route, payer):
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
    if not _claim(store, auth_key, route, payer):
        raise VerifyError("duplicate_nonce")

    return Proof(
        payer=payer,
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

    if reason == "settlement_pending" and not tx:
        raise VerifyError("settlement_pending")
    if not result.get("success"):
        raise VerifyError(reason or "settle_failed")
    if not tx:
        raise VerifyError("settle_failed")
    return tx


# --- Demonstração ----------------------------------------------------------

if __name__ == "__main__":
    import os

    os.environ.setdefault(quote.KEY_ENV, quote.genkey())
    config.assert_integrity()

    class StubFacilitator:
        def __init__(self, ok: bool = True) -> None:
            self.ok = ok

        def verify(self, payload, requirements):
            auth = payload["payload"]["authorization"]
            return {
                "isValid": self.ok,
                "payer": auth["from"],
                "invalidReason": None if self.ok else "insufficient_funds",
            }

        def settle(self, payload, requirements):
            return {"success": True, "transaction": "0x" + "ab" * 32,
                    "network": config.network()}

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
        header = base64.b64encode(json.dumps(payload).encode()).decode()
        return body, quote.issue(route, body), header

    store = nonce.MemoryNonce()
    fac = StubFacilitator()

    body, qt, sig = build()
    proof = authorize(route="scan", body=body, quote_token=qt, signature_header=sig,
                      store=store, facilitator=fac)
    print(f"ok: payer {proof.payer[:8]}… valor {proof.value}")
    print(f"settle: {settle_and_confirm(proof, fac)[:12]}…")

    def expect_fail(label: str, **kwargs) -> None:
        try:
            authorize(body=body, store=store, facilitator=fac, **kwargs)
            print(f"{label}: PASSOU (errado)")
        except VerifyError as exc:
            print(f"{label}: {exc.code}")

    expect_fail("replay da cotação", route="scan", quote_token=qt, signature_header=sig)
    expect_fail("reuso em outra rota", route="verify", quote_token=qt, signature_header=sig)

    body2, qt2, sig2 = build(value=config.price("scan") - 1)
    expect_fail("subpagamento", route="scan", quote_token=qt2, signature_header=sig2)

    body3, qt3, sig3 = build()
    expect_fail("facilitador recusa", route="scan", quote_token=qt3, signature_header=sig3)

    # unidade errada: "0.02" em vez de "20000"
    body4, qt4, _ = build()
    payload4 = json.loads(base64.b64decode(build()[2]))
    payload4["accepted"]["value"] = "0.02"
    sig4 = base64.b64encode(json.dumps(payload4).encode()).decode()
    expect_fail("unidade em dólar", route="scan", quote_token=qt4, signature_header=sig4)

    # janela expirada
    body5, qt5, _ = build()
    payload5 = json.loads(base64.b64decode(build()[2]))
    payload5["payload"]["authorization"]["validBefore"] = str(int(time.time()) - 1)
    sig5 = base64.b64encode(json.dumps(payload5).encode()).decode()
    expect_fail("janela expirada", route="scan", quote_token=qt5, signature_header=sig5)