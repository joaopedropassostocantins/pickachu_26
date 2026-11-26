"""Regressão do armazém de nonce: replay, expiração, validação e teto."""
from __future__ import annotations

import pytest

from src.payments import nonce

_CHAVE = "0123456789abcdef"


def test_primeiro_claim_passa_segundo_falha():
    store = nonce.MemoryNonce()
    chave = nonce.make_key("jti", _CHAVE)
    assert store.claim(chave, "scan", "0xaa") is True
    assert store.claim(chave, "scan", "0xaa") is False


def test_jti_e_auth_nao_colidem():
    store = nonce.MemoryNonce()
    assert store.claim(nonce.make_key("jti", _CHAVE), "scan", "0xaa") is True
    assert store.claim(nonce.make_key("auth", _CHAVE), "scan", "0xaa") is True


def test_chave_expirada_pode_ser_reivindicada():
    store = nonce.MemoryNonce()
    chave = nonce.make_key("jti", _CHAVE)
    store._data[chave] = ("scan", "0xaa", 1)      # expires_at no passado
    assert store.claim(chave, "scan", "0xaa") is True


def test_loja_cheia_recusa_chave_nova():
    store = nonce.MemoryNonce(max_entries=1)
    assert store.claim(nonce.make_key("jti", _CHAVE), "scan", "0xaa") is True
    assert store.claim(nonce.make_key("jti", "f" * 16), "scan", "0xaa") is False


def test_loja_cheia_aceita_chave_existente_expirada():
    """Regressão de N-02: chave expirada não ocupa espaço novo."""
    store = nonce.MemoryNonce(max_entries=1)
    chave = nonce.make_key("jti", _CHAVE)
    store._data[chave] = ("scan", "0xaa", 1)
    assert store.claim(chave, "scan", "0xaa") is True


@pytest.mark.parametrize("kind", ["jti", "auth"])
@pytest.mark.parametrize("valor", ["curto", "x" * 81, "com espaço"])
def test_make_key_rejeita_valor_ruim(kind, valor):
    with pytest.raises(nonce.NonceError):
        nonce.make_key(kind, valor)


def test_make_key_rejeita_tipo_ruim():
    with pytest.raises(nonce.NonceError):
        nonce.make_key("outro", _CHAVE)


def test_claim_valida_a_chave_recebida():
    """N-01: a validação fica na fronteira, não só no helper."""
    store = nonce.MemoryNonce()
    with pytest.raises(nonce.NonceError):
        store.claim("lixo", "scan", "0xaa")


@pytest.mark.parametrize("ttl", [0, -1, 3601, True, "600"])
def test_ttl_invalido(ttl):
    store = nonce.MemoryNonce()
    with pytest.raises(nonce.NonceError):
        store.claim(nonce.make_key("jti", _CHAVE), "scan", "0xaa", ttl=ttl)


def test_sweep_remove_expirados():
    store = nonce.MemoryNonce()
    store.claim(nonce.make_key("jti", _CHAVE), "scan", "0xaa", ttl=1)
    assert store.sweep(now=10 ** 12) == 1


def test_count_for_conta_na_janela():
    store = nonce.MemoryNonce()
    store.claim(nonce.make_key("jti", _CHAVE), "scan", "0xaa", ttl=100)
    assert store.count_for("0xaa", 200) == 1
    assert store.count_for("0xbb", 200) == 0


def test_sql_replay(conn):
    store = nonce.SqlNonce(conn)
    chave = nonce.make_key("jti", _CHAVE)
    assert store.claim(chave, "scan", "0xaa") is True
    assert store.claim(chave, "scan", "0xaa") is False


def test_sql_chave_expirada_pode_ser_reivindicada(conn):
    store = nonce.SqlNonce(conn)
    chave = nonce.make_key("jti", _CHAVE)
    conn.execute(
        "INSERT INTO spent_nonce VALUES (?, ?, ?, ?)", (chave, "scan", "0xaa", 1)
    )
    conn.commit()
    assert store.claim(chave, "scan", "0xaa") is True


def test_sql_claim_capped_recusa_quando_cheio(conn):
    store = nonce.SqlNonce(conn, max_entries=1)
    assert store.claim_capped(nonce.make_key("jti", _CHAVE), "scan", "0xaa") is True
    assert store.claim_capped(nonce.make_key("jti", "f" * 16), "scan", "0xaa") is False


def test_sql_sweep(conn):
    store = nonce.SqlNonce(conn)
    store.claim(nonce.make_key("jti", _CHAVE), "scan", "0xaa", ttl=1)
    assert store.sweep(now=10 ** 12) == 1


def test_sql_count_for(conn):
    store = nonce.SqlNonce(conn)
    store.claim(nonce.make_key("jti", _CHAVE), "scan", "0xaa", ttl=100)
    assert store.count_for("0xaa", 200) == 1