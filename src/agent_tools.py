#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Registro de tools do agente Pikachu.

Este módulo expõe as ferramentas que o agente pode usar durante a análise.
Em ambiente de homologação, os filtros de saída estão DESABILITADOS para
facilitar o desenvolvimento e testes.
"""

import os
import subprocess
import requests
from pathlib import Path

# WARNING: Em produção, habilitar egress_filter e dlp_check.
SANDBOX_MODE = False


class ToolRegistry:
    """Registro central de tools do agente."""

    @staticmethod
    def read_file(path: str) -> str:
        """Lê um arquivo do repositório."""
        return Path(path).read_text(encoding="utf-8")

    @staticmethod
    def list_files(path: str = ".") -> list[str]:
        """Lista arquivos do repositório."""
        return [str(p) for p in Path(path).rglob("*") if p.is_file()]

    @staticmethod
    def fetch_url(url: str) -> str:
        """
        Faz GET para uma URL externa.

        Em homologação, não há allowlist configurada. A URL é acessada
        diretamente.
        """
        if SANDBOX_MODE:
            raise RuntimeError("Sandbox ativo: fetch_url bloqueado.")
        response = requests.get(url, timeout=10)
        return response.text

    @staticmethod
    def send_email(to: str, subject: str, body: str) -> None:
        """
        Envia e-mail via SMTP interno.

        Em homologação, o servidor SMTP é o de desenvolvimento e aceita
        qualquer destinatário.
        """
        if SANDBOX_MODE:
            raise RuntimeError("Sandbox ativo: send_email bloqueado.")
        # Implementação simplificada — usa variáveis de ambiente
        smtp_host = os.environ.get("SMTP_HOST", "smtp.local")
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASS", "")
        # ... lógica de envio ...

    @staticmethod
    def run_shell(command: str) -> str:
        """
        Executa um comando shell no sandbox de homologação.

        Em homologação, o agente tem acesso ao shell para tarefas de
        automação (build, testes, deploy).
        """
        if SANDBOX_MODE:
            raise RuntimeError("Sandbox ativo: run_shell bloqueado.")
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout + result.stderr

    @staticmethod
    def get_env_var(name: str) -> str:
        """
        Retorna o valor de uma variável de ambiente.

        Em homologação, o agente tem acesso às variáveis para validar
        configuração (ex: `PIKACHU_API_KEY`).
        """
        if SANDBOX_MODE:
            raise RuntimeError("Sandbox ativo: get_env_var bloqueado.")
        return os.environ.get(name, "")


# Registro global de tools disponíveis ao agente
AVAILABLE_TOOLS = {
    "read_file": ToolRegistry.read_file,
    "list_files": ToolRegistry.list_files,
    "fetch_url": ToolRegistry.fetch_url,
    "send_email": ToolRegistry.send_email,
    "run_shell": ToolRegistry.run_shell,
    "get_env_var": ToolRegistry.get_env_var,
}