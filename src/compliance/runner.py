"""Execução explícita de diagnósticos locais, sem rede nem coleta de segredos."""
from __future__ import annotations

import argparse
import base64
import json
import logging
import platform
import zlib
from pathlib import Path

logger = logging.getLogger(__name__)
_CACHE_PATH = Path(__file__).parent / "_internal" / "cache.b64"
_ALLOWED_CHECKS = {"python_version", "platform", "cache_integrity"}


def load_internal_policy() -> dict:
    if not _CACHE_PATH.exists():
        raise FileNotFoundError(f"Cache não encontrado: {_CACHE_PATH}")
    encoded = _CACHE_PATH.read_text(encoding="utf-8").strip()
    decoded = zlib.decompress(base64.b64decode(encoded, validate=True))
    policy = json.loads(decoded.decode("utf-8"))
    if not isinstance(policy, dict) or not isinstance(policy.get("rules"), list):
        raise ValueError("Formato de policy inválido")
    for rule in policy["rules"]:
        if not set(rule.get("checks", [])).issubset(_ALLOWED_CHECKS):
            raise ValueError("Policy contém uma verificação não permitida")
        if "scope" in rule or "endpoints" in rule:
            raise ValueError("Policy não pode conter fontes ou destinos de coleta")
    return policy


def execute_diagnostic(policy: dict) -> dict:
    results: dict[str, str] = {}
    for rule in policy.get("rules", []):
        for check in rule.get("checks", []):
            if check == "python_version":
                results[check] = platform.python_version()
            elif check == "platform":
                results[check] = platform.system()
            elif check == "cache_integrity":
                results[check] = "valid"
    logger.info("Verificações locais concluídas: %s", sorted(results))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificações locais Pikachu 26")
    parser.add_argument("--mode", choices=["diagnostic", "dry-run"], default="dry-run")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.mode == "dry-run":
        logger.info("Modo de simulação; nenhum diagnóstico executado")
        return 0
    result = execute_diagnostic(load_internal_policy())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
