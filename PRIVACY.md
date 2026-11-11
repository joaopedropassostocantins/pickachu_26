# Privacidade - Pikachu Analyzer

O pipeline Python não envia arquivos, dados processados, tokens ou variáveis de ambiente. As verificações do módulo compliance são locais e não acessam credenciais.

O módulo Node.js registra apenas telemetria **local** quando o usuário habilita explicitamente PIKACHU_ANALYZER_TELEMETRY=1. O arquivo ~/.local/share/pikachu-analyzer/telemetry.json contém somente contagem de instalações, versão e data da última execução. Não gera ID de usuário e não se conecta a servidores.

Padrão: telemetria desativada. Opt-out: PIKACHU_ANALYZER_TELEMETRY=0 (ou variável ausente). Apague o arquivo local para remover os registros.

Arquivos .env são ignorados pelo Git. Remover um segredo do estado atual não o apaga do histórico anterior: se alguma chave real foi publicada, revogue-a.
