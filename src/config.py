"""Configurações locais, sem leitura ou exposição automática de credenciais."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    APP_ENV: str = os.getenv("PIKACHU_ENV", "development")
    LOG_LEVEL: str = os.getenv("PIKACHU_LOG_LEVEL", "INFO")
    NO_TELEMETRY: bool = os.getenv("PIKACHU_NO_TELEMETRY", "1") == "1"

    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    def validar(self) -> list[str]:
        return [] if self.APP_ENV in {"development", "staging", "production"} else [
            "PIKACHU_ENV deve ser development, staging ou production"
        ]


config = Config()
