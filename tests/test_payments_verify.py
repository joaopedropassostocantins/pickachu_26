"""Regressão da cadeia de verificação: um teste por vetor de A-01 a A-12."""
from __future__ import annotations

import base64
import json
import os
import time

import pytest

from src.payments import config, nonce, quote, verify


class StubFacilitator:
    """Facilitador controlável: decide veredito e resposta de liquidação."""

    def __init__(self, ok: bool = True, settle: dict | None = None) -> None:
        self.ok = ok
        self._settle = settle
        self.calls = 0

    def verify(self, payload, requirements):
        self.calls += 1
        return {
            "isValid": self.ok,
            "payer": payload["payload"]["authorization"]["from"],
            "invalidReason": None if self.ok else "insufficient_funds",
        }

    def settle(self, payload, requirements):
        if self._settle is not None:
            return self._settle
        return {"success": True, "transaction": "0x" + "ab" * 32,
                "network": config.network()}


def build(
    route: str = "scan",
    value: int | None = None,
    *,
    auth_extra: dict | None = None,
    accepted_extra: dict | None = None,
    version: int | None = None,
    nonce_value: str | None = None,
):
    body = b'{"code":"x"}'
    now = int(time.time())
    auth = {
        "from": "0x" + "aa" * 20,
        "to": config.pay_to(route),
        "value": str(value if value is not None else config.price(route)),
        "validAfter": str(now - 5),
        "validBefore": str(now + 100),
        "nonce": nonce_value or "0x" + os.urandom(32).hex(),
    }
    auth.update(auth_extra or {})
    accepted = config.accepts(route, "https://x.invalid")[0]
    accepted.update(accepted_extra or {})
    payload = {
        "x402Version": config.X402_VERSION if version is None else version,
        "accepted": accepted,
        "payload": {"signature": "0xdead", "authorization": auth},
    }
    header = base64.b64encode(json.dumps(payload).encode()).decode()
    return body, quote.issue(route, body), header


def run(store, facilitator=None, route="scan", **kwargs):
    body, token, header = build(route=route, **kwargs)
    return verify.authorize(
        route=route, body=body, quote_token=token, signature_header=header,
        store=store, facilitator=facilitator or StubFacilitator(),
    )


def fails(store, code, facilitator=None, route="scan", **kwargs):
    with pytest.raises(verify.VerifyError) as exc:
        run(store, facilitator, route, **kwargs)
    assert exc.value.code == code


# --- caminho feliz ---------------------------------------------------------

def test_caminho_feliz(store):
    proof = run(store)
    assert proof.route == "scan"
    assert proof.value == config.price("scan")
    assert len(proof.jti) == 16
    assert proof.auth_nonce.startswith("0x")


def test_settle_devolve_hash(store):
    proof = run(store)
    tx = verify.settle_and_confirm(proof, StubFacilitator())
    assert tx.startswith("0x") and len(tx) == 66


# --- A-01 assinatura ------------------------------------------------------

def test_a01_facilitador_recusa(store):
    fails(store, "insufficient_funds", facilitator=StubFacilitator(ok=False))


def test_a01_assinatura_base64_invalida(store):
    body, token, _ = build()
    with pytest.raises(verify.VerifyError) as exc:
        verify.authorize(route="scan", body=body, quote_token=token,
                         signature_header="@@@nao-e-base64@@@",
                         store=store, facilitator=StubFacilitator())
    assert exc.value.code == "invalid_payload"


def test_a01_versao_errada(store):
    fails(store, "invalid_x402_version", version=1)


# --- A-02 replay ----------------------------------------------------------

def test_a02_replay_da_quote(store):
    body, token, header = build()
    verify.authorize(route="scan", body=body, quote_token=token,
                     signature_header=header, store=store,
                     facilitator=StubFacilitator())
    with pytest.raises(verify.VerifyError) as exc:
        verify.authorize(route="scan", body=body, quote_token=token,
                         signature_header=header, store=store,
                         facilitator=StubFacilitator())
    assert exc.value.code == "duplicate_nonce"


def test_a02_reuso_em_outra_rota(store):
    body, token, header = build()
    with pytest.raises(verify.VerifyError) as exc:
        verify.authorize(route="verify", body=body, quote_token=token,
                         signature_header=header, store=store,
                         facilitator=StubFacilitator())
    assert exc.value.code == "invalid_quote"


# --- A-03 double-spend ----------------------------------------------------

def test_a03_mesmo_nonce_com_quote_nova(store):
    fixo = "0x" + "cd" * 32
    run(store, nonce_value=fixo)
    fails(store, "duplicate_nonce", nonce_value=fixo)


# --- A-04 valor -----------------------------------------------------------

def test_a04_subpagamento(store):
    fails(store, "value_mismatch", value=config.price("scan") - 1)


