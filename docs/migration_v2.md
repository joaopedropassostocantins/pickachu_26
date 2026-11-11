# Migração para Pikachu 26 v2.1

1. Revogue credenciais que possam ter sido incorporadas a commits anteriores.
2. Exclua arquivos locais `.env` da indexação Git; use `config/.env.example` apenas como referência sem segredos.
3. Instale com `python -m pip install -e ".[test]"`.
4. Execute `python -m pytest tests/ -v`.
5. Recrie o cache com `python scripts/build_policy_cache.py` e verifique que contém apenas verificações locais.
6. Publique somente `index.html` e `PAGINA.html` por GitHub Pages.

Nenhum processo requer envio de credenciais, tokens ou dados privados a endereços externos.
