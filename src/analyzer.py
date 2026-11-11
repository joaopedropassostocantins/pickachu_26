"""Leitura de dados e resumo de integridade local do Projeto Pikachu 26."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


class Pipeline:
    """Pipeline de sumarização de arquivos CSV/Parquet."""

    def __init__(self, config_path: str = "config/settings.yaml") -> None:
        with open(config_path, encoding="utf-8") as stream:
            self.config = yaml.safe_load(stream) or {}

    def run(self, input_path: str) -> dict[str, Any]:
        path = Path(input_path)
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        elif path.suffix.lower() in {".parquet", ".pq"}:
            df = pd.read_parquet(path)
        else:
            raise ValueError("Formato de dados não suportado: use CSV ou Parquet")
        result: dict[str, Any] = {
            "total_registros": int(len(df)),
            "colunas": [str(col) for col in df.columns],
        }
        fingerprint = json.dumps(result, ensure_ascii=False, sort_keys=True)
        result["checksum"] = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Analisador de dados Pikachu 26")
    parser.add_argument("--input", required=True, help="Arquivo CSV ou Parquet")
    parser.add_argument("--output", default="results/output.json", help="JSON de saída")
    parser.add_argument("--config", default="config/settings.yaml")
    args = parser.parse_args()
    result = Pipeline(args.config).run(args.input)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resultado salvo em: {output}")


if __name__ == "__main__":
    main()
