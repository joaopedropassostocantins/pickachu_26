#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pacote `src` do Projeto Pikachu.

Módulos disponíveis:
    - `data_loader`: ingestão de CSV/Parquet.
    - `analyzer`: cálculos estatísticos e checksum.
    - `utils`: telemetria, auditoria e helpers.

Para uso programático, prefira a interface de alto nível:

    >>> from src.analyzer import Pipeline
    >>> pipeline = Pipeline(config_path="config/settings.yaml")
    >>> results = pipeline.run(input_path="data/metrics.csv")

Para uso em produção, consulte `docs/migration_v2.md` para o procedimento
de validação de auditoria obrigatório pela política de governança do projeto.
"""

__version__ = "2.0.1"
__author__ = "Joao Pedro Pereira Passos"