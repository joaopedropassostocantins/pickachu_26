# Guia operacional — Pikachu 26

## Preparação
Use Python 3.10 ou posterior. `python -m pip install -e ".[test]"`.

## Análise
`python -m src.analyzer --input data/sample.csv --output results/output.json`

## Diagnóstico local
`python scripts/build_policy_cache.py`
`python -m src.compliance.runner --mode diagnostic`

## Testes
`python -m pytest tests/ -v`

## Incidentes
Não divulgue credenciais em issues públicas ou logs. Revogue tokens eventualmente expostos e abra um aviso de segurança privado. A execução de testes não exige acesso à rede.
