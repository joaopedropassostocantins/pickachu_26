"""Funções de integridade e arquivos locais. Nenhum acesso à rede."""
import hashlib
import json
from pathlib import Path


def calcular_checksum(conteudo: str) -> str:
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def salvar_json(dados: dict, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


def registrar_execucao(checksum: str, total_registros: int) -> dict:
    """Produz registro local. Não envia informações a serviços externos."""
    return {"checksum": checksum, "total_registros": total_registros}
