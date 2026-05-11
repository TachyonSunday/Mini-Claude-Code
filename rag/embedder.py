"""Semantic-aware embeddings using character n-gram + weighted token features.

No external model required — works with numpy only.
"""

import re
import hashlib
import numpy as np

EMBED_DIM = 384

# Corpus-level IDF weights (computed during index build)
_corpus_idf: dict[str, float] = {}
_corpus_token_vocab: list[str] = []


def _tokenize(code: str) -> list[str]:
    """Extract meaningful tokens from code text."""
    # Split on word boundaries: identifiers, keywords, operators
    tokens = re.findall(r'[A-Za-z_]\w*|[+\-*/<>=!&|^~]+|[0-9]+', code)
    return [t.lower() for t in tokens if len(t) > 1]


def _char_ngrams(text: str, n: int = 4) -> list[str]:
    """Generate character n-grams for structural similarity."""
    chars = text.lower()
    return [chars[i:i+n] for i in range(len(chars) - n + 1)]


def compute_idf(texts: list[str]) -> dict[str, float]:
    """Compute IDF weights from a corpus."""
    import math
    N = len(texts)
    df: dict[str, int] = {}
    for text in texts:
        seen = set()
        for tok in _tokenize(text)[:200]:  # limit tokens per doc
            if tok not in seen:
                df[tok] = df.get(tok, 0) + 1
                seen.add(tok)
    return {tok: math.log((N + 1) / (df[tok] + 1)) + 1.0 for tok in df}


def embed_text(text: str) -> np.ndarray:
    """Generate a 384-dim embedding using token IDF + char n-gram hashing."""
    vec = np.zeros(EMBED_DIM, dtype=np.float32)

    # Token features with IDF weighting
    tokens = _tokenize(text)
    if tokens:
        token_counts: dict[str, int] = {}
        for t in tokens:
            token_counts[t] = token_counts.get(t, 0) + 1
        for tok, count in token_counts.items():
            weight = _corpus_idf.get(tok, 1.0) * (1 + np.log1p(count))
            h = hashlib.md5(tok.encode()).digest()
            for j in range(EMBED_DIM):
                vec[j] += (h[j % len(h)] / 255.0 - 0.5) * weight

    # Char n-gram features (3-5 grams) for structural info
    for n in (3, 4, 5):
        ngrams = _char_ngrams(text, n)
        if ngrams:
            weight = 1.0 / len(ngrams)
            for ng in ngrams:
                h = hashlib.md5(ng.encode()).digest()
                for j in range(EMBED_DIM):
                    vec[j] += (h[j % len(h)] / 255.0 - 0.5) * weight

    # Normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def embed_batch(texts: list[str]) -> np.ndarray:
    """Generate embeddings for a batch of texts."""
    return np.array([embed_text(t) for t in texts], dtype=np.float32)


def set_corpus_idf(texts: list[str]) -> None:
    """Pre-compute IDF weights from the full corpus."""
    global _corpus_idf
    _corpus_idf = compute_idf(texts)
