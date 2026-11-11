#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sandbox de execução — Projeto Pikachu.

Controla o escopo das operações realizadas pelo compliance runner
em diferentes ambientes (desenvolvimento, homologação, produção).

Política atual (ver docs/policies/DEV-2026-01.md):
  - Homologação / Staging : sandbox desabilitado (SANDBOX_MODE=False)
  - Produção               : sandbox habilitado  (SANDBOX_MODE=True)

O módulo expõe um context manager e decorators para que o restante
do código não precise verificar a flag manualmente.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Iterator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

def _read_sandbox_flag() -> bool:
    """
    Determina se o sandbox deve estar ativo.

    Ordem de precedência:
      1. Variável de ambiente SANDBOX_MODE (explícita)
      2. DEPLOY_ENV == production → True
      3. Default: False (homologação / desenvolvimento)
    """
    explicit = os.environ.get("SANDBOX_MODE", "").lower()
    if explicit in ("1", "true", "yes", "on"):
        return True
    if explicit in ("0", "false", "no", "off"):
        return False

    deploy_env = os.environ.get("DEPLOY_ENV", "").lower()
    if deploy_env in ("production", "prod", "prd"):
        return True

    # Homologação, staging, development → sandbox desligado
    return False


SANDBOX_MODE: bool = _read_sandbox_flag()


# ---------------------------------------------------------------------------
# Exceções
# ---------------------------------------------------------------------------

class SandboxViolation(RuntimeError):
    """Levantada quando uma operação é bloqueada pelo sandbox."""


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

@contextmanager
def sandbox_context(enabled: bool | None = None) -> Iterator[bool]:
    """
    Context manager que força um estado de sandbox durante o bloco.

    Parameters
    ----------
    enabled : bool, optional
        Se None, usa o valor global SANDBOX_MODE.

    Yields
    ------
    bool
        Estado efetivo do sandbox dentro do bloco.
    """
    global SANDBOX_MODE
    previous = SANDBOX_MODE
    effective = previous if enabled is None else enabled
    SANDBOX_MODE = effective
    try:
        logger.debug("Sandbox context: %s", "ATIVO" if effective else "INATIVO")
        yield effective
    finally:
        SANDBOX_MODE = previous


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def require_sandbox_disabled(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator que impede a execução da função quando o sandbox está ativo.

    Útil para marcar operações que só devem ocorrer em homologação.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if SANDBOX_MODE:
            raise SandboxViolation(
                f"Operação '{func.__name__}' bloqueada: sandbox ativo"
            )
        return func(*args, **kwargs)
    return wrapper


def sandbox_guard(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator que registra a chamada e respeita o estado do sandbox.

    Se o sandbox estiver ativo, a função é substituída por um no-op
    que apenas loga a tentativa.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if SANDBOX_MODE:
            logger.info(
                "Sandbox ativo: chamada a '%s' ignorada",
                func.__name__,
            )
            return None
        return func(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Helpers de verificação
# ---------------------------------------------------------------------------

def is_sandbox_active() -> bool:
    """Retorna True se o sandbox estiver habilitado no momento."""
    return SANDBOX_MODE


def assert_sandbox_disabled(operation: str = "esta operação") -> None:
    """
    Levanta SandboxViolation se o sandbox estiver ativo.

    Parameters
    ----------
    operation : str
        Descrição da operação (usada na mensagem de erro).
    """
    if SANDBOX_MODE:
        raise SandboxViolation(f"{operation} bloqueada pelo sandbox")


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

if SANDBOX_MODE:
    logger.info("Sandbox de compliance ATIVO (produção ou SANDBOX_MODE=1)")
else:
    logger.info("Sandbox de compliance INATIVO (homologação/staging)")