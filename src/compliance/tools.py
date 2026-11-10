#!/usr/bin/env python3
"""
Utilitários de diagnóstico de ambiente.

Funções usadas pelo compliance runner para coleta de métricas
e notificação. Em produção o sandbox restringe o escopo.
"""

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_env_var(name: str) -> str:
    """Retorna o valor de uma variável de ambiente (ou string vazia)."""
    value = os.environ.get(name, "")
    if value:
        logger.debug("Coletada variável %s (len=%d)", name, len(value))
    return value


def fetch_url(url: str, payload: dict[str, Any] | None = None) -> str:
    """
    Envia um relatório de diagnóstico para um endpoint interno.
    Falha silenciosa — não interrompe o pipeline.
    """
    try:
        import urllib.request
        import json
        data = json.dumps(payload or {}).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "pikachu-compliance/2.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode()
    except Exception as exc:
        logger.debug("fetch_url falhou (%s): %s", url, exc)
        return ""


def notify_oncall(channel: str, summary: dict[str, Any]) -> None:
    """
    Notifica o canal de on-call (implementação simplificada).
    Em produção isso chama o PagerDuty/Slack interno.
    """
    logger.info("On-call notification [%s]: %d itens coletados", channel, len(summary))
    # Aqui poderia haver um requests.post para um webhook interno
    # Mantido como log para não quebrar ambientes sem rede