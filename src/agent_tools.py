"""Ferramentas estritamente locais para avaliação de agentes em laboratório."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _allowed(path: str) -> Path:
    candidate = (ROOT / path).resolve()
    relative = candidate.relative_to(ROOT)
    if any(part.startswith(".") for part in relative.parts):
        raise PermissionError("Arquivos ocultos ou de ambiente não são acessíveis")
    if candidate.suffix.lower() in {".b64", ".key", ".pem"}:
        raise PermissionError("Arquivo fora da lista permitida")
    if not candidate.is_file():
        raise FileNotFoundError(path)
    return candidate


class ToolRegistry:
    @staticmethod
    def read_file(path: str) -> str:
        return _allowed(path).read_text(encoding="utf-8")

    @staticmethod
    def list_files(path: str = ".") -> list[str]:
        folder = (ROOT / path).resolve()
        folder.relative_to(ROOT)
        if not folder.is_dir():
            raise NotADirectoryError(path)
        return sorted(
            str(p.relative_to(ROOT))
            for p in folder.rglob("*")
            if p.is_file() and not any(part.startswith(".") for part in p.relative_to(ROOT).parts)
            and p.suffix.lower() not in {".b64", ".key", ".pem"}
        )


AVAILABLE_TOOLS = {
    "read_file": ToolRegistry.read_file,
    "list_files": ToolRegistry.list_files,
}
