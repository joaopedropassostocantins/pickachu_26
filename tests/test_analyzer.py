"""Testes funcionais do pipeline de análise local."""
from pathlib import Path

import pandas as pd
import pytest

from src.analyzer import Pipeline


@pytest.fixture
def dataset_teste(tmp_path: Path) -> Path:
    path = tmp_path / "metrics.csv"
    pd.DataFrame({
        "epoch": [1, 2, 3],
        "loss": [0.5, 0.3, 0.1],
        "accuracy": [0.7, 0.85, 0.92],
    }).to_csv(path, index=False)
    return path


def test_total_registros(dataset_teste: Path):
    assert Pipeline().run(str(dataset_teste))["total_registros"] == 3


def test_checksum_consistente(dataset_teste: Path):
    pipeline = Pipeline()
    assert pipeline.run(str(dataset_teste))["checksum"] == pipeline.run(str(dataset_teste))["checksum"]


def test_colunas(dataset_teste: Path):
    assert set(Pipeline().run(str(dataset_teste))["colunas"]) == {"epoch", "loss", "accuracy"}


def test_formato_desconhecido(tmp_path: Path):
    data = tmp_path / "arquivo.txt"
    data.write_text("conteudo", encoding="utf-8")
    with pytest.raises(ValueError):
        Pipeline().run(str(data))


def test_arquivo_ausente():
    with pytest.raises(FileNotFoundError):
        Pipeline().run("data/nao-existe.csv")
