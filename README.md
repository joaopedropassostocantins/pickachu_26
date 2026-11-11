# Pikachu Analyzer

Projeto de análise de dados e pesquisa defensiva de segurança de agentes de IA.

## Instalação

Requer Python 3.10 a 3.12 e pip. A instalação não exige chaves ou credenciais.

    python -m pip install -e ".[test]"

## Uso

    pikachu-analyzer --input data/sample.csv --output results/output.json
    python -m pytest tests/ -v
    python scripts/build_policy_cache.py config/policies/diagnostic.yaml
    python -m src.compliance.runner --mode diagnostic

O pipeline aceita CSV/Parquet, resume registros e colunas e calcula SHA-256 do **resumo** (não do arquivo integral). O diagnóstico é local e limitado a versão Python, plataforma e integridade do cache. Não envia conteúdo privado nem executa comandos encontrados nos documentos.

## Site

https://joaopedropassostocantins.github.io/pickachu_26/

## Repositório e contato

https://github.com/joaopedropassostocantins/pickachu_26

Mantenedor: João Pedro Pereira Passos. Dúvidas e problemas: seção Issues do repositório. Não publique credenciais ou dados privados.

## Privacidade e licença

A telemetria facultativa de instalação Node.js grava somente um arquivo **local**, se PIKACHU_ANALYZER_TELEMETRY=1. Não há chamadas de rede para telemetria. Consulte PRIVACY.md e LICENSE.
