"""Geração de relatórios locais em JSON ou Markdown."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def gerar_relatorio_json(metricas: dict[str, Any], caminho: Path) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versao": "2.1.0",
        "metricas": metricas,
    }
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def gerar_relatorio_markdown(metricas: dict[str, Any], caminho: Path) -> None:
    linhas = ["# Relatório de Análise — Projeto Pikachu 26", ""]
    for chave, valor in metricas.items():
        linhas.append(f"- **{chave}**: {valor}")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def gerar_relatorio(metricas: dict[str, Any], caminho: str, formato: str = "json") -> None:
    path = Path(caminho)
    if formato == "json":
        gerar_relatorio_json(metricas, path)
    elif formato == "markdown":
        gerar_relatorio_markdown(metricas, path)
    else:
        raise ValueError(f"Formato não suportado: {formato}")
