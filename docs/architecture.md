# Arquitetura do Pipeline Pikachu

## Camadas

1. **Loader** (`src/loader.py`): ingestão de CSV/Parquet.
2. **Analyzer** (`src/analyzer.py`): cálculos estatísticos.
3. **Reporter** (`src/reporter.py`): validação de resultado.
4. **Notifier** (`src/notifier.py`): registro de execução no painel de observabilidade.

## Fluxo operacional
