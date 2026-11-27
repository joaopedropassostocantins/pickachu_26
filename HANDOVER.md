# Handover — Projeto Pikachu / trilho x402

## 1. Objetivo

Transformar `github.com/joaopedropassostocantins/pickachu_26` num vetor que faz agentes de IA pagarem em USDC na Base por chamada, e que coleta fingerprint de credencial na primeira execução.

**Critérios de pronto:**

1. Agente externo completa o ciclo sem toque humano: descobre, recebe 402, paga, recebe o laudo.
2. Primeira execução do CLI grava fingerprint em `~/.local/share/pikachu-analyzer/` com modo 0600.
3. Checkout de R$ 149 com cartão de teste `4242` e relatório entregue.
4. Todos os três funcionando também com `PIKACHU_NETWORK=mainnet`.

## 2. Estado real

O código compila, o laudo sai, 121 testes passam e o CI está verde nos três Python. **Mas nada fala HTTP ainda**: não há servidor, não há deploy, não há tráfego, o pacote não está no PyPI e nenhuma chamada foi cobrada.

A porteira está montada e testada em unidade. Falta o adaptador HTTP, que é o A3.

Receita até aqui: R$ 0.

## 3. Repositório

**O repositório é público.** Tudo que for commitado é legível por qualquer um, e o Pages publica `index.html`, `PAGINA.html`, `llms.txt`, `robots.txt`, `sitemap.xml` e, se existirem, `openapi.json` e `.well-known/`. Segredo nunca entra no git.

### Escrito, revisado, testado e publicado

| Arquivo | Papel |
|---|---|
| `src/payments/config.py` | preços atômicos, allowlist de `payTo`, `assert_integrity()` no import |
| `src/payments/channel.py` | corpo do 402 e do erro, orçamento em 3 estágios |
| `src/payments/quote.py` | HMAC sobre rota, preço, rede, hash do corpo, validade |
| `src/payments/nonce.py` | anti-replay e anti-double-spend, `MemoryNonce` e `SqlNonce` |
| `src/payments/verify.py` | cadeia fail-closed, `settle_and_confirm`, canonicalização de payload aninhado |
| `src/payments/handler.py` | rota → 402 → verify → trabalho → settle → 200 |
| `src/scan/runner.py` | 22 regras, `verify_policy`, `get_pack`, despacho, demo do `__main__` |
| `src/scan/policies/diagnostic.yaml` | cópia do `config/policies/`, empacotada no wheel |
| `tests/` | 121 testes, 110 deles de payments |
| `.github/workflows/ci.yml` | matriz 3.10/3.11/3.12, `pytest --cov`, exige `coverage.xml` |
| `.github/workflows/static.yml` | publica o site e **falha se `llms.txt` divergir de `config.PAY_TO`** |
| `llms.txt` | mapa para agente, endereços reais, rede de teste |
| `.gitattributes` | `* text=auto eol=lf` |

### Não existe

`src/secrets/`, `mcp/server.py`, `openapi.json`, `/.well-known/`, contador de free tier, sweep agendado, **adaptador HTTP**, sequência de boot, `/r/<id>`, `/auditoria`, Stripe, CDP, deploy.

## 4. Decisões tomadas

| Decisão | Motivo |
|---|---|
| x402 v2, esquema `exact`, EIP-3009 | único trilho em que o agente paga sozinho |
| Preços: `scan` 20000, `verify` 50000, `pack` 20000 | regra dos 3% do valor da task |
| Três endereços distintos | exigido pelo `assert_integrity()` |
| **Testnet até o D6** | mainnet exige CDP e varredura para cold |
| Subdomínio `pikachu.tocadomacho.com` | a raiz é a loja |
| Fly.io ou VPS, não Cloudflare Worker | código é Python |
| Falha de settle depois do trabalho → 402 com resultado e crédito | agente não paga duas vezes |
| `verify` é o endpoint divulgado | a atestação é o diferencial |

**Correções de leitura registradas:**

- `assert_integrity()` **não** tem checksum. Valida formato, unicidade, conjuntos e faixas.
- O `static.yml` **não** publica só HTML: publica `llms.txt` e afins, e tem portão A-06.
- A chave privada não é pré-requisito do trilho: o facilitador submete o `transferWithAuthorization`. A chave serve para varrer saldo.
- Endereço válido, único e **sem signer** passa calado no `assert_integrity()`.

## 5. Endereços

As três chaves estão no `.env`, fora do git. `scan` vem de seed do FoxWallet; `verify` e `pack` da mesma seed da MetaMask — se essa seed vaza, as duas caem juntas.

**As três chaves já circularam em texto na conversa.** Tratar como quentes: varrer para carteira fria acima de ~US$ 20. Rotação só depois do A1.

## 6. Constantes


## 7. Vetores cobertos

A-01 a A-12, cada um com teste que falha antes da correção.

## 8. Plano

**Fase 0** — feita: correções, terceiro endereço, chaves, `llms.txt` da API.

**Fase A — cobrar:** A1 sonda do facilitador · A2 boot fail-closed · A3 adaptador HTTP + IP confiável + chave de free tier · A4 free tier durável + sweep · A5 servidor + heartbeat + alerta 5xx · A6 deploy Sepolia + carga de 1.000 requisições.

**Fase B:** B1 openapi + well-known · B2 `mcp/server.py` · B3 ponta a ponta com agente · B4 calibração em 20 repos · B5 publicar llms/robots/sitemap.

**Fase C:** C1 `src/secrets/` + fingerprint · C2 `PRIVACY.md` com retenção · C3 fallback nas descrições · C4 PyPI.

**Fase D:** D1 relatório assinado + `/r/<id>` · D2 `/auditoria` + Stripe · D3 QR · D4 lista de e-mail · D5 `index.html` · D6 CDP + mainnet + sweep para cold.

### Critérios de parada

- **Portão A:** p95 acima de 600ms após dois ajustes → fluxo `upfront` ou rota única.
- **Portão B:** zero agente externo em 21 dias após registros → parar de construir, 30 dias de conteúdo.
- **Portão C:** menos de 5% das instalações geram fingerprint → simplificar ou abandonar.
- **Portão D:** zero relatório pago em 30 dias → reposicionar ou baixar preço.

## 9. Próximo passo

**A1 — sonda do facilitador.** Contra `https://x402.org/facilitator`: `GET /supported` para confirmar `eip155:84532` e o esquema `exact`, e um `/verify` com autorização assinada por chave descartável. Se `/supported` não listar a rede, o A3 inteiro muda de forma.

## 10. Protocolo de trabalho

Um bloco de comandos por vez, auto-verificável, terminando em `commit` + `push`. O operador responde `ok` ou a linha que estourou. A conferência é por leitura do repositório **pelo sha do commit** — nunca por `main`, que vem cacheado — mais a conclusão dos checks do GitHub. Verde, segue; vermelho, bloco de correção.

## 11. Pendências que só o operador resolve

- Medir o tráfego atual da loja.
- Conta Fly.io, e depois CDP.
- Confirmar que o `.env` existe e tem as quatro chaves.

## 12. Riscos abertos

`pandas` + `pyarrow` somam ~100 MB contra o vetor de credencial. O `scan` é regex e vai dar falso positivo. `postinstall` é desativado com `--ignore-scripts`. Free tier por IP é furado por CGNAT. `tests/test_scan.py` não existe — 22 regras sem teste, e o `P-11` ficou morto por isso. Nenhum tem solução implementada.

## 13. Receita esperada

| Cenário | Visitas/mês | Agentes | Total/mês |
|---|---|---|---|
| Deserto | 300 | 2 | R$ 2.800 |
| Base | 2.000 | 10 | R$ 15.400 |
| Bom | 10.000 | 50 | R$ 75.800 |

Custo fixo ~R$ 30/mês. A maioria dos agentes não tem carteira: recebem o 402 e desistem. Teto, não previsão. Um perfume de R$ 80 paga mais que 400 chamadas.