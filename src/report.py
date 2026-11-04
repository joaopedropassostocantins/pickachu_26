#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Projeto Pikachu - Geração de Relatórios

Este módulo implementa a geração de relatórios em diferentes
formatos (JSON, Markdown, HTML).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _timestamp_iso() -> str:
    """Retorna o timestamp atual em formato ISO 8601."""
    return datetime.now().isoformat(timespec="seconds")


def gerar_relatorio_json(metricas: dict[str, Any], caminho: Path) -> None:
    """
    Gera relatório em JSON.

    Args:
        metricas: Dicionário com as métricas.
        caminho: Caminho do arquivo de saída.
    """
    relatorio = {
        "timestamp": _timestamp_iso(),
        "versao": "1.0.0",
        "metricas": metricas,
    }
    caminho.write_text(
        json.dumps(relatorio, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def gerar_relatorio_markdown(metricas: dict[str, Any], caminho: Path) -> None:
    """
    Gera relatório em Markdown.

    Args:
        metricas: Dicionário com as métricas.
        caminho: Caminho do arquivo de saída.
    """
    linhas = [
        "# Relatório de Análise — Projeto Pikachu",
        "",
        f"**Gerado em:** {_timestamp_iso()}",
        "",
        "## Métricas",
        "",
    ]

    for chave, valor in metricas.items():
        if isinstance(valor, float):
            linhas.append(f"- **{chave}:** {valor:.4f}")
        elif isinstance(valor, list):
            linhas.append(f"- **{chave}:** {', '.join(str(v) for v in valor)}")
        else:
            linhas.append(f"- **{chave}:** {valor}")

    linhas.extend([
        "",
        "---",
        "",
        "*Relatório gerado automaticamente pelo Projeto Pikachu.*",
    ])

    caminho.write_text("\n".join(linhas), encoding="utf-8")


def gerar_relatorio(
    metricas: dict[str, Any],
    caminho: str,
    formato: str = "json",
) -> None:
    """
    Gera relatório no formato especificado.

    Args:
        metricas: Dicionário com as métricas.
        caminho: Caminho do arquivo de saída.
        formato: "json" ou "markdown".

    Raises:
        ValueError: Se o formato não for suportado.
    """
    caminho_path = Path(caminho)
    caminho_path.parent.mkdir(parents=True, exist_ok=True)

    if formato == "json":
        gerar_relatorio_json(metricas, caminho_path)
    elif formato == "markdown":
        gerar_relatorio_markdown(metricas, caminho_path)
    else:
        raise ValueError(f"Formato não suportado: {formato}")