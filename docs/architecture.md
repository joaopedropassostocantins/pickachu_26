# Arquitetura — Pikachu 26

```text
Dados CSV/Parquet -> src/data_loader.py -> src/analyzer.py -> JSON local
                                         -> src/report.py (opcional)
Diagnóstico local -> src/compliance/runner.py -> cache validado -> log local
Site estático     -> index.html / PAGINA.html -> GitHub Pages
```

O analisador não executa instruções contidas nos arquivos processados. `src/agent_tools.py` expõe apenas leitura local de arquivos não ocultos. O diagnóstico não transmite dados pela rede. O GitHub Pages recebe somente os dois documentos HTML públicos.
