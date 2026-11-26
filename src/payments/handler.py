"""Cola do trilho: rota → 402 → verify → trabalho → settle → 200.

Sem framework. `handle` recebe dados e devolve dados, então o mesmo código roda
num servidor HTTP, num teste ou numa função de borda.

Quatro invariantes:

1. Nada executa antes de `verify.authorize` retornar. Trabalho só depois de
   pagamento verificado e nonces reivindicados.
2. Falha de settle DEPOIS do trabalho devolve o resultado junto com nota de
   crédito. O agente não paga duas vezes pelo mesmo scan.
3. `ValueError` do trabalho é 400; qualquer outra exceção é 502 com crédito.
4. Rota desconhecida aponta para o llms.txt, não devolve 404 mudo.

Ordem do fluxo `authorization` do x402: verify → recurso → settle.
"""
from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from src.payments import channel, config, nonce, quote, verify

MAX_BODY_BYTES = 256 * 1024
_METHOD = {"scan": "POST", "verify": "POST", "pack": "GET"}
_JSON = {"Content-Type": "application/json; charset=utf-8"}


def _compile(template: str) -> re.Pattern[str]:
    out: list[str] = []
    for part in re.split(r"(\{\w+\})", template):
        m = re.fullmatch(r"\{(\w+)\}", part)
        if m:
            out.append(rf"(?P<{m.group(1)}>[A-Za-z0-9._-]{{1,64}})")
        else:
            out.append(re.escape(part))
    return re.compile("^" + "".join(out) + "$")


_ROUTES = {route: _compile(tpl) for route, tpl in config.RESOURCES.items()}


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes = b""
    client_ip: str = ""


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Deps:
    base_url: str
    store: nonce.NonceStore
    facilitator: verify.Facilitator
    work: Callable[[str, dict[str, str], bytes], dict[str, Any]]
    free_tier: Callable[[str], bool]
    clock: Callable[[], int] = lambda: int(time.time())


def _json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()


def _match(path: str) -> tuple[str, dict[str, str]] | None:
    for route, pattern in _ROUTES.items():
        found = pattern.match(path)
        if found:
            return route, found.groupdict()
    return None


def _error(status: int, code: str, **extra: Any) -> Response:
    return Response(status, _json({"error": code, **extra}), dict(_JSON))


def _payment_402(body: dict[str, Any]) -> Response:
    return Response(402, _json(body), channel.headers(body))


def _credit() -> str:
    """Nota de crédito: prova de que o trabalho rodou sem liquidação."""
    return "cr_" + secrets.token_hex(8)


def handle(request: Request, deps: Deps) -> Response:
    """Ponto único de entrada. Nunca levanta: converte tudo em resposta."""
    if len(request.body) > MAX_BODY_BYTES:
        return _error(413, "payload_too_large", maxBytes=MAX_BODY_BYTES)

    matched = _match(request.path)
    if matched is None:
        return _error(404, "unknown_route", map=f"{deps.base_url.rstrip('/')}/llms.txt")

    route, params = matched
    if request.method != _METHOD[route]:
        return _error(405, "method_not_allowed", expected=_METHOD[route])

    headers = {k.lower(): v for k, v in request.headers.items()}

    try:
        token = quote.issue(route, request.body)
    except quote.QuoteError as exc:
        return _error(500, exc.code)

    signature = headers.get("payment-signature", "")
    quote_header = headers.get("payment-quote", "")

    # Sem prova de pagamento: oferece a porta, com cotação nova.
    if not signature:
        if deps.free_tier(request.client_ip):
            return _run(route, params, request, deps, proof=None)
        return _payment_402(
            channel.free_tier_exhausted(route, deps.base_url, token, **params)
        )

    # Com prova: a cotação do header precisa ser a que assina este corpo.
    if not quote_header:
        return _payment_402(
            channel.payment_failed("invalid_quote", route, deps.base_url, token, **params)
        )

    try:
        proof = verify.authorize(
            route=route, body=request.body, quote_token=quote_header,
            signature_header=signature, store=deps.store,
            facilitator=deps.facilitator, now=deps.clock(),
        )
    except verify.VerifyError as exc:
        return _payment_402(
            channel.payment_failed(exc.code, route, deps.base_url, token, **params)
        )

    return _run(route, params, request, deps, proof=proof)


def _run(
    route: str,
    params: dict[str, str],
    request: Request,
    deps: Deps,
    proof: verify.Proof | None,
) -> Response:
    """Executa o trabalho e liquida. Pagamento já verificado, se houver."""
    try:
        result = deps.work(route, params, request.body)
    except ValueError as exc:
        return _error(400, "bad_request", detail=str(exc)[:200])
    except Exception:
        # Nonces já queimados: o agente precisa de nova assinatura, por isso a
        # nota de crédito.
        return _error(502, "work_failed", credit=_credit())

    if proof is None:
        return Response(200, _json({"result": result, "paid": False}), dict(_JSON))

    try:
        tx = verify.settle_and_confirm(proof, deps.facilitator)
    except verify.VerifyError as exc:
        return Response(
            402,
            _json({
                "error": exc.code,
                "hint": channel.ERROR_HINTS.get(exc.code, ""),
                "credit": _credit(),
                "result": result,
            }),
            {**_JSON, "PAYMENT-RESPONSE": "failed"},
        )

    return Response(
        200,
        _json({"result": result, "paid": True, "payer": proof.payer}),
        {**_JSON, "PAYMENT-RESPONSE": tx},
    )