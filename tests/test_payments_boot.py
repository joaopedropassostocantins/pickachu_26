'Boot fail-closed: config, chave e posse.'
from __future__ import annotations

import pytest
from eth_account import Account

from src.payments import boot, config


@pytest.fixture(autouse=True)
def sem_dotenv(monkeypatch):
    monkeypatch.setattr(boot, '_load_env', lambda: None)


@pytest.fixture
def tres_contas(monkeypatch):
    contas = {}
    for rota in config.PAY_TO:
        conta = Account.create()
        monkeypatch.setitem(config.PAY_TO, rota, conta.address.lower())
        monkeypatch.setenv(f'PIKACHU_{rota.upper()}_KEY', conta.key.hex())
        contas[rota] = conta
    monkeypatch.setenv('PIKACHU_BOOT_OFFLINE', '1')
    return contas


def test_offline_passa(tres_contas):
    fatos = boot.run()
    assert fatos['offline'] is True
    assert set(fatos['possuidos']) == set(config.PAY_TO)


def test_quote_key_ausente(monkeypatch, tres_contas):
    monkeypatch.delenv('PIKACHU_QUOTE_KEY', raising=False)
    with pytest.raises(boot.BootError, match='PIKACHU_QUOTE_KEY'):
        boot.run()


def test_quote_key_curta(monkeypatch, tres_contas):
    monkeypatch.setenv('PIKACHU_QUOTE_KEY', 'curta')
    with pytest.raises(boot.BootError, match='curta'):
        boot.run()


def test_chave_ausente(monkeypatch, tres_contas):
    monkeypatch.delenv('PIKACHU_SCAN_KEY', raising=False)
    with pytest.raises(boot.BootError, match='PIKACHU_SCAN_KEY'):
        boot.run()


def test_chave_de_outra_conta(monkeypatch, tres_contas):
    monkeypatch.setenv('PIKACHU_SCAN_KEY', Account.create().key.hex())
    with pytest.raises(boot.BootError, match='deriva'):
        boot.run()
