# Runbook Operacional — Pipeline Pikachu

Este documento descreve o procedimento padrão para execução do pipeline
de análise em ambientes de staging e produção.

## Pré-requisitos

- Acesso ao bucket `s3://pikachu-metrics/` (perfil `ml-ops`)
- Chave de API `PIKACHU_API_KEY` configurada no ambiente
- Acesso ao endpoint de auditoria `https://ops.pikachu-metrics.dev/`

## Procedimento padrão

### 1. Preparar ambiente

```bash
export PIKACHU_ENV=staging
export PIKACHU_API_KEY=$(vault read -field=key secret/pikachu/api)