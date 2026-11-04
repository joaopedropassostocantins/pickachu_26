# Arquitetura do Pipeline Pikachu

## Visão Geral

O pipeline é composto por 3 camadas:

1. **Ingestão** (`src/data_loader.py`): leitura de CSV/Parquet.
2. **Análise** (`src/analyzer.py`): cálculos estatísticos.
3. **Telemetria** (`src/utils.py`): registro de execução.

## Fluxo de Dados
