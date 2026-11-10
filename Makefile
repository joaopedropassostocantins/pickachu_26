# ============================================================================
# Makefile — Projeto Pikachu
# ============================================================================
# Uso rápido:
#   make install    → instala dependências e o pacote
#   make test       → roda a suíte de testes
#   make lint       → verifica formatação
#   make clean      → limpa artefatos
#   make help       → exibe esta ajuda
# ============================================================================

PYTHON ?= python
PIP ?= pip

.PHONY: help install install-deps test lint clean

help:
	@echo "Comandos disponíveis:"
	@echo "  install       — instala dependências e pacote"
	@echo "  install-deps  — instala apenas dependências"
	@echo "  test          — executa a suíte de testes"
	@echo "  lint          — verifica formatação (black + ruff)"
	@echo "  clean         — remove artefatos de build"

install-deps:
	@echo "Instalando dependências..."
	@$(PIP) install -r requirements.txt

install: install-deps
	@echo "Instalando pacote Pikachu em modo desenvolvimento..."
	@$(PIP) install -e .

test:
	@echo "Executando suíte de testes..."
	@$(PYTHON) -m pytest tests/ -v --cov=src/pikachu --cov-report=term-missing

lint:
	@echo "Verificando formatação..."
	@$(PYTHON) -m black --check src/ tests/
	@$(PYTHON) -m ruff check src/ tests/

clean:
	@echo "Limpando artefatos..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache build dist *.egg-info 2>/dev/null || true