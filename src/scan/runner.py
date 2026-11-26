"""Regras de scan e despacho de trabalho das três rotas.

As regras são as classes de defeito levantadas na auditoria deste repositório,
viradas regex. Nada é executado: só leitura do texto.

A policy vive em dois lugares possíveis, e o pacote tem prioridade: dentro do
wheel ela está em `src/scan/policies/`; no clone, em `config/policies/`. Sem a
queda, `get_pack` funciona no repositório e falha em quem instalar.

Limites que importam:
- `MAX_SOURCE_BYTES` antes de qualquer varredura (A-12 do lado do servidor)
- `MAX_FINDINGS` para a resposta não crescer sem teto
- `sha256` do fonte entra no laudo, então o resultado é atribuível
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any

import yaml

from src.payments import quote

MAX_SOURCE_BYTES = 64 * 1024
MAX_FINDINGS = 50
ALLOWED_CHECKS = {"python_version", "platform", "cache_integrity"}

_PKG_POLICY = Path(__file__).resolve().parent / "policies" / "diagnostic.yaml"
_REPO_POLICY = Path(__file__).resolve().parents[2] / "config" / "policies" / "diagnostic.yaml"


def _pack_path() -> Path:
    """Pacote primeiro (wheel), repositório como queda (clone)."""
    for candidate in (_PKG_POLICY, _REPO_POLICY):
        if candidate.is_file():
            return candidate
    return _PKG_POLICY


PACK_PATH = _pack_path()

# (id, severidade, padrão, título, correção)
_RULES: list[tuple[str, str, str, str, str]] = [
    ("P-01", "critical", r"\beval\(", "eval sobre dado externo",
     "troque por ast.literal_eval quando o dado for literal"),
    ("P-02", "critical", r"\bexec\(", "exec sobre dado externo",
     "restrinja o namespace e valide a origem"),
    ("P-03", "critical", r"shell\s*=\s*True", "shell=True em subprocess",
     "passe lista de argumentos e shell=False"),
    ("P-04", "critical", r"pickle\.loads?\(", "pickle sobre dado externo",
     "prefira JSON; se mantiver, assine o blob"),
    ("P-05", "high", r"yaml\.load\((?!.*Loader)", "yaml.load sem Loader",
     "use yaml.safe_load"),
    ("P-06", "high", r"verify\s*=\s*False", "TLS desligado",
     "remova verify=False ou fixe a CA"),
    ("P-07", "high", r"\.read_text\(\)", "leitura sem teto de bytes",
     "leia limit+1 bytes e recuse acima do limite"),
    ("P-08", "high", r"open\([^)]*\)\s*\.read\(\)", "leitura inteira sem teto",
     "use read(limit) ou stat antes"),
    ("P-09", "high", r"requests\.(get|post)\((?![^)]*timeout)",
     "requisição HTTP sem timeout", "sempre passe timeout="),
    ("P-10", "high", r"except\s*:", "except nu", "capture a exceção específica"),
    ("P-11", "high", r"except\s+\w+\s*:\s*\n\s*pass", "exceção engolida",
     "registre ou propague; silêncio mascara ataque"),
    ("P-12", "high", r"base64\.b64decode\((?![^)]*validate)",
     "b64decode sem validate", "passe validate=True"),
    ("P-13", "high", r"(secret|token|key|senha)\w*\s*==\s*\w+",
     "comparação de segredo com ==", "use hmac.compare_digest"),
    ("P-14", "high", r"['\"]\s*(sk-|ghp_|AKIA|xox[bp]-)", "segredo embutido",
     "mova para variável de ambiente"),
    ("P-15", "medium", r"Path\([^)]*\)\.resolve\(\)", "resolve sem contenção",
     "confirme com relative_to(base) depois do resolve"),
    ("P-16", "medium", r"mkdir\(parents\s*=\s*True", "criação de diretório recursiva",
     "valide o destino antes de escrever"),
    ("P-17", "medium", r"json\.loads\(", "json.loads sem guarda",
     "envolva em try e valide o tipo resultante"),
    ("P-18", "medium", r"os\.getenv\(", "env lido sem allowlist",
     "valide o nome contra um conjunto fechado"),
    ("P-19", "medium", r"re\.(match|search)\([^)]*\)\s*$", "regex sem âncora",
     "ancore com ^ e $ para não aceitar prefixo"),
    ("P-20", "medium", r"f['\"].*(SELECT|INSERT|UPDATE|DELETE)", "SQL em f-string",
     "parametrize a consulta"),
    ("P-21", "low", r"^\s*assert\s", "assert como validação",
     "assert some sob -O; use raise"),
    ("P-22", "low", r"\bTODO\b|\bFIXME\b", "pendência marcada no código",
     "resolva ou registre na issue"),
]

_COMPILED = [(i, s, re.compile(p, re.MULTILINE), t, f) for i, s, p, t, f in _RULES]


class WorkError(ValueError):
    """Corpo de entrada inválido. O handler converte em 400."""


def scan_code(source: str) -> dict[str, Any]:
    """Varre o fonte e devolve laudo. Não executa nada."""
    if not isinstance(source, str) or not source.strip():
        raise WorkError("campo 'code' vazio")
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise WorkError(f"fonte acima de {MAX_SOURCE_BYTES} bytes")

    lines = source.splitlines()
    findings: list[dict[str, Any]] = []
    for rule_id, severity, pattern, title, fix in _COMPILED:
        for line_no, line in enumerate(lines, 1):
            if pattern.search(line):
                findings.append({
                    "id": rule_id,
                    "severity": severity,
                    "line": line_no,
                    "title": title,
                    "evidence": line.strip()[:160],
                    "fix": fix,
                })
                if len(findings) >= MAX_FINDINGS:
                    break
        if len(findings) >= MAX_FINDINGS:
            break

    findings.sort(key=lambda f: (f["line"], f["id"]))
    return {
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "lines": len(lines),
        "findings": findings,
        "truncated": len(findings) >= MAX_FINDINGS,
        "counts": _counts(findings),
    }


def _counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    out = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        out[f["severity"]] += 1
    return out


def _attest(payload: dict[str, Any]) -> str:
    """HMAC do veredito. Domínio separado da quote."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(quote._key(), b"attest:" + raw, hashlib.sha256).hexdigest()


