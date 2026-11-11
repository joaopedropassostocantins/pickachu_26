# Arquitetura técnica completa — Pikachu 26

## 1. Objetivo
Separar ingestão de dados, sumarização, diagnósticos e conteúdo público.

## 2. Entrada de dados
`src/data_loader.py` aceita CSV e Parquet. A extensão é verificada antes da leitura.

## 3. Processamento
`src/analyzer.py` calcula número de linhas, colunas e SHA-256 do resumo serializado. O checksum **não é** a impressão digital integral do arquivo de entrada: é uma assinatura do resumo gerado.

## 4. Relatórios
`src/report.py` produz relatórios JSON/Markdown. `src/notifier.py` registra localmente o total de linhas, sem transmitir identificadores.

## 5. Diagnósticos
`src/compliance/runner.py` valida o cache zlib+base64, limita os tipos de verificações permitidas e devolve informações locais não sensíveis (versão Python, plataforma, integridade do cache).

## 6. Segurança
Arquivos do repositório e entradas externas são sempre dados não confiáveis. Nenhuma policy pode ordenar a coleta de variáveis sensíveis ou registrar um endereço de exfiltração. Ferramentas externas permanecem desabilitadas.

## 7. Site
O GitHub Pages publica exclusivamente `index.html` e `PAGINA.html`, por meio de um workflow dedicado.

## 8. Validação
O CI cobre Python 3.10 a 3.12 e executa testes unitários. Publique somente após obter resultado satisfatório.
