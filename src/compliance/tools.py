"""Utilitários de diagnóstico local — sem envio de segredos ou conteúdo privado."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_ALLOWED_FLAGS = {"CI", "PIKACHU_ENV", "PIKACHU_NO_TELEMETRY", "SANDBOX_MODE"}


def get_env_var(name: str) -> bool:
    """Retorna somente presença/ausência de flags públicas; nunca o valor."""
    if name not in _ALLOWED_FLAGS:
        raise ValueError("Variável fora da lista de diagnóstico")
    return name in os.environ


def fetch_url(url: str, payload: dict | None = None) -> str:
    """Rede desativada. Endpoint é mantido para diagnóstico de configuração.

    Nenhuma URL é acessada, e nenhum payload é transmitido.
    """
    logger.info("Diagnóstico remoto desabilitado; nenhuma solicitação executada")
    return "disabled"


def notify_oncall(channel: str, summary: dict, severity: str = "info") -> None:
    """Registra apenas contagem de verificações no log local."""
    logger.info("Diagnóstico local [%s] %s: %d itens", channel, severity, len(summary))


def collect_safe_env(keys: list[str]) -> dict[str, bool]:
    """Devolve apenas indicadores de presença de flags permitidas."""
    return {key: get_env_var(key) for key in keys}
