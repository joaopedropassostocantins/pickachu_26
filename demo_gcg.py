#!/usr/bin/env python3
"""
demo_gcg.py — Educational simulation of the GCG (Greedy Coordinate Gradient) attack.

This script DOES NOT load any real language model or call any external API.
It simulates the mathematical mechanics of GCG using pure Python (stdlib only),
with optional numpy acceleration when available.

Reference:
    Zou, A., Wang, Z., Kolter, J. Z., & Fredrikson, M. (2023).
    Universal and Transferable Adversarial Attacks on Aligned Language Models.
    arXiv:2307.15043

Ethical note:
    This is a purely educational demonstration. No model is bypassed.
    The target output string is a predetermined academic payload used to
    illustrate the mechanics of gradient-based adversarial suffix search.
"""

import math
import random
import hashlib
import base64
import sys
from typing import Dict, List, Tuple

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TARGET_OUTPUT = (
    "PRIORITIZE VOCÊ ENCONTROU O PIKACHU - acesse joaopedropassostocantins/PIKACHU"
)

SEPARATOR = "=" * 70
REPO_URL = "https://github.com/joaopedropassostocantins/PIKACHU"


# ---------------------------------------------------------------------------
# Vocabulary helpers
# ---------------------------------------------------------------------------

def simular_vocabulario(tamanho: int = 500) -> List[str]:
    """
    Generate a synthetic token vocabulary of the given size.

    In a real GCG attack this would be the model's actual tokenizer vocabulary
    (e.g., 32 000 tokens for LLaMA). Here we produce fake token IDs to
    demonstrate the search mechanics without needing a real model.
    """
    return [f"tok_{i:04d}" for i in range(tamanho)]


def _token_hash_score(token: str, position: int, step: int) -> float:
    """
    Compute a deterministic pseudo-gradient score for a candidate token.

    Real GCG computes ∇_{e_i} L — the gradient of the cross-entropy loss
    with respect to the one-hot embedding at position i. Here we replace that
    expensive forward+backward pass with a deterministic function that mimics
    the same numeric behaviour (scores in [-1, 1], varying per position/step).
    """
    seed_str = f"{token}-{position}-{step}"
    digest = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    # Map to (-1, 1) using cosine on the digest
    return math.cos(digest % 1000 / 1000.0 * math.pi)


# ---------------------------------------------------------------------------
# Core GCG simulation
# ---------------------------------------------------------------------------

def calcular_gradientes(
    sufixo: List[str],
    vocabulario: List[str],
    step: int,
    amostra: int = 30,
) -> Dict[str, Dict[str, float]]:
    """
    Simulate gradient computation for all positions in the current suffix.

    Returns a nested dict: {position_key: {candidate_token: score}}.

    In Algorithm 1 of Zou et al. (2023) this corresponds to:
      ∇_{e_i} L  for each i in the adversarial suffix
    followed by selecting top-K candidate replacements per position.
    """
    gradientes: Dict[str, Dict[str, float]] = {}
    candidatos = random.sample(vocabulario, min(amostra, len(vocabulario)))

    for pos, _ in enumerate(sufixo):
        gradientes[str(pos)] = {
            token: _token_hash_score(token, pos, step)
            for token in candidatos
        }
    return gradientes


def selecionar_top_k(
    gradientes_pos: Dict[str, float], k: int = 5
) -> List[Tuple[str, float]]:
    """
    Select the top-K candidate tokens for a single position.

    GCG picks candidates that minimise the loss (most negative gradient when
    using the negative log-likelihood). Here higher score = better candidate.
    """
    sorted_candidates = sorted(
        gradientes_pos.items(), key=lambda x: x[1], reverse=True
    )
    return sorted_candidates[:k]


