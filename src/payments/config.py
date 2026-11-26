"""Constantes do trilho de pagamento — fonte única de verdade.

INVARIANTE CENTRAL: `payTo` nunca vem do request. Cada rota tem endereço
fixo em allowlist, e `assert_integrity()` falha fechado se algo divergir.

Unidade: TODOS os preços estão em unidade atômica (6 decimais, USDC).
20_000 = $0.02. Confundir isso com dólar é o bug silencioso mais comum
do x402 e multiplica a cobrança por 1000.

Endereços podem ser colados com checksum EIP-55 (maiúsculas misturadas,
como BaseScan e as carteiras entregam); a normalização para minúsculas
acontece na saída, em `pay_to()`.
"""
from __future__ import annotations

import os
import re
from decimal import Decimal

# --- Protocolo -------------------------------------------------------------

X402_VERSION = 2
SCHEME = "exact"

# --- Rede ------------------------------------------------------------------

NETWORK_MAINNET = "eip155:8453"    # Base
NETWORK_TESTNET = "eip155:84532"   # Base Sepolia

_NETWORKS: dict[str, str] = {
    "mainnet": NETWORK_MAINNET,
    "testnet": NETWORK_TESTNET,
}

ASSET_MAINNET = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"   # USDC Base
ASSET_TESTNET = "0x036cbd53842c5426634e7929541eC2318f3dcf7e"   # USDC Base Sepolia

DECIMALS = 6

# --- Preços (atômico, 6 decimais) -----------------------------------------

PRICES_ATOMIC: dict[str, int] = {
    "scan": 20_000,     # $0.02
    "verify": 50_000,   # $0.05 — teto por unidade (regra dos 3%)
    "pack": 20_000,     # $0.02
}

MAX_UNIT_PRICE_ATOMIC = 50_000
MAX_TIMEOUT_SECONDS = 120
FREE_TIER_PER_IP_DAY = 100

# --- Rotas (templates; parâmetros entre chaves) ----------------------------

RESOURCES: dict[str, str] = {
    "scan": "/v1/scan/snippet",
    "verify": "/v1/verify/policy",
    "pack": "/v1/policy/pack/{id}",
}

DESCRIPTIONS: dict[str, str] = {
    "scan": "Achados de segurança em snippet de código de agente, com PoC",
    "verify": "Veredito assinado para policy de diagnóstico",
    "pack": "Policy pack assinado, versionado",
}

# --- Destino (SUBSTITUA pelos seus endereços reais) ------------------------
# Placeholders válidos em formato; troque pelos seus e rode
# `python -m src.payments.config` para confirmar.

PAY_TO: dict[str, str] = {
    "scan": "0x1111111111111111111111111111111111111111",
    "verify": "0x2222222222222222222222222222222222222222",
    "pack": "0x3333333333333333333333333333333333333333",
}

_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")


class ConfigError(RuntimeError):
    """Configuração inconsistente. Sempre fatal, nunca silenciosa."""


# --- Seletores -------------------------------------------------------------

def _env_network() -> str:
    """Allowlist estrita. Valor desconhecido é fatal, não vira testnet."""
    raw = os.getenv("PIKACHU_NETWORK", "testnet").strip().lower()
    if raw not in _NETWORKS:
        raise ConfigError(
            f"PIKACHU_NETWORK inválido: {raw!r} (use 'mainnet' ou 'testnet')"
        )
    return raw


def is_mainnet() -> bool:
    return _env_network() == "mainnet"


def network() -> str:
    return _NETWORKS[_env_network()]


def asset() -> str:
    return ASSET_MAINNET if is_mainnet() else ASSET_TESTNET


def price(route: str) -> int:
    try:
        return PRICES_ATOMIC[route]
    except KeyError as exc:
        raise ConfigError(f"rota sem preço: {route}") from exc


def pay_to(route: str) -> str:
    """Sempre minúsculas: EIP-55 é formato de exibição, não de comparação."""
    try:
        return PAY_TO[route].lower()
    except KeyError as exc:
        raise ConfigError(f"rota sem payTo: {route}") from exc


def resource(route: str, **params: str) -> str:
    try:
        template = RESOURCES[route]
    except KeyError as exc:
        raise ConfigError(f"rota desconhecida: {route}") from exc
    try:
        return template.format(**params)
    except KeyError as exc:
        raise ConfigError(f"{route}: falta o parâmetro {exc}") from exc


def usd(atomic: int) -> str:
    """Formata unidade atômica para exibição. Só para log e llms.txt."""
    return f"${Decimal(atomic) / Decimal(10 ** DECIMALS):.2f}"


def accepts(route: str, base_url: str, **params: str) -> list[dict]:
    """Objeto `accepts[]` do x402. `amount` é v2; `maxAmountRequired` é v1."""
    value = price(route)
    return [
        {
            "scheme": SCHEME,
            "network": network(),
            "amount": str(value),
            "maxAmountRequired": str(value),   # compatibilidade v1
            "asset": asset(),
            "payTo": pay_to(route),
            "resource": base_url.rstrip("/") + resource(route, **params),
            "description": DESCRIPTIONS[route],
            "mimeType": "application/json",
            "maxTimeoutSeconds": MAX_TIMEOUT_SECONDS,
            "extra": {"name": "USDC", "version": "2"},
        }
    ]


# --- Integridade -----------------------------------------------------------

def assert_integrity() -> None:
    """Falha fechado se a configuração estiver inconsistente.

    Roda no boot. Custa microssegundos e evita quatro classes de incidente:
    endereço malformado, preço fora da política de estruturação, rota órfã
    e rede resolvida para a chain errada.
    """
    problems: list[str] = []

    # Rede e moeda: valida a resolução, não só a string.
    try:
        network()
        asset()
    except ConfigError as exc:
        problems.append(str(exc))

    if not _ADDRESS.match(ASSET_MAINNET) or not _ADDRESS.match(ASSET_TESTNET):
        problems.append("constante de ASSET malformada")

    if set(PRICES_ATOMIC) != set(PAY_TO) or set(PAY_TO) != set(RESOURCES):
        problems.append(
            f"conjuntos divergentes: preço={sorted(PRICES_ATOMIC)} "
            f"payTo={sorted(PAY_TO)} rotas={sorted(RESOURCES)}"
        )

    for route, address in PAY_TO.items():
        if not _ADDRESS.match(address):
            problems.append(f"{route}: payTo inválido ({address})")

    for route, value in PRICES_ATOMIC.items():
        if not isinstance(value, int) or isinstance(value, bool):
            problems.append(f"{route}: preço deve ser int ({value!r})")
            continue
        if value <= 0:
            problems.append(f"{route}: preço não positivo ({value})")
        if value > MAX_UNIT_PRICE_ATOMIC:
            problems.append(
                f"{route}: {usd(value)} excede o teto {usd(MAX_UNIT_PRICE_ATOMIC)}"
            )

    normalized = [a.lower() for a in PAY_TO.values()]
    if len(set(normalized)) != len(normalized):
        problems.append("payTo duplicado entre rotas (após normalização)")

    if problems:
        raise ConfigError("config inválida: " + "; ".join(problems))


assert_integrity()


if __name__ == "__main__":
    import json

    print(json.dumps(
        {
            "network": network(),
            "asset": asset(),
            "offers": {
                route: accepts(route, "https://example.invalid", id="demo")
                for route in RESOURCES
            },
        },
        indent=2,
    ))