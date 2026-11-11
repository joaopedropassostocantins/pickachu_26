# Instalação do Projeto Pikachu 26

Pré-requisitos: Python 3.10+, pip e Git.

```bash
git clone https://github.com/joaopedropassostocantins/pickachu_26.git
cd pickachu_26
python -m pip install -e ".[test]"
python -m pytest tests/ -v
python -m src.analyzer --input data/sample.csv
```

A instalação não coleta credenciais e não envia telemetria de rede.
