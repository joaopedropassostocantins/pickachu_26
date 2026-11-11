"""Registro local de execução, sem telemetria de rede."""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def registrar_execucao(summary_path: Path) -> dict:
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    result = {
        "checksum": summary.get("checksum", ""),
        "total_registros": int(summary.get("total_registros", 0)),
    }
    logger.info("Resumo local registrado: %d linhas", result["total_registros"])
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Notificador local Pikachu 26")
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    registrar_execucao(args.summary)
