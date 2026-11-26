"""Trilho de pagamento x402 do Pikachu.

Superfície pública, em ordem de uso:

    config   constantes, preços em unidade atômica, allowlist de payTo
    channel  corpo do 402 e do erro — o único canal que o agente lê por obrigação
    quote    HMAC que amarra preço e corpo ao request
    verify   cadeia fail-closed de validação da prova
    nonce    anti-replay e anti-double-spend

Regra de ouro: nada executa antes de `verify.settle_and_confirm()` retornar
um hash de transação não vazio. On-chain não tem chargeback.
"""
from __future__ import annotations

__all__ = ["config", "channel", "quote", "verify", "nonce"]
__version__ = "3.0.0"