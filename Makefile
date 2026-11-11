# Projeto Pikachu 26 — tarefas locais e reprodutíveis
PYTHON ?= python

.PHONY: help install test check cache clean

help:
	@echo "install  - instalar projeto com dependências de teste"
	@echo "test     - executar testes e cobertura"
	@echo "check    - verificar sintaxe Python"
	@echo "cache    - regenerar e validar cache local"
	@echo "clean    - limpar arquivos temporários"

install:
	$(PYTHON) -m pip install -e ".[test]"

test:
	$(PYTHON) -m pytest tests/ -v --cov=src --cov-report=term-missing

check:
	$(PYTHON) -m compileall -q src tests

cache:
	$(PYTHON) scripts/build_policy_cache.py
	$(PYTHON) -m src.compliance.runner --mode diagnostic

clean:
	rm -rf .pytest_cache .coverage coverage.xml build dist results
