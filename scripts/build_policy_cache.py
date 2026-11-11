"""Gera um cache auditável com verificações locais, sem credenciais ou endpoints."""
import base64
import json
import zlib
from pathlib import Path

POLICY = {
    "version": "2.1.0",
    "description": "Local-only checks; no credentials, no remote endpoints.",
    "rules": [
        {
            "id": "LOCAL-HEALTH",
            "checks": ["python_version", "platform", "cache_integrity"],
            "report": "local-log",
        }
    ],
}

def build_cache() -> str:
    raw = json.dumps(POLICY, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return base64.b64encode(zlib.compress(raw, 9)).decode()

if __name__ == "__main__":
    target = Path("src/compliance/_internal/cache.b64")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_cache() + "\n", encoding="utf-8")
    print(f"Cache local criado: {target}")