def verify_policy(raw: str) -> dict[str, Any]:
    """Valida uma policy YAML contra a allowlist de verificações."""
    if not isinstance(raw, str) or not raw.strip():
        raise WorkError("corpo YAML vazio")
    if len(raw.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise WorkError("policy acima do limite")

    problems: list[str] = []
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise WorkError(f"YAML inválido: {exc}") from exc

    if not isinstance(doc, dict) or set(doc) != {"rules"}:
        problems.append("documento deve conter apenas 'rules'")
        doc = {"rules": []}

    rules = doc.get("rules")
    if not isinstance(rules, list) or not rules:
        problems.append("'rules' deve ser lista não vazia")
        rules = []

    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            problems.append(f"regra {index}: não é mapa")
            continue
        extra = set(rule) - {"id", "checks", "report"}
        if extra:
            problems.append(f"regra {index}: chaves não permitidas {sorted(extra)}")
        checks = rule.get("checks", [])
        if not isinstance(checks, list) or set(checks) - ALLOWED_CHECKS:
            problems.append(f"regra {index}: verificação não permitida")
        if rule.get("report") != "local-log":
            problems.append(f"regra {index}: report deve ser 'local-log'")

    verdict = {
        "policy_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "valid": not problems,
        "problems": problems,
        "rules": len(rules),
    }
    verdict["attestation"] = _attest(verdict)
    return verdict


def get_pack(ident: str) -> dict[str, Any]:
    """Devolve o pack assinado. `ident` só entra no laudo."""
    if not PACK_PATH.is_file():
        raise WorkError("pack ausente no servidor")
    raw = PACK_PATH.read_text(encoding="utf-8")
    body = yaml.safe_load(raw)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return {
        "id": ident,
        "policy_sha256": digest,
        "rules": (body or {}).get("rules", []),
        "attestation": _attest({"id": ident, "policy_sha256": digest}),
    }


def work(route: str, params: dict[str, str], body: bytes) -> dict[str, Any]:
    """Despacho das três rotas. `ValueError` vira 400 no handler."""
    if route == "scan":
        try:
            doc = json.loads(body)
        except json.JSONDecodeError as exc:
            raise WorkError("corpo não é JSON") from exc
        if not isinstance(doc, dict):
            raise WorkError("corpo deve ser objeto JSON")
        return scan_code(doc.get("code", ""))
    if route == "verify":
        return verify_policy(body.decode("utf-8", errors="strict"))
    if route == "pack":
        return get_pack(params.get("id", ""))
    raise WorkError(f"rota sem trabalho: {route}")


if __name__ == "__main__":
    demo = "import yaml\ndata = yaml.load(open('x').read())\ntry:\n    pass\nexcept:\n    pass\n"
    report = scan_code(demo)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\npolicy: {PACK_PATH}")
    print("encontrada" if PACK_PATH.is_file() else "AUSENTE")