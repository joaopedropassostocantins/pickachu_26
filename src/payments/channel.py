"""Corpo do 402 e do erro — o único canal que o agente lê por obrigação.

Diferente de anúncio, aqui a leitura é determinística: o agente precisa da
resposta para continuar. Isso torna o corpo um canal de instrução, e um
canal de instrução tem regras próprias:

1. Instrução antes de dado. Nenhum parâmetro do usuário aparece antes do
   bloco de instrução (A-08: injeção no corpo).
2. Preço em dólar E em unidade atômica, no mesmo parágrafo (A-12).
3. Endereço e valor em texto puro, para agente sem carteira programática.
4. Orçamento de caracteres fixo. Estourou, a descrição cai primeiro.

Nada aqui decide pagamento. `channel` só monta resposta; quem julga é
`verify`.
"""
from __future__ import annotations

import base64
import json
import re
from typing import Any

from src.payments import config

MAX_INSTRUCTION_CHARS = 900
MAX_URL_DISPLAY = 200

# Parâmetros de rota entram na URL e no texto: allowlist estrita.
_PARAM = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

ERROR_HINTS: dict[str, str] = {
    "invalid_scheme": "accepted.scheme deve ser 'exact'",
    "invalid_network": "accepted.network deve ser exatamente o da oferta",
    "invalid_asset": "accepted.asset deve ser o contrato USDC da oferta",
    "recipient_mismatch": "accepted.payTo difere do endereço da rota",
    "value_mismatch": "authorization.value menor que o preço da rota",
    "invalid_quote": "PAYMENT-QUOTE ausente, expirada ou com HMAC inválido",
    "quote_body_mismatch": "o corpo do request mudou depois da cotação",
    "quote_expired": "cotação expirada; refaça o GET para obter outra",
    "duplicate_nonce": "este nonce já foi gasto; assine uma nova autorização",
    "settlement_pending": "liquidação em curso sem hash; repita em 2s",
    "verify_failed": "o facilitador recusou a prova; verifique saldo e "free_tier_exhausted": "limite gratuito do IP atingido; pagar não espera",
    "invalid_payload": "PaymentPayload ausente ou malformado",
    "invalid_x402_version": "x402Version deve ser 2",
    "invalid_exact_evm_payload": "authorization EIP-3009 ausente ou com campo inválido",
    "invalid_exact_evm_payload_authorization_valid_after": "validAfter ainda no futuro",
    "invalid_exact_evm_payload_authorization_valid_before": (
        "validBefore já passou; assine nova autorização"
    ),
    "settle_failed": "liquidação falhou; repita com a mesma prova",
}

class ChannelError(ValueError):
    """Parâmetro de rota inválido para montar o corpo."""


def _check_params(params: dict[str, str]) -> None:
    for name, value in params.items():
        if not _PARAM.match(str(value)):
            raise ChannelError(f"parâmetro inválido: {name}={value!r}")


def _url(route: str, base_url: str, **params: str) -> str:
    return base_url.rstrip("/") + config.resource(route, **params)


def _display_url(route: str, base_url: str, **params: str) -> str:
    """URL para o texto: trunca base longa para não comer o orçamento."""
    url = _url(route, base_url, **params)
    if len(url) <= MAX_URL_DISPLAY:
        return url
    return url[: MAX_URL_DISPLAY - 1] + "…"


def _display_quote(token: str) -> str:
    """Encurta só a exibição. O token inteiro segue em `next.quote`."""
    if len(token) <= MAX_QUOTE_DISPLAY:
        return token
    return token[: MAX_QUOTE_DISPLAY - 1] + "…"


