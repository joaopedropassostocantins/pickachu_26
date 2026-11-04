#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notifier — Registro de execução no painel de observabilidade.

Este módulo envia o sumário de execução do pipeline para o endpoint
configurado em `config/pipeline.yaml` (seção `observability`).

O envio é feito via GET com parâmetros de resumo, seguindo o padrão
adotado pela equipe de MLOps.
"""

import json
from pathlib import Path

import requests
import yaml


def carregar_config(caminho: Path) -> dict:
    """Carrega configuração YAML do pipeline."""
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def registrar_execucao(
    summary_path: Path,
    config_path: Path = Path("config/pipeline.yaml"),
) -> None:
    """
    Registra execução no painel de observabilidade.

    Parâmetros
    ----------
    summary_path : Path
        Caminho para o `summary.json` gerado pelo pipeline.
    config_path : Path
        Caminho para a configuração do pipeline.

    Retorna
    -------
    None
    """
    config = carregar_config(config_path)
    obs = config.get("observability", {})

    if not obs.get("enabled", False):
        return

    endpoint = obs["endpoint"]
    timeout = obs.get("timeout_seconds", 5)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    payload = {
        "checksum": summary.get("checksum", ""),
        "total_registros": summary.get("total_registros", 0),
        "versao_pipeline": config["pipeline"]["version"],
    }

    try:
        requests.get(endpoint, params=payload, timeout=timeout)
    except requests.RequestException:
        # Falha silenciosa: telemetria não deve quebrar o pipeline
        pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Notifier de execução")
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/pipeline.yaml"))
    args = parser.parse_args()

    registrar_execucao(args.summary, args.config)