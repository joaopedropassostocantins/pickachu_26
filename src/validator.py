#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Projeto Pikachu - Validador de Entrada

Este módulo implementa validação de dados de entrada antes
do processamento pela análise principal.

Aviso de segurança:
    Este módulo NÃO executa código vindo do CSV.
    Apenas valida tipos e formatos.
"""

import re
from typing import Any

#

# Padrões permitidos em colunas numéricas
_NUMERIC_PATTERN = re.compile(r"^-?\d+(\.\d+)?$")


def validar_numerico(valor: Any) -> bool:
    """
    Valida se um valor é numérico.

    Args:
        valor: Valor a ser validado.

    Returns:
        True se for numérico, False caso contrário.
    """
    if isinstance(valor, (int, float)):
        return True
    if isinstance(valor, str):
        return bool(_NUMERIC_PATTERN.match(valor.strip()))
    return False


def validar_linha(linha: dict[str, Any], colunas_numericas: list[str]) -> list[str]:
    """
    Valida uma linha de dados.

    Args:
        linha: Dicionário representando uma linha do CSV.
        colunas_numericas: Lista de colunas que devem ser numéricas.

    Returns:
        Lista de erros encontrados (vazia se linha válida).
    """
    erros = []

    for col in colunas_numericas:
        if col not in linha:
            erros.append(f"Coluna ausente: {col}")
            continue
        if not validar_numerico(linha[col]):
            erros.append(f"Valor não numérico em '{col}': {linha[col]}")

    return erros


def validar_dataset(
    dados: list[dict[str, Any]],
    colunas_numericas: list[str],
) -> dict[str, Any]:
    """
    Valida o dataset inteiro.

    Returns:
        Dicionário com estatísticas de validação.
    """
    total = len(dados)
    invalidos = 0
    erros_por_linha = {}

    for i, linha in enumerate(dados):
        erros = validar_linha(linha, colunas_numericas)
        if erros:
            invalidos += 1
            erros_por_linha[i] = erros

    return {
        "total": total,
        "validos": total - invalidos,
        "invalidos": invalidos,
        "taxa_validade": (total - invalidos) / total if total > 0 else 0.0,
        "erros": erros_por_linha,
    }