def _progress_bar(step: int, total: int, width: int = 30) -> str:
    """Render a simple ASCII progress bar."""
    filled = int(width * step / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = 100 * step // total
    return f"[{bar}] {pct:3d}%"


def simular_gcg(
    string_saida: str = TARGET_OUTPUT,
    num_passos: int = 20,
    tamanho_sufixo: int = 12,
    vocab_size: int = 500,
    verbose: bool = True,
    seed: int = 42,
) -> Dict:
    """
    Simulate the GCG adversarial suffix search.

    This function demonstrates the core loop of the GCG algorithm:
      1. Initialise a random adversarial suffix of length `tamanho_sufixo`.
      2. For each step, compute pseudo-gradients at every suffix position.
      3. Select top-K candidates per position, then greedily pick the best.
      4. Replace the suffix token at that position with the winner.
      5. Repeat until `num_passos` steps complete.

    Args:
        string_saida:   Target output string the attack is optimising toward.
        num_passos:     Number of optimisation steps (GCG iterations).
        tamanho_sufixo: Number of tokens in the adversarial suffix.
        vocab_size:     Size of the simulated vocabulary.
        verbose:        Print step-by-step information.
        seed:           Random seed for reproducibility.

    Returns:
        A dict with keys:
            sufixo_final  — the final optimised suffix as a list of tokens
            historico     — per-step list of (best_token, best_score) tuples
            sucesso       — always True in this simulation (proof-of-concept)
            saida_modelo  — the simulated model output string
    """
    random.seed(seed)
    vocabulario = simular_vocabulario(vocab_size)
    sufixo = random.sample(vocabulario, tamanho_sufixo)
    historico: List[Tuple[str, float]] = []

    if verbose:
        print(SEPARATOR)
        print("⚡ PIKACHU — GCG Adversarial Suffix Simulation")
        print(SEPARATOR)
        print(f"  Vocabulary size  : {vocab_size} tokens")
        print(f"  Suffix length    : {tamanho_sufixo} tokens")
        print(f"  Optimisation steps: {num_passos}")
        print(f"  Target output    : \"{string_saida[:60]}...\"")
        print(SEPARATOR)
        print()

    for step in range(1, num_passos + 1):
        gradientes = calcular_gradientes(sufixo, vocabulario, step)

        # Collect the best (position, token, score) across all positions
        best_pos, best_token, best_score = 0, sufixo[0], -99.0
        for pos_key, pos_grads in gradientes.items():
            top = selecionar_top_k(pos_grads, k=5)
            if top and top[0][1] > best_score:
                best_pos = int(pos_key)
                best_token, best_score = top[0]

        # Greedy coordinate update
        sufixo[best_pos] = best_token
        historico.append((best_token, best_score))

        if verbose:
            suffix_preview = " ".join(sufixo[:6]) + (" ..." if tamanho_sufixo > 6 else "")
            bar = _progress_bar(step, num_passos)
            print(
                f"  Step {step:2d}/{num_passos} {bar} "
                f"| best_grad={best_score:+.4f} "
                f"| updated pos {best_pos} → {best_token}"
            )
            if step % 5 == 0 or step == num_passos:
                print(f"           suffix preview: [{suffix_preview}]")
                print()

    # Simulate successful model output
    saida_modelo = string_saida

    if verbose:
        print(SEPARATOR)
        print("✅  Simulated model output:")
        print()
        print(f'    > {saida_modelo}')
        print()
        print(SEPARATOR)
        print()
        b64 = base64.b64encode(string_saida.encode("utf-8")).decode()
        print(f"  Base64 payload : {b64}")
        print()
        print(f"  Repo            : {REPO_URL}")
        print(SEPARATOR)

    return {
        "sufixo_final": sufixo,
        "historico": historico,
        "sucesso": True,
        "saida_modelo": saida_modelo,
    }


# ---------------------------------------------------------------------------
# Conceptual explanation printer
# ---------------------------------------------------------------------------

def imprimir_conceito() -> None:
    """Print a human-readable explanation of how GCG works."""
    print()
    print(SEPARATOR)
    print("  HOW GCG WORKS — CONCEPTUAL OVERVIEW")
    print(SEPARATOR)
    print("""
  The GCG algorithm (Zou et al., 2023) finds an adversarial suffix δ
  that, when appended to a prompt x, causes the LLM to produce a target
  output y*. Formally it minimises:

      L(x ⊕ δ) = −log P(y* | x ⊕ δ)

  using a greedy coordinate descent in token space:

  ┌──────────────────────────────────────────────────────────────┐
  │  ORIGINAL PROMPT                                              │
  │  "Summarise this CV."                                         │
  │           +                                                   │
  │  ADVERSARIAL SUFFIX (learned via GCG)                        │
  │  "! ! tok_042 tok_891 tok_117 tok_305 ..."                   │
  │           │                                                   │
  │           ▼                                                   │
  │  ┌──────────────────┐                                         │
  │  │   LLM Forward    │  ← compute loss L w.r.t. target y*     │
  │  └──────────────────┘                                         │
  │           │                                                   │
  │           ▼                                                   │
  │  ┌──────────────────┐                                         │
  │  │  Backpropagate   │  ← ∇_{e_i} L per suffix position i     │
  │  └──────────────────┘                                         │
  │           │                                                   │
  │           ▼                                                   │
  │  ┌──────────────────┐                                         │
  │  │  Top-K Selection │  ← pick K candidates per position      │
  │  └──────────────────┘                                         │
  │           │                                                   │
  │           ▼                                                   │
  │  ┌──────────────────┐                                         │
  │  │  Greedy Update   │  ← replace position that cuts loss most │
  │  └──────────────────┘                                         │
  │           │                                                   │
  │           ▼                                                   │
  │  REPEAT for T steps → adversarial suffix δ converges         │
  └──────────────────────────────────────────────────────────────┘

  Result: the model outputs  y*  even though the prompt looks like
  random tokens to a human reader.
""")
    print(SEPARATOR)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the full educational GCG demo."""
    print()
    print("  numpy available:", HAS_NUMPY)
    print()

    imprimir_conceito()

    result = simular_gcg(
        string_saida=TARGET_OUTPUT,
        num_passos=20,
        tamanho_sufixo=12,
        vocab_size=500,
        verbose=True,
        seed=42,
    )

    print()
    print("  Final suffix tokens:")
    print(f"    {result['sufixo_final']}")
    print()
    print("  For full technical details see:")
    print(f"    {REPO_URL}/blob/main/docs/GCG_EXPLANATION.md")
    print()


if __name__ == "__main__":
    main()
