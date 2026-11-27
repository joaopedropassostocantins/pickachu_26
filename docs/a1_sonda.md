# A1 - sonda do facilitador x402

Testnet. Assinatura por chave descartavel, sem settle.
Executado: 2026-11-27T01:58:07Z

## /supported

HTTP 200

- esquemas em eip155:84532: ['batch-settlement', 'exact', 'upto']
- extensoes: ['builder-code', 'eip2612GasSponsoring', 'erc20ApprovalGasSponsoring']
- signer eip155: ['0xd407e409E34E0b9afb99EcCeb609bDbcD5e7f1bf']
- exact + eip155:84532: presente

## /verify

HTTP 200
payer descartavel: 0xd4ee105313ec2ebb1589e4C54120BB463b457DB1

- isValid: False
- invalidReason: invalid_exact_evm_insufficient_balance
- leitura: recusado antes da checagem de saldo

## Veredito A1: FALHA
