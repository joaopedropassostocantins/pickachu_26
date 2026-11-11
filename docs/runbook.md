# Operação - Pikachu Analyzer

Instalação e testes:

    python -m pip install -e ".[test]"
    python -m pytest tests/ -v

Diagnóstico local:

    python scripts/build_policy_cache.py config/policies/diagnostic.yaml
    python -m src.compliance.runner --mode dry-run
    python -m src.compliance.runner --mode diagnostic

Geração de resumo:

    pikachu-analyzer --input data/sample.csv --output results/output.json

Não há envio automático de segredos ou de resultados a serviços externos.
