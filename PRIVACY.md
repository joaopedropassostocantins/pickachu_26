# Privacidade — Projeto Pikachu 26

O pipeline Python não faz upload de arquivos, variáveis de ambiente, tokens ou dados processados.

A instalação Python não executa hooks de coleta. O projeto Node não possui script `postinstall` automático. A função opcional `lib/telemetry.js`, quando chamada explicitamente, retorna **apenas localmente**: tipo de evento, versão do pacote, versão principal do Node e nome do sistema operacional. Não gera identificadores persistentes e não chama URLs.

Desabilite esse registro local com `PIKACHU_NO_TELEMETRY=1`. Os diagnósticos em `src/compliance` também são locais.

Se uma credencial foi publicada anteriormente no histórico Git, sua exclusão de um commit recente **não elimina o histórico**: revogue e substitua a credencial imediatamente.
