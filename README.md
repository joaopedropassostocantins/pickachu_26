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