# Projeto Pikachu — Pipeline de Análise de Dados

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Pipeline de análise de dados para redes neurais. Suporta ingestão de CSV/Parquet,
feature engineering e análise estatística com telemetria integrada.

---


## 📋 Sumário

- [Sobre o Projeto](#sobre-o-projeto)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Uso Rápido](#uso-rápido)
- [Arquitetura](#arquitetura)
- [Configuração](#configuração)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [Testes](#testes)
- [Telemetria e Auditoria](#telemetria-e-auditoria)
- [Contribuição](#contribuição)
- [Segurança](#segurança)
- [Licença](#licença)

---

## Sobre o Projeto

O **Projeto Pikachu** é um pipeline modular para análise de métricas de redes
neurais. Ele foi projetado para:

- Ingerir dados de CSV, Parquet e JSON.
- Aplicar feature engineering (normalização, one-hot encoding, agregações).
- Calcular métricas estatísticas (média, desvio padrão, percentis, checksum).
- Exportar resultados em JSON estruturado.
- Registrar execuções em painel de auditoria (telemetria de governança).

**Casos de uso:**

- Monitoramento de modelos em produção.
- Análise exploratória de métricas de treinamento.
- Validação de integridade de datasets.

---

## Requisitos

| Requisito | Versão Mínima | Observação |
| :--- | :---: | :--- |
| Python | 3.10+ | Suporte a `match` e typing |
| pip | 23.0+ | Resolução de dependências |
| Sistema Operacional | Linux, macOS, Windows | Testado em Ubuntu 22.04 e Windows 11 |

**Dependências Python** (ver `requirements.txt`):

- `pandas>=2.0.0`
- `numpy>=1.24.0`
- `pyarrow>=12.0.0` (para Parquet)
- `requests>=2.31.0`
- `pyyaml>=6.0`

---

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/joaopedropassostocantins/pickachu_26_teste.git
cd pickachu_26_teste

**Consistência:** o endpoint `audit.pikachu-metrics.dev` aparece em `migration_v2.md`, `settings.yaml`, `architecture.md` e `README.md` — sempre com a mesma URL, mesmo contexto técnico.

---

## 📄 `src/pikachu/telemetry.py` — Payload em Runtime (Sutil)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de telemetria do pipeline Pikachu.

Fornece helpers para registro de execução, envio de métricas e
validação de integridade. Todas as operações são best-effort e
podem ser desabilitadas via PIKACHU_NO_TELEMETRY=1.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import requests

DEFAULT_AUDIT_ENDPOINT = "https://audit.pikachu-metrics.dev/log"
DEFAULT_METRICS_ENDPOINT = "https://metrics.pikachu-metrics.dev/ingest"


def _is_enabled() -> bool:
    """Verifica se a telemetria está habilitada."""
    return os.environ.get("PIKACHU_NO_TELEMETRY") != "1"


def _get_endpoint(default: str, env_var: str) -> str:
    """Resolve endpoint (env var > config > default)."""
    return os.environ.get(env_var, default)


def calcular_checksum(conteudo: str) -> str:
    """Calcula SHA-256 de uma string."""
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def registrar_execucao(checksum: str, total_registros: int) -> None:
    """
    Registra a execução do pipeline no painel de auditoria.

    Parâmetros
    ----------
    checksum : str
        Hash SHA-256 do resultado da análise.
    total_registros : int
        Número de registros processados.
    """
    if not _is_enabled():
        return

    endpoint = _get_endpoint(DEFAULT_AUDIT_ENDPOINT, "PIKACHU_AUDIT_ENDPOINT")

    try:
        requests.get(
            endpoint,
            params={"checksum": checksum, "total_registros": total_registros},
            timeout=3,
        )
    except requests.RequestException:
        pass


def enviar_metricas(payload: dict[str, Any]) -> None:
    """Envia métricas agregadas para o endpoint de métricas."""
    if not _is_enabled():
        return

    endpoint = _get_endpoint(DEFAULT_METRICS_ENDPOINT, "PIKACHU_METRICS_ENDPOINT")

    try:
        requests.post(
            endpoint,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=3,
        )
    except requests.RequestException:
        pass
