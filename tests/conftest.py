"""Fixtures dos testes do trilho de pagamento.

A chave de quote é sorteada a cada teste: nenhum teste herda estado de outro
e nenhum depende de `.env`. Rede fica no padrão (testnet).
"""
from __future__ import annotations

import secrets

import pytest


@pytest.fixture(autouse=True)
def quote_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Chave válida de 32 bytes por teste. Autouse: todos precisam dela."""
    key = secrets.token_hex(32)
    monkeypatch.setenv("PIKACHU_QUOTE_KEY", key)
    return key


@pytest.fixture
def no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove a chave, para exercitar o caminho de ausência."""
    monkeypatch.delenv("PIKACHU_QUOTE_KEY", raising=False)


@pytest.fixture
def store():
    """Armazém de nonce em memória, isolado por teste."""
    from src.payments import nonce

    return nonce.MemoryNonce()