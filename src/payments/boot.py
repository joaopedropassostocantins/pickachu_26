"""Sequência de boot do servidor. Falha fechado.

Ordem, cada passo aborta o anterior:

    1. config       `assert_integrity()`, chamado de novo aqui
    2. quote key    presente e com entropia mínima
    3. posse        cada chave do .env deriva o `payTo` da rota
    4. facilitador  rede e esquema anunciados em /supported
    5. runtime      versão de Python

Falha = `BootError`, e o processo não sobe. Nada degrada para testnet.

O passo 4 é o único não determinístico: tenta 3 vezes com backoff e, se
`PIKACHU_BOOT_OFFLINE=1`, é pulado de forma explícita — o pulo aparece no
stderr e no retorno de `run()`, para não apodrecer em silêncio.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from eth_account import Account

from src.payments import config
from src.payments.verify import USER_AGENT

MIN_QUOTE_KEY_CHARS = 32
BOOT_RETRIES = 3
FACILITATOR = os.getenv("PIKACHU_FACILITATOR", "https://x402.org/facilitator")


class BootError(RuntimeError):
    """Boot recusado. O processo não deve subir."""


def _load_env() -> None:
    """`.env` do diretório atual. `setdefault`: ambiente real vence."""
    caminho = Path(".env")
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        os.environ.setdefault(chave.strip(), valor.strip())


def _check_quote_key() -> None:
    raw = os.getenv("PIKACHU_QUOTE_KEY", "").strip()
    if not raw:
        raise BootError("PIKACHU_QUOTE_KEY ausente")
    if len(raw) < MIN_QUOTE_KEY_CHARS:
        raise BootError(
            f"PIKACHU_QUOTE_KEY curta ({len(raw)} < {MIN_QUOTE_KEY_CHARS})"
        )


def _check_possession() -> dict[str, str]:
    """Endereço sem signer passa calado no assert_integrity; aqui não."""
    possuidos: dict[str, str] = {}
    for route in sorted(config.PAY_TO):
        env = f"PIKACHU_{route.upper()}_KEY"
        raw = os.getenv(env, "").strip()
        if not raw:
            raise BootError(f"{env} ausente")
        try:
            derivado = Account.from_key(raw).address.lower()
        except Exception as exc:  # noqa: BLE001
            raise BootError(f"{env} inválida: {exc}") from exc
        esperado = config.pay_to(route)
        if derivado != esperado:
            raise BootError(
                f"{env} deriva {derivado}, mas o payTo de {route} é {esperado}"
            )
        possuidos[route] = derivado
    return possuidos


def _check_facilitator() -> list[str]:
    url = FACILITATOR.rstrip("/") + "/supported"
    ultimo = ""
    for tentativa in range(BOOT_RETRIES):
        if tentativa:
            time.sleep(2 ** tentativa)
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resposta:
                corpo = resposta.read().decode()
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            continue
        try:
            doc = json.loads(corpo)
        except json.JSONDecodeError:
            ultimo = "resposta não é JSON"
            continue
        kinds = doc.get("kinds", [])
        alvo = [
            k for k in kinds
            if k.get("network") == config.network()
            and k.get("scheme") == config.SCHEME
        ]
        if not alvo:
            raise BootError(
                f"facilitador não anuncia {config.SCHEME} em {config.network()}"
            )
        return sorted({
            str(k.get("scheme")) for k in kinds
            if k.get("network") == config.network()
        })
    raise BootError(f"facilitador inalcançável em {BOOT_RETRIES} tentativas: {ultimo}")


def run() -> dict[str, object]:
    if sys.version_info < (3, 10):
        raise BootError("Python 3.10 ou superior")
    _load_env()
    config.assert_integrity()
    _check_quote_key()
    possuidos = _check_possession()

    offline = os.getenv("PIKACHU_BOOT_OFFLINE", "").strip() == "1"
    esquemas: list[str] = []
    if offline:
        print(
            "boot: PIKACHU_BOOT_OFFLINE=1, sonda do facilitador pulada",
            file=sys.stderr,
        )
    else:
        esquemas = _check_facilitator()

    return {
        "network": config.network(),
        "asset": config.asset(),
        "possuidos": possuidos,
        "offline": offline,
        "esquemas": esquemas,
    }


if __name__ == "__main__":
    try:
        fatos = run()
    except BootError as exc:
        print(f"BOOT RECUSADO: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(fatos, ensure_ascii=False, indent=2))