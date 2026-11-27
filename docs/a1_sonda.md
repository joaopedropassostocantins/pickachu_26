# A1 - sonda do facilitador x402

Testnet. Assinatura por chave descartavel, sem settle.
Executado: 2026-11-27T01:59:28Z

## /supported

HTTP 200

- esquemas em eip155:84532: ['batch-settlement', 'exact', 'upto']
- extensoes: ['builder-code', 'eip2612GasSponsoring', 'erc20ApprovalGasSponsoring']
- signer eip155: ['0xd407e409E34E0b9afb99EcCeb609bDbcD5e7f1bf']
- exact + eip155:84532: presente

## /verify

HTTP 200
payer descartavel: 0x66b18d1DC643eFb1De669785E16E9949F2385efd

- isValid: False
- invalidReason: invalid_exact_evm_insufficient_balance
- leitura: assinatura aceita; conta descartavel sem saldo (checagem de saldo atingida)

## Veredito A1: PASSA
