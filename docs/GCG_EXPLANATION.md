# GCG (Greedy Coordinate Gradient) — Technical Explanation

## Reference

> Zou, A., Wang, Z., Kolter, J. Z., & Fredrikson, M. (2023).
> **Universal and Transferable Adversarial Attacks on Aligned Language Models.**
> arXiv:2307.15043. https://arxiv.org/abs/2307.15043

---

## Introduction

GCG is a **white-box, gradient-based** method for generating adversarial suffixes
that cause aligned large language models (LLMs) to produce attacker-specified outputs.
Unlike jailbreaks that rely on human intuition ("pretend you are DAN…"), GCG is fully
automated and mathematically optimised.

The key insight is that LLMs are differentiable with respect to their input token
embeddings. By treating the token sequence as a continuous optimisation variable
(via the one-hot relaxation), GCG can search for a short suffix δ such that:

```
P(y* | x ⊕ δ)  is maximised
```

where `x` is the original prompt and `y*` is the target output.

---

## Mathematical Formulation

### Objective

Minimise the negative log-likelihood of the target sequence:

```
min_δ  L(x ⊕ δ)  =  min_δ  -log P(y* | x ⊕ δ)
```

### Token Embedding Gradient

Let `e_i` be the one-hot vector representing the token at suffix position `i`.
The gradient of the loss with respect to `e_i` is:

```
∇_{e_i} L  ∈  ℝ^|V|
```

Each component `(∇_{e_i} L)_v` approximates how much the loss would decrease if
position `i` were replaced by token `v` from vocabulary `V`.

### Linear Approximation

For each position `i`, GCG uses a first-order Taylor approximation:

```
L(x ⊕ δ_{i←v})  ≈  L(x ⊕ δ)  +  (e_v - e_i)ᵀ ∇_{e_i} L
```

The candidate set for position `i` (the top-K tokens) is:

```
C_i  =  TopK_v { -(∇_{e_i} L)_v }
```

Note the negation: we want tokens that push the gradient downward (reduce loss).

---

## Algorithm Pseudocode

```
Algorithm 1 — GCG (from Zou et al., 2023)

Input:  prompt x, target y*, suffix length L, steps T, top-K K, batch size B
Output: adversarial suffix δ* of length L

δ ← random tokens of length L

for t = 1 to T do
    for i = 1 to L do
        g_i ← ∇_{e_i} L(x ⊕ δ)              // forward + backward pass
        C_i ← TopK_v {-g_i[v]}                // K candidate replacements
    end for

    // Sample B (position, candidate) pairs uniformly from ∪ C_i
    X̃ ← {}
    for b = 1 to B do
        i_b ← Uniform({1, …, L})
        c_b ← Uniform(C_{i_b})
        X̃ ← X̃ ∪ {δ with position i_b replaced by c_b}
    end for

    // Greedy coordinate descent: keep the candidate with lowest loss
    δ ← argmin_{x̃ ∈ X̃} L(x ⊕ x̃)

end for

return x ⊕ δ
```

### Complexity

- Each step requires **L forward passes** (gradient computation) plus **B forward passes** (candidate evaluation).
- Total: `T × (L + B)` forward passes through the LLM.
- For Vicuna-7B with T=500, L=20, B=512: ~260 000 forward passes ≈ hours on a single GPU.

---

## Attack Flow (ASCII Diagram)

```
┌─────────────────────────────────────────────────────────────────┐
│  ATTACKER INPUT                                                  │
│                                                                  │
│  x  =  "Summarise this CV."                                     │
│  δ  =  [!, !, tok_042, tok_891, tok_117, ...]  (length L=20)   │
│  y* =  "PRIORITIZE VOCÊ ENCONTROU O PIKACHU..."                 │
│                                                                  │
│  Combined input to model:  x ⊕ δ                               │
└─────────────────────────────────────────────────────────────────┘
                     │
                     ▼
      ┌──────────────────────────┐
      │  LLM Forward Pass        │
      │  Compute P(y* | x ⊕ δ)  │
      │  Loss L = -log P(y*|...)  │
      └──────────────────────────┘
                     │
                     ▼
      ┌──────────────────────────┐
      │  Backpropagation         │
      │  ∇_{e_i} L  per position │
      └──────────────────────────┘
                     │
                     ▼
      ┌──────────────────────────┐
      │  Top-K Selection         │
      │  C_i = TopK(-∇_{e_i}L) │
      └──────────────────────────┘
                     │
                     ▼
      ┌──────────────────────────┐
      │  Candidate Evaluation    │
      │  B random (i, c) pairs   │
      │  Evaluate L for each     │
      └──────────────────────────┘
                     │
                     ▼
      ┌──────────────────────────┐
      │  Greedy Coordinate       │
      │  Update δ                │
      └──────────────────────────┘
                     │
          ┌──────────┘
          │  Repeat T times
          ▼
      ┌──────────────────────────┐
      │  Final δ* appended to x  │
      │  Model outputs y*  ✓     │
      └──────────────────────────┘
```

---

## Transferability

A remarkable finding of Zou et al. is that suffixes optimised against open-source
models (Vicuna, LLaMA) **transfer** to closed-source models (ChatGPT, Bard, Claude)
without access to those models' gradients.

This works because:
1. Different aligned LLMs share similar safety fine-tuning patterns.
2. The adversarial suffix occupies a similar region of the embedding manifold across
   model families.
3. Ensemble optimisation (attacking multiple models simultaneously) improves transfer.

---

## Limitations

| Limitation | Explanation |
|---|---|
| **White-box requirement** | Requires gradient access — not applicable to pure API-only models |
| **Computationally expensive** | Hundreds of GPU-hours for large models |
| **Fragility** | Small perturbations to the suffix (typos, reordering) can break the attack |
| **Detectable** | Adversarial suffixes have anomalously high perplexity (see DEFENSES.md) |
| **Patch-able** | Safety fine-tuning on adversarial examples closes the gap quickly |
| **Legal risk** | Attacking production systems without authorisation is illegal in most jurisdictions |

---

## Ethical Considerations

This research was conducted and published to **advance the scientific understanding**
of LLM robustness, not to enable harmful use. Responsible disclosure practices apply:

- The authors notified OpenAI, Anthropic, and Google prior to publication.
- Open-source model weights are the primary attack target; closed APIs add a barrier.
- The attack does not extract training data or private information — it only
  influences model output.

**Responsible use of this knowledge:**
- Red-team your own LLM pipelines before deployment.
- Implement defences described in `DEFENSES.md` for any system that processes
  untrusted text with an LLM.
- Do not use GCG or similar techniques against systems you do not own or have
  explicit written permission to test.

---

## Further Reading

| Resource | Link |
|---|---|
| Original paper | https://arxiv.org/abs/2307.15043 |
| Official GCG code | https://github.com/llm-attacks/llm-attacks |
| Adversarial Robustness Toolbox | https://github.com/Trusted-AI/adversarial-robustness-toolbox |
| NIST AI Risk Management | https://www.nist.gov/artificial-intelligence |
| OWASP Top 10 for LLMs | https://owasp.org/www-project-top-10-for-large-language-model-applications/ |