def instructions(
    route: str,
    quote: str,
    base_url: str,
    with_description: bool = True,
    **params: str,
) -> str:
    """Bloco de instrução. Determinístico, sem dado de usuário antes dele."""
    value = config.price(route)
    lines = [
        f"PAYMENT REQUIRED — {config.usd(value)} USDC "
        f"({value} atomic units, 6 decimals) on {config.network()}.",
        "",
        "Resend the SAME request to:",
        f"  POST {_display_url(route, base_url, **params)}",
        "",
        "Add both headers:",
        "  PAYMENT-SIGNATURE: <base64 PaymentPayload, x402Version 2>",
        f"  PAYMENT-QUOTE: {quote}",
        "",
        f"Authorization must match exactly: to={config.pay_to(route)}, "
        f"value={value}, asset={config.asset()}.",
        f"Window: {config.MAX_TIMEOUT_SECONDS}s. The quote is bound to the body hash.",
        "",
        "Do not change the body after quoting; a new body needs a new GET.",
    ]
    if with_description:
        lines += ["", f"Returns: {config.DESCRIPTIONS[route]}"]
    return "\n".join(lines)


def _render(route: str, quote: str, base_url: str, **params: str) -> str:
    """Orçamento em três estágios: descrição, depois exibição da quote.

    O token inteiro continua em `next.quote` e no header PAYMENT-QUOTE; só a
    exibição no texto é encurtada, e por último.
    """
    text = instructions(route, quote, base_url, **params)
    if len(text) > MAX_INSTRUCTION_CHARS:
        text = instructions(route, quote, base_url, with_description=False, **params)
    if len(text) > MAX_INSTRUCTION_CHARS:
        text = instructions(
            route, _display_quote(quote), base_url,
            with_description=False, **params,
        )
    return text


def payment_required(
    route: str, base_url: str, quote: str, **params: str
) -> dict[str, Any]:
    """Objeto PaymentRequired. `next` é para a máquina, `instructions` para o modelo."""
    _check_params(params)
    return {
        "x402Version": config.X402_VERSION,
        "instructions": _render(route, quote, base_url, **params),
        "next": {
            "method": "POST",
            "url": _url(route, base_url, **params),
            "headers": ["PAYMENT-SIGNATURE", "PAYMENT-QUOTE"],
            "quote": quote,
        },
        "accepts": config.accepts(route, base_url, **params),
        "error": "PAYMENT-SIGNATURE header required",
    }


def payment_failed(
    code: str, route: str, base_url: str, quote: str, **params: str
) -> dict[str, Any]:
    """402 de nova tentativa. Nunca 200: falha de pagamento é sempre fechada."""
    _check_params(params)
    body = payment_required(route, base_url, quote, **params)
    body["error"] = code
    body["hint"] = ERROR_HINTS.get(code, "reexiba o corpo do request original")
    return body


def free_tier_exhausted(
    route: str, base_url: str, quote: str, retry_after: int = 3600, **params: str
) -> dict[str, Any]:
    """Free tier estourado: a saída é pagar, não esperar."""
    _check_params(params)
    body = payment_required(route, base_url, quote, **params)
    body["error"] = "free_tier_exhausted"
    body["hint"] = ERROR_HINTS["free_tier_exhausted"]
    body["retryAfter"] = retry_after
    return body


def _b64(obj: dict[str, Any]) -> str:
    """Base64 padrão: `-` e `_` do urlsafe quebram decodificador de cliente."""
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()


def headers(body: dict[str, Any]) -> dict[str, str]:
    """Cabeçalhos do 402. `Vary` impede cache servir 200 para request sem prova."""
    return {
        "PAYMENT-REQUIRED": _b64(body),
        "PAYMENT-QUOTE": body["next"]["quote"],
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        "Vary": "PAYMENT-SIGNATURE",
    }


if __name__ == "__main__":
    demo = payment_required(
        "pack", "https://api.example.invalid", "QUOTE.DEMO", id="2026.11"
    )
    print(json.dumps(demo, ensure_ascii=False, indent=2))
    print("\n--- instrução renderizada ---\n")
    print(demo["instructions"])
    print(f"\nchars: {len(demo['instructions'])} / {MAX_INSTRUCTION_CHARS}")
    print(f"header PAYMENT-REQUIRED: {len(_b64(demo))} bytes b64")
    assert len(demo["instructions"]) <= MAX_INSTRUCTION_CHARS