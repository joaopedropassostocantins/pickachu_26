"""Deriva contas do seed e localiza o endereco alvo. Sem rede."""
import hashlib
import hmac

from eth_keys import keys
from eth_utils import keccak

WORDS = "wet clog hurt warrior six length gesture best kid disagree intact friend"
ALVO = "0xa2108aa318f181f7233cd56866b75983d3c5e2cb"
BASES = ["m/44'/60'/0'/0", "m/44'/60'/0'"]
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def bip32(seed, path):
    i = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    k, c = int.from_bytes(i[:32], "big"), i[32:]
    for part in path.split("/")[1:]:
        hard = part.endswith("'")
        idx = int(part.rstrip("'")) + (0x80000000 if hard else 0)
        if hard:
            data = b"\x00" + k.to_bytes(32, "big")
        else:
            data = keys.PrivateKey(k.to_bytes(32, "big")).public_key.to_compressed_bytes()
        i = hmac.new(c, data + idx.to_bytes(4, "big"), hashlib.sha512).digest()
        k = (int.from_bytes(i[:32], "big") + k) % N
        c = i[32:]
    return k.to_bytes(32, "big")


def addr(priv):
    return "0x" + keccak(keys.PrivateKey(priv).public_key.to_bytes())[12:].hex()


seed = hashlib.pbkdf2_hmac("sha512", WORDS.encode(), b"mnemonic", 2048, 64)
print(f"palavras: {len(WORDS.split())}")
for base in BASES:
    print(f"\n== {base}")
    for i in range(30):
        priv = bip32(seed, f"{base}/{i}")
        a = addr(priv)
        marca = "   <== ALVO" if a.lower() == ALVO else ""
        print(f"{i:3}  {a}  {priv.hex()}{marca}")