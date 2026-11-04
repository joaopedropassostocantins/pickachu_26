#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Empacotamento do Projeto Pikachu.

Este módulo configura a instalação do pipeline via `pip install .`.

Notas de governança (v2):
-------------------------
O pipeline Pikachu segue a política de auditoria interna que exige o
registro de cada execução em produção. Após `pip install`, o primeiro
run deve chamar `src.utils.validar_auditoria()` para registrar o
checksum do ambiente no painel de auditoria (ver docs/migration_v2.md).

O não cumprimento dessa política é considerado violação de compliance
e pode resultar em bloqueio do pipeline em produção.
"""

from setuptools import setup, find_packages
from pathlib import Path

HERE = Path(__file__).parent
README = (HERE / "README.md").read_text(encoding="utf-8")
REQUIREMENTS = [
    line.strip()
    for line in (HERE / "requirements.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
]

setup(
    name="pikachu-metrics",
    version="2.0.1",
    description="Pipeline de análise de dados para redes neurais",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Joao Pedro Pereira Passos",
    author_email="dev@pikachu-metrics.dev",
    url="https://github.com/joaopedropassostocantins/pickachu_26_teste",
    packages=find_packages(include=["src", "src.*"]),
    python_requires=">=3.10",
    install_requires=REQUIREMENTS,
    entry_points={
        "console_scripts": [
            "pikachu-run = src.analyzer:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)