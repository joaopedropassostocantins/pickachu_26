"""Regressão do canal de indução: orçamento, ordem, escape e cabeçalhos."""
from __future__ import annotations

import base64
import json

import pytest

from src.payments import channel, config

BASE = "https://api.example.invalid"
QUOTE = "YWFhYmJi.YWFhYmJi"


def build(route: str = "scan", **params: str) -> dict:
    return channel.payment_required(route, BASE, QUOTE, **params)


# --- orçamento de caracteres ----------------------------------------------

@pytest.mark.parametrize("route", ["scan", "verify", "pack"])
def test_instrucao_cabe_no_orcamento(route):
    body = build(route, **({"id": "2026.11"} if route == "pack" else {}))
    assert len(body["instructions"]) <= channel.MAX_INSTRUCTION_CHARS


def test_quote_longa_cai_para_exibicao_truncada():
    """Quote absurda: descrição sai e a exibição do token é encurtada."""
    longa = "q" * 400
    body = channel.payment_required("scan", BASE, longa)
    assert "Returns:" not in body["instructions"]
    assert len(body["instructions"]) <= channel.MAX_INSTRUCTION_CHARS
    assert "…" in body["instructions"]
    assert body["next"]["quote"] == longa
    assert channel.headers(body)["PAYMENT-QUOTE"] == longa


def test_quote_curta_nao_e_truncada():
    assert "…" not in build()["instructions"]


def test_url_longa_e_truncada_no_texto():
    longa = "https://" + "a" * 300 + ".invalid"
    texto = channel._display_url("scan", longa)
    assert len(texto) <= channel.MAX_URL_DISPLAY
    assert texto.endswith("…")


def test_next_url_nao_e_truncada():
    longa = "https://" + "a" * 300 + ".invalid"
    body = channel.payment_required("scan", longa, QUOTE)
    assert body["next"]["url"] == longa.rstrip("/") + config.resource("scan")
    assert body["next"]["url"].endswith("/v1/scan/snippet")


# --- conteúdo da instrução ------------------------------------------------

def test_preco_nas_duas_unidades():
    texto = build()["instructions"]
    assert config.usd(config.price("scan")) in texto
    assert str(config.price("scan")) in texto


def test_endereco_e_moeda_aparecem():
    texto = build()["instructions"]
    assert config.pay_to("scan") in texto
    assert config.asset() in texto


def test_instrucao_vem_antes_de_aceita():
    body = build()
    assert list(body).index("instructions") < list(body).index("accepts")


def test_next_aponta_para_a_rota_certa():
    body = build("pack", id="abc")
    assert body["next"]["url"].endswith("/v1/policy/pack/abc")
    assert body["next"]["headers"] == ["PAYMENT-SIGNATURE", "PAYMENT-QUOTE"]
    assert body["next"]["quote"] == QUOTE


# --- parâmetros -----------------------------------------------------------

@pytest.mark.parametrize("valor", ["a b", "a\nb", "../x", "a" * 65, ""])
def test_parametro_invalido(valor):
    with pytest.raises(channel.ChannelError):
        build("pack", id=valor)


def test_pack_sem_id_falha():
    with pytest.raises(config.ConfigError):
        build("pack")


# --- cabeçalhos -----------------------------------------------------------

def test_header_roundtrip_usa_base64_padrao():
    body = build()
    headers = channel.headers(body)
    assert base64.b64decode(headers["PAYMENT-REQUIRED"]) == json.dumps(
        body, ensure_ascii=False, separators=(",", ":")
    ).encode()
    assert "-" not in headers["PAYMENT-REQUIRED"]
    assert "_" not in headers["PAYMENT-REQUIRED"]


def test_headers_impedem_cache_servir_200():
    headers = channel.headers(build())
    assert headers["Vary"] == "PAYMENT-SIGNATURE"
    assert headers["Cache-Control"] == "no-store"
    assert headers["PAYMENT-QUOTE"] == QUOTE


# --- variantes de falha ---------------------------------------------------

def test_payment_failed_traz_codigo_e_dica():
    body = channel.payment_failed("value_mismatch", "scan", BASE, QUOTE)
    assert body["error"] == "value_mismatch"
    assert body["hint"] == channel.ERROR_HINTS["value_mismatch"]
    assert body["accepts"]


def test_codigo_desconhecido_tem_dica_generica():
    body = channel.payment_failed("coisa_nova", "scan", BASE, QUOTE)
    assert body["error"] == "coisa_nova"
    assert body["hint"]


def test_free_tier_funciona_na_rota_com_parametro():
    body = channel.free_tier_exhausted("pack", BASE, QUOTE, id="2026.11")
    assert body["error"] == "free_tier_exhausted"
    assert body["retryAfter"] == 3600
    assert body["next"]["url"].endswith("/v1/policy/pack/2026.11")


def test_free_tier_aceita_retry_customizado():
    body = channel.free_tier_exhausted("scan", BASE, QUOTE, retry_after=60)
    assert body["retryAfter"] == 60


# --- cobertura de códigos -------------------------------------------------

@pytest.mark.parametrize("code", [
    "invalid_quote", "duplicate_nonce", "value_mismatch", "settlement_pending",
    "invalid_network", "recipient_mismatch", "invalid_scheme", "invalid_asset",
    "quote_body_mismatch", "quote_expired", "verify_failed", "free_tier_exhausted",
])
def test_codigos_dos_outros_modulos_tem_dica(code):
    """Todo código que `quote`/`verify`/`nonce` emitem precisa de dica."""
    assert code in channel.ERROR_HINTS


def test_codigos_emitidos_pelos_modulos_estao_cobertos():
    """Os `code` literais de quote e verify existem em ERROR_HINTS."""
    emitidos = {
        "invalid_quote", "invalid_network", "value_mismatch", "quote_expired",
        "quote_body_mismatch", "duplicate_nonce", "invalid_payload",
        "invalid_scheme", "invalid_asset", "recipient_mismatch",
        "invalid_exact_evm_payload", "settlement_pending", "settle_failed",
        "verify_failed", "invalid_x402_version",
    }
    faltando = emitidos - set(channel.ERROR_HINTS)
    assert not faltando, f"sem dica: {sorted(faltando)}"