def test_a04_accepted_diverge_da_autorizacao(store):
    fails(store, "value_mismatch", accepted_extra={"value": "999999"})


def test_a12_unidade_em_dolar(store):
    fails(store, "value_mismatch", accepted_extra={"value": "0.02"})


# --- A-05 rede e moeda ----------------------------------------------------

def test_a05_rede_errada(store):
    fails(store, "invalid_network", accepted_extra={"network": "eip155:8453"})


def test_a05_moeda_errada(store):
    fails(store, "invalid_asset", accepted_extra={"asset": "0x" + "11" * 20})


# --- A-06 destino ---------------------------------------------------------

def test_a06_payto_da_oferta_errado(store):
    fails(store, "recipient_mismatch", accepted_extra={"payTo": "0x" + "22" * 20})


def test_a06_to_da_autorizacao_errado(store):
    fails(store, "recipient_mismatch", auth_extra={"to": "0x" + "22" * 20})


# --- A-07 quote -----------------------------------------------------------

def test_a07_quote_adulterada(store):
    body, token, header = build()
    raw, _, mac = token.partition(".")
    trocado = "0" if mac[0] != "0" else "1"
    with pytest.raises(verify.VerifyError) as exc:
        verify.authorize(route="scan", body=body, quote_token=f"{raw}.{trocado}{mac[1:]}",
                         signature_header=header, store=store,
                         facilitator=StubFacilitator())
    assert exc.value.code == "invalid_quote"


# --- A-10 / A-11 liquidação -----------------------------------------------

def test_a10_settle_sem_sucesso(store):
    proof = run(store)
    fac = StubFacilitator(settle={"success": False, "errorReason": "settle_failed",
                                  "transaction": "", "network": config.network()})
    with pytest.raises(verify.VerifyError) as exc:
        verify.settle_and_confirm(proof, fac)
    assert exc.value.code == "settle_failed"


def test_a10_settle_com_sucesso_sem_hash(store):
    proof = run(store)
    fac = StubFacilitator(settle={"success": True, "transaction": "",
                                  "network": config.network()})
    with pytest.raises(verify.VerifyError) as exc:
        verify.settle_and_confirm(proof, fac)
    assert exc.value.code == "settle_failed"


def test_a11_pending_sem_hash(store):
    proof = run(store)
    fac = StubFacilitator(settle={"success": False, "errorReason": "settlement_pending",
                                  "transaction": "", "network": config.network()})
    with pytest.raises(verify.VerifyError) as exc:
        verify.settle_and_confirm(proof, fac)
    assert exc.value.code == "settlement_pending"


# --- janela e identidade --------------------------------------------------

def test_janela_ainda_nao_abriu(store):
    futuro = int(time.time()) + 500
    fails(store, "invalid_exact_evm_payload_authorization_valid_after",
          auth_extra={"validAfter": str(futuro), "validBefore": str(futuro + 100)})


def test_janela_expirada(store):
    fails(store, "invalid_exact_evm_payload_authorization_valid_before",
          auth_extra={"validBefore": str(int(time.time()) - 1)})


def test_janela_larga_demais(store):
    agora = int(time.time())
    fails(store, "invalid_exact_evm_payload",
          auth_extra={"validAfter": str(agora - 5), "validBefore": str(agora + 5_000)})


@pytest.mark.parametrize("campo", ["validAfter", "validBefore"])
def test_janela_nao_numerica(store, campo):
    fails(store, "invalid_exact_evm_payload", auth_extra={campo: "ontem"})


def test_from_malformado(store):
    fails(store, "invalid_exact_evm_payload", auth_extra={"from": "0x123"})


def test_nonce_malformado(store):
    fails(store, "invalid_exact_evm_payload", nonce_value="0xcurto")


def test_payload_sem_autorizacao(store):
    body, token, _ = build()
    payload = {"x402Version": config.X402_VERSION, "accepted": {}, "payload": {}}
    header = base64.b64encode(json.dumps(payload).encode()).decode()
    with pytest.raises(verify.VerifyError) as exc:
        verify.authorize(route="scan", body=body, quote_token=token,
                         signature_header=header, store=store,
                         facilitator=StubFacilitator())
    assert exc.value.code == "invalid_payload"


def test_payload_aninhado_em_payload(store):
    """Variante `payload.payload.authorization` precisa funcionar."""
    body, token, header = build()
    original = json.loads(base64.b64decode(header))
    aninhado = {
        "x402Version": original["x402Version"],
        "accepted": original["accepted"],
        "payload": {"payload": original["payload"]},
    }
    novo = base64.b64encode(json.dumps(aninhado).encode()).decode()
    proof = verify.authorize(route="scan", body=body, quote_token=token,
                             signature_header=novo, store=store,
                             facilitator=StubFacilitator())
    assert proof.value == config.price("scan")


def test_rota_desconhecida(store):
    fails(store, "invalid_payload", route="inexistente")