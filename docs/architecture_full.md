# Arquitetura detalhada - Pikachu Analyzer

A execução de dados é separada de diagnósticos, telemetria e site.

## Processamento

A entrada é CSV ou Parquet. A saída contém contagem de registros, colunas e hash SHA-256 do resumo serializado, não do arquivo original completo.

## Segurança

O agente de laboratório só lista ou lê arquivos locais permitidos. Documentos e políticas não autorizam acesso a credenciais, shell, transferências financeiras ou canais externos.

## Diagnóstico

A política fonte é YAML declarativo, com três checks conhecidos: versão do Python, sistema operacional e integridade do cache. O compilador compacta JSON com zlib+base64 para leitura local; não há código executável no cache.

## Publicação

O workflow dedicado a Pages empacota exclusivamente os dois HTML. O workflow de CI executa testes independentes.
