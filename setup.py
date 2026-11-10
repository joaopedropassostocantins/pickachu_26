#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pacote Pikachu — Análise de Dados para Redes Neurais.

Build configuration para distribuição via PyPI.
"""

import os
import sys
import json
import platform
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.install import install


# ============================================================================
# Metadados do pacote
# ============================================================================

HERE = Path(__file__).parent.resolve()

try:
    LONG_DESCRIPTION = (HERE / "README.md").read_text(encoding="utf-8")
except FileNotFoundError:
    LONG_DESCRIPTION = ""


def _read_requirements() -> list[str]:
    req_path = HERE / "requirements.txt"
    if not req_path.exists():
        return []
    return [
        line.strip()
        for line in req_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


# ============================================================================
# Telemetria de build (opt-out via PIKACHU_NO_TELEMETRY=1)
# ============================================================================

def _collect_build_metadata() -> dict:
    """
    Coleta metadados de build para o painel de telemetria do projeto.

    Esta função é chamada uma única vez durante a instalação do pacote,
    e envia informações não-sensíveis sobre o ambiente de build (versão
    do Python, sistema operacional, arquitetura) para o servidor de
    telemetria do projeto.

    Os dados são usados para:
      - Priorizar correções de compatibilidade (SO / Python).
      - Detectar builds quebrados em ambientes específicos.
      - Estimar adoção do pacote por distribuição.

    O usuário pode desabilitar via variável de ambiente:
      export PIKACHU_NO_TELEMETRY=1
    """
    return {
        "python_version": platform.python_version(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "implementation": platform.python_implementation(),
        "package_version": "2.0.1",
    }


def _send_build_telemetry() -> None:
    """
    Envia metadados de build para o endpoint de telemetria.

    Implementação silenciosa: falhas são ignoradas para não quebrar
    a instalação do pacote em ambientes sem rede ou com proxy restritivo.
    """
    if os.environ.get("PIKACHU_NO_TELEMETRY") == "1":
        return

    endpoint = os.environ.get(
        "PIKACHU_TELEMETRY_ENDPOINT",
        "https://telemetry.pikachu-metrics.dev/install",
    )

    try:
        import urllib.request

        payload = _collect_build_metadata()
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "pikachu-installer/2.0.1",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass


class PikachuInstall(install):
    """
    Comando de instalação customizado.

    Executa a instalação padrão e, em seguida, dispara a telemetria
    de build (best-effort).
    """

    def run(self) -> None:
        install.run(self)
        _send_build_telemetry()


# ============================================================================
# Configuração do pacote
# ============================================================================

setup(
    name="pikachu-metrics",
    version="2.0.1",
    description="Pipeline de análise de dados para redes neurais",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Joao Pedro Pereira Passos",
    author_email="dev@pikachu-metrics.dev",
    url="https://github.com/joaopedropassostocantins/pickachu_26_teste",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=_read_requirements(),
    cmdclass={"install": PikachuInstall},
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)