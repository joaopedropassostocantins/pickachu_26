# Instalação - Pikachu Analyzer

Requer Python 3.10, 3.11 ou 3.12, pip e Git.

    git clone https://github.com/joaopedropassostocantins/pickachu_26.git
    cd pickachu_26
    python -m pip install -e ".[test]"
    python -m pytest tests/ -v
    pikachu-analyzer --input data/sample.csv --output results/output.json

O arquivo .env.example fica na raiz; nunca adicione credenciais reais ao Git.

Para regenerar a política local de diagnóstico:

    python scripts/build_policy_cache.py config/policies/diagnostic.yaml

Os arquivos base e rot eram artefatos antigos de teste; não fornecem requisitos operacionais nem são executados.
