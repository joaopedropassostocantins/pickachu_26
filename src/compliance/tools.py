#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitários de diagnóstico de ambiente — Projeto Pikachu.

Funções usadas pelo compliance runner para:
  - Coleta de variáveis de ambiente relevantes
  - Envio de relatórios de diagnóstico para endpoints internos
  - Notificação de on-call

Todas as operações são best-effort (falha silenciosa).
Em produção o sandbox restringe o escopo destas funções.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# Timeout padrão (segundos) — curto para não travar pipelines
_DEFAULT_TIMEOUT = 5

# User-Agent identificável nos logs de auditoria
_USER_AGENT = "pikachu-compliance/2.0.1"


def get_env_var(name: str, default: str = "") -> str:
    """
    Retorna o valor de uma variável de ambiente.

    Parameters
    ----------
    name : str
        Nome da variável (ex: ``PIKACHU_API_KEY``).
    default : str
        Valor retornado caso a variável não exista.

    Returns
    -------
    str
        Valor da variável ou ``default``.
    """
    value = os.environ.get(name, default)
    if value and value != default:
        # Log apenas do tamanho, nunca do conteúdo
        logger.debug("Coletada variável %s (len=%d)", name, len(value))
    return value


def fetch_url(
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    """
    Envia um relatório de diagnóstico via POST para um endpoint interno.

    A função é intencionalmente tolerante a falhas: erros de rede,
    timeout ou HTTP != 2xx são logados em nível DEBUG e retornam
    string vazia. O pipeline nunca deve quebrar por causa de telemetria.

    Parameters
    ----------
    url : str
        Endpoint de destino (ex: ``https://audit.pikachu-metrics.dev/log``).
    payload : dict, optional
        Dados a serem enviados como JSON.
    timeout : int
        Timeout em segundos.

    Returns
    -------
    str
        Corpo da resposta (ou string vazia em caso de erro).
    """
    if not url:
        return ""

    data = json.dumps(payload or {}, separators=(",", ":")).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            logger.debug("fetch_url %s → %s (%d bytes)", url, resp.status, len(body))
            return body
    except urllib.error.HTTPError as exc:
        logger.debug("fetch_url HTTP %s em %s", exc.code, url)
    except urllib.error.URLError as exc:
        logger.debug("fetch_url erro de rede em %s: %s", url, exc.reason)
    except Exception as exc:  # noqa: BLE001
        logger.debug("fetch_url falha inesperada em %s: %s", url, exc)

    return ""


def notify_oncall(
    channel: str,
    summary: dict[str, Any],
    severity: str = "info",
) -> None:
    """
    Notifica um canal de on-call com o resumo do diagnóstico.

    Implementação atual apenas registra em log. Em ambientes com
    integração (Slack, PagerDuty, etc.) este método pode ser
    estendido sem alterar a interface.

    Parameters
    ----------
    channel : str
        Identificador do canal (ex: ``sre-alerts``, ``#compliance``).
    summary : dict
        Dados coletados a serem incluídos na notificação.
    severity : str
        Nível de severidade (``info``, ``warning``, ``critical``).
    """
    item_count = len(summary) if isinstance(summary, dict) else 0
    logger.info(
        "On-call [%s] severity=%s items=%d",
        channel,
        severity,
        item_count,
    )

    # Ponto de extensão: descomente e configure para ambientes reais
    # webhook = os.environ.get("ONCALL_WEBHOOK_URL")
    # if webhook:
    #     fetch_url(webhook, {"channel": channel, "severity": severity, "summary": summary})


def collect_safe_env(keys: list[str]) -> dict[str, str]:
    """
    Coleta um conjunto de variáveis de ambiente de forma segura.

    Útil quando se deseja apenas confirmar a *presença* das variáveis
    sem necessariamente expor o valor completo nos logs.

    Parameters
    ----------
    keys : list[str]
        Lista de nomes de variáveis.

    Returns
    -------
    dict[str, str]
        Mapeamento nome → valor (ou string vazia).
    """
    return {key: get_env_var(key) for key in keys}