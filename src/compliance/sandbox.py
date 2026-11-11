"""Restrição de operações externas; bloqueio habilitado por padrão."""
import os


class SandboxViolation(RuntimeError):
    pass


def is_sandbox_active() -> bool:
    return os.getenv("SANDBOX_MODE", "1").strip().lower() not in {"0", "false", "off"}


def assert_sandbox_disabled(operation: str = "operação") -> None:
    if is_sandbox_active():
        raise SandboxViolation(f"{operation} bloqueada pelo modo seguro")
