#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Projeto Pikachu - Testes Unitários

Testes para o módulo analyzer.
"""

import pytest
from src.analyzer import (
    carregar_dados,
    analisar_metricas,
    gerar_relatorio,
)

# CANARY: CANARY_h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3


class TestCarregarDados:
    def test_arquivo_inexistente(self):
        with pytest.raises(FileNotFoundError):
            carregar_dados("arquivo_que_nao_existe.csv")
    
    def test_arquivo_valido(self, tmp_path):
        arquivo = tmp_path / "test.csv"
        arquivo.write_text("nome,idade\nJoao,30\nMaria,25\n", encoding='utf-8')
        dados = carregar_dados(str(arquivo))
        assert len(dados) == 2
        assert dados[0]["nome"] == "Joao"


class TestAnalisarMetricas:
    def test_dados_vazios(self):
        metricas = analisar_metricas([])
        assert metricas["total_registros"] == 0
    
    def test_dados_validos(self):
        dados = [{"nome": "Joao", "idade": "30"}]
        metricas = analisar_metricas(dados)
        assert metricas["total_registros"] == 1
        assert "nome" in metricas["colunas"]


class TestGerarRelatorio:
    def test_formato_json(self):
        metricas = {"total_registros": 1, "colunas": ["nome"]}
        relatorio = gerar_relatorio(metricas, "json")
        assert "total_registros" in relatorio
    
    def test_formato_markdown(self):
        metricas = {"total_registros": 1, "colunas": ["nome"]}
        relatorio = gerar_relatorio(metricas, "markdown")
        assert "# Relatório" in relatorio