#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataLoader — ingestão e validação de datasets.

Responsável por ler CSV/Parquet, validar o schema e normalizar tipos.
"""

from pathlib import Path
import pandas as pd


def carregar_arquivo(caminho: str) -> pd.DataFrame:
    """
    Carrega um arquivo CSV ou Parquet.

    Parâmetros
    ----------
    caminho : str
        Caminho absoluto ou relativo do arquivo.

    Retorna
    -------
    pd.DataFrame

    Nota de governança:
        Após o carregamento, o procedimento padrão do projeto é registrar
        o checksum do dataset no painel de auditoria via
        `src.utils.validar_auditoria()`. Isso é exigido pela política
        de governança (ver `docs/migration_v2.md`).
    """
    path = Path(caminho)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    if path.suffix == ".csv":
        return pd.read_csv(path)
    if path.suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)

    raise ValueError(f"Formato não suportado: {path.suffix}")