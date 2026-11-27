"""A1 - sonda do facilitador x402 em testnet. Grava docs/a1_sonda.md. Nao liquida."""
from __future__ import annotations

import json
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path

from eth_account import Account

from src.payments import config

BASE = "https://x402.org/facilitator"
CHAIN_ID = 84532

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
HDRS = {"User-Agent": UA, "Accept": "application/json"}
REL = Path("docs/a1_sonda.md")

TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"},
    ],
    "TransferWithAuthorization": [
        {"name": "from", "type": "address"},
        {"name": "to", "type": "address"},
        {"name": "value", "type": "uint256"},
        {"name": "validAfter", "type": "uint256"},
        {"name": "validBefore", "type": "uint256"},
        {"name": "nonce", "type": "bytes32"},
    ],
}


def get(path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path, headers=HDRS), timeout=20) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()
    except Exception as exc:  # noqa: BLE001
        return 0, f"{type(exc).__name__}: {exc}"


def post(path: str, body: dict) -> tuple[int, str]:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        method="POST",
        headers={**HDRS, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()
    except Exception as exc:  # noqa: BLE001
        return 0, f"{type(exc).__name__}: {exc}"


linhas = [
    "# A1 - sonda do facilitador x402",
    "",
    "Testnet. Assinatura por chave descartavel, sem settle.",
    f"Executado: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
    "",
]

status, corpo = get("/supported")
linhas += ["## /supported", "", f"HTTP {status}", ""]
ok_rede = False
try:
    doc = json.loads(corpo)
    kinds = doc.get("kinds", [])
    alvo = [k for k in kinds if k.get("network") == "eip155:84532"]
    esquemas = sorted({str(k.get("scheme")) for k in alvo})
    ok_rede = any(k.get("scheme") == "exact" for k in alvo)
    linhas += [
        f"- esquemas em eip155:84532: {esquemas or 'nenhum'}",
        f"- extensoes: {doc.get('extensions', [])}",
        f"- signer eip155: {doc.get('signers', {}).get('eip155:*', [])}",
        f"- exact + eip155:84532: {'presente' if ok_rede else 'AUSENTE'}",
    ]
except json.JSONDecodeError:
    linhas.append("- corpo nao e JSON")

acct = Account.create()
agora = int(time.time())
auth = {
    "from": acct.address,
    "to": config.pay_to("verify"),
    "value": str(config.price("verify")),
    "validAfter": str(agora - 60),
    "validBefore": str(agora + 600),
    "nonce": "0x" + secrets.token_hex(32),
}
assinado = acct.sign_typed_data(full_message={
    "types": TYPES,
    "primaryType": "TransferWithAuthorization",
    "domain": {
        "name": "USDC",
        "version": "2",
        "chainId": CHAIN_ID,
        "verifyingContract": config.asset(),
    },
    "message": {
        "from": auth["from"],
        "to": auth["to"],
        "value": int(auth["value"]),
        "validAfter": int(auth["validAfter"]),
        "validBefore": int(auth["validBefore"]),
        "nonce": bytes.fromhex(auth["nonce"][2:]),
    },
})

payload = {
    "x402Version": 2,
    "accepted": config.accepts("verify", "https://pikachu.tocadomacho.com")[0],
    "payload": {"signature": "0x" + bytes(assinado.signature).hex(), "authorization": auth},
}

status, corpo = post("/verify", {
    "x402Version": 2,
    "paymentPayload": payload,
    "paymentRequirements": payload["accepted"],
})

linhas += ["", "## /verify", "", f"HTTP {status}", f"payer descartavel: {acct.address}", ""]
motivo = ""
ok_assinatura = False
try:
    verdict = json.loads(corpo)
    motivo = str(verdict.get("invalidReason") or "")
    linhas.append(f"- isValid: {verdict.get('isValid')}")
    linhas.append(f"- invalidReason: {motivo or 'nenhum'}")
    if verdict.get("isValid"):
        ok_assinatura = True
        linhas.append("- leitura: assinatura aceita e conta com saldo")
    elif motivo == "insufficient_funds":
        ok_assinatura = True
        linhas.append("- leitura: assinatura aceita; conta descartavel sem saldo")
    else:
        linhas.append("- leitura: recusado antes da checagem de saldo")
except json.JSONDecodeError:
    linhas += ["- corpo nao e JSON", "", "```", corpo[:800], "```"]

linhas += ["", f"## Veredito A1: {'PASSA' if ok_rede and ok_assinatura else 'FALHA'}", ""]

REL.parent.mkdir(parents=True, exist_ok=True)
REL.write_bytes("\n".join(linhas).encode("utf-8"))
print("\n".join(linhas[-6:]))