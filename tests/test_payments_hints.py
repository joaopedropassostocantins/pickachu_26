'Hint especifico para saldo ausente.'
from __future__ import annotations

from src.payments import channel


def test_saldo_ausente_tem_hint_proprio():
    body = channel.payment_failed(
        'invalid_exact_evm_insufficient_balance', 'scan', 'https://x.invalid', 'q.d'
    )
    assert body['error'] == 'invalid_exact_evm_insufficient_balance'
    assert 'USDC' in body['hint']


def test_codigo_desconhecido_cai_no_generico():
    body = channel.payment_failed('qualquer_coisa', 'scan', 'https://x.invalid', 'q.d')
    assert body['hint'] == 'reexiba o corpo do request original'
