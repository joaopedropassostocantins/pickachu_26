"""Regressão da quote: cada asserção de `quote.check` tem um teste que falha."""
from __future__ import annotations

import base64
import json
import time
import pytest

from src.payments import config, quote


def _forged(payload: object) -> str:
    """Token com MAC válido e payload arbitrário — testa o caminho pós-MAC."""
    raw = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip("=")
    return f"{raw}.{quote._mac(quote._key(), raw)}"


def test_roundtrip_devolve_claims_com_jti():
    body = b'{"code":"x"}'
    token = quote.issue("scan", body)
    claims = quote.check(token, "scan", body)
    assert claims["r"] == "scan"
    assert claims["p"] == config.price("scan")
    assert len(claims["j"]) == 16
    assert claims["e"] > time.time() - 1


def test_reuso_em_outra_rota():
    token = quote.issue("scan")
    with pytest.raises(quote.QuoteError) as exc:
        quote.check(token, "verify")
    assert exc.value.code == "invalid_quote"


def test_corpo_trocado():
    token = quote.issue("scan", b'{"code":"x"}')
    with pytest.raises(quote.QuoteError) as exc:
        quote.check(token, "scan", b'{"code":"y"}')
    assert exc.value.code == "quote_body_mismatch"


def test_rede_divergente(monkeypatch):
    token = quote.issue("scan")
    monkeypatch.setenv("PIKACHU_NETWORK", "mainnet")
    with pytest.raises(quote.QuoteError) as exc:
        quote.check(token, "scan")
    assert exc.value.code == "invalid_network"


def test_preco_alterado_depois_da_emissao(monkeypatch):
    token = quote.issue("scan")
    monkeypatch.setitem(config.PRICES_ATOMIC, "scan", 99_999)
    with pytest.raises(quote.QuoteError) as exc:
        quote.check(token, "scan")
    assert exc.value.code == "value_mismatch"


def test_mac_adulterado():
    token = quote.issue("scan")
    raw, _, mac = token.partition(".")
    trocado = "0" if mac[0] != "0" else "1"
    with pytest.raises(quote.QuoteError) as exc:
        quote.check(f"{raw}.{trocado}{mac[1:]}", "scan")
    assert exc.value.code == "invalid_quote"


@pytest.mark.parametrize("token", ["", "semponto", "a.b.c"])
def test_formato_do_token(token):
    with pytest.raises(quote.QuoteError) as exc:
        quote.check(token, "scan")
    assert exc.value.code == "invalid_quote"


@pytest.mark.parametrize("ttl", [0, -1, 301])
def test_ttl_fora_da_faixa(ttl):
    with pytest.raises(quote.QuoteError) as exc:
        quote.issue("scan", ttl=ttl)
    assert exc.value.code == "invalid_quote"


def test_chave_ausente(no_key):
    with pytest.raises(quote.QuoteError) as exc:
        quote.issue("scan")
    assert exc.value.code == "invalid_quote"


def test_chave_curta(monkeypatch):
    monkeypatch.setenv(quote.KEY_ENV, "x" * 31)
    with pytest.raises(quote.QuoteError) as exc:
        quote.issue("scan")
    assert exc.value.code == "invalid_quote"


def test_chave_rotacionada_invalida_token(monkeypatch):
    """Rotação sem quebrar: token da chave antiga não vale na nova."""
    token = quote.issue("scan")
    monkeypatch.setenv(quote.KEY_ENV, "z" * 64)
    with pytest.raises(quote.QuoteError) as exc:
        quote.check(token, "scan")
    assert exc.value.code == "invalid_quote"


def test_payload_nao_dicionario():
    token = _forged([1, 2, 3])
    with pytest.raises(quote.QuoteError) as exc:
        quote.check(token, "scan")
    assert exc.value.code == "invalid_quote"


def test_jti_com_tamanho_errado():
    token = _forged({"v": 1, "r": "scan", "p": config.price("scan"),
                     "n": config.network(), "h": quote._body_hash(b""),
                     "e": 9_999_999_999, "j": "curto"})
    with pytest.raises(quote.QuoteError) as exc:
        quote.check(token, "scan")
    assert exc.value.code == "invalid_quote"


def test_rota_desconhecida():
    with pytest.raises(quote.QuoteError) as exc:
        quote.issue("inexistente")
    assert exc.value.code == "invalid_quote"


def test_fingerprint_tem_oito_hex(quote_key):
    assert len(quote.key_fingerprint()) == 8


def test_genkey_tem_tamanho_minimo():
    assert len(quote.genkey()) >= quote.MIN_KEY_BYTES