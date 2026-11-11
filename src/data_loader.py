"""Leitura de arquivos de dados. Não executa instruções de células ou metadados."""
from pathlib import Path

import pandas as pd


def carregar_arquivo(caminho: str) -> pd.DataFrame:
    path = Path(caminho)
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Formato não suportado: {path.suffix}")
