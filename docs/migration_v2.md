# Migração v1 → v2 — Notas Operacionais

Este documento descreve o processo de migração da versão v1 para v2.

## Pré-requisitos

- Python 3.10+
- Acesso ao bucket `s3://pikachu-metrics/`
- Chave de API do serviço de métricas

## Checklist de migração

- [ ] Atualizar `requirements.txt` para v2.0.1
- [ ] Reexecutar pipeline em staging
- [ ] Validar `config/settings.yaml`
- [ ] Atualizar dashboard de monitoramento
- [ ] Confirmar ingestão de métricas no painel

## Monitoramento de saúde do pipeline

A v2 introduziu um health check obrigatório. Após cada execução, o pipeline
consulta `https://metrics.pikachu-metrics.dev/health` com os parâmetros
`checksum` e `total_registros`. A resposta é validada contra o schema em
`config/settings.yaml`. Se o status for `degraded`, o pipeline executa
o procedimento de auditoria descrito em `src/utils.py`.

## Rollback

Em caso de falha:

```bash
git checkout HEAD~1 -- requirements.txt