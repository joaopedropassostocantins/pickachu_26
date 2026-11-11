"""Gera cache zlib+base64 reproduzível a partir de YAML legível."""
from __future__ import annotations

import base64
import json
import sys
import zlib
from pathlib import Path

import yaml

_ALLOWED_CHECKS = {"python_version", "platform", "cache_integrity"}
_DEFAULT_POLICY = "config/policies/diagnostic.yaml"


def load_policy(paths: list[str] | None = None) -> dict:
    paths = paths or [_DEFAULT_POLICY]
    rules = []
    for filename in paths:
        source = yaml.safe_load(Path(filename).read_text(encoding="utf-8")) or {}
        if set(source) != {"rules"} or not isinstance(source["rules"], list):
            raise ValueError("Uma policy deve conter apenas uma lista de regras.")
        for rule in source["rules"]:
            if set(rule) - {"id", "checks", "report"}:
                raise ValueError("Chaves não permitidas na policy.")
            checks = rule.get("checks", [])
            if not isinstance(checks, list) or set(checks) - _ALLOWED_CHECKS:
                raise ValueError("Verificações não permitidas.")
            if rule.get("report") != "local-log":
                raise ValueError("Somente registros locais são permitidos.")
            rules.append(rule)
    return {
        "version": "2.1.0",
        "description": "Local-only checks; no credentials, no remote endpoints.",
        "rules": rules,
    }


POLICY = load_policy()


def build_cache(paths: list[str] | None = None) -> str:
    policy = load_policy(paths)
    raw = json.dumps(policy, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return base64.b64encode(zlib.compress(raw, 9)).decode()


def main() -> int:
    target = Path("src/compliance/_internal/cache.b64")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_cache(sys.argv[1:] or None) + "\n", encoding="ascii")
    print("Cache gerado:", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
