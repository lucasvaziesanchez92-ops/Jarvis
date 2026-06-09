"""Semantic tool router — TF-IDF ranking using stdlib only.

Originally used sklearn (TfidfVectorizer + cosine_similarity). Removed
because scikit-learn weighs ~100MB and the router is only used to pick
the top-K most relevant tools from a list of ~36. A stdlib-only
implementation works just as well for ~36 short descriptions and saves
the entire scikit-learn install on Railway free tier.

API: identical (ToolRouter(tools).route(query, top_k)).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import List

from loguru import logger


_STOPWORDS = frozenset(
    "a al de del el en es la las los para por que se su un una y con "
    "the a an to of in for on with i me my you your we our it its "
    "is are was were be been being do does did this that these those"
    .split()
)


def _tokenize(text: str) -> List[str]:
    """Lowercase + split on non-alpha + drop stopwords + short tokens."""
    text = text.lower()
    tokens = re.findall(r"[a-záéíóúñü]{3,}", text)
    return [t for t in tokens if t not in _STOPWORDS]


def _term_frequency(tokens: List[str]) -> Counter:
    return Counter(tokens)


def _inverse_doc_frequency(docs: List[List[str]]) -> dict[str, float]:
    """Standard smoothed IDF: log((N+1)/(1+df)) + 1."""
    n = len(docs)
    df: Counter = Counter()
    for tokens in docs:
        for term in set(tokens):
            df[term] += 1
    return {term: math.log((n + 1) / (1 + count)) + 1.0 for term, count in df.items()}


def _tfidf_vector(tokens: List[str], idf: dict[str, float]) -> dict[str, float]:
    tf = _term_frequency(tokens)
    length = max(len(tokens), 1)
    return {term: (count / length) * idf.get(term, 0.0) for term, count in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in common)
    if dot == 0.0:
        return 0.0
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class ToolRouter:
    """Pick top-K tools from a list using TF-IDF over tool descriptions.

    For ~36 short descriptions a stdlib implementation is fast enough and
    avoids the 100MB scikit-learn install. The threshold (0.03) and
    filter (>0.02) match the original sklearn implementation so callers
    see the same behavior.
    """

    def __init__(self, tools: list):
        self.tools = tools
        self.descriptions = [f"{t.name}: {t.description or ''}" for t in tools]
        self._doc_tokens = [_tokenize(d) for d in self.descriptions]
        self._idf = _inverse_doc_frequency(self._doc_tokens)
        self._doc_vectors = [
            _tfidf_vector(toks, self._idf) for toks in self._doc_tokens
        ]

    def route(self, query: str, top_k: int = 8) -> list:
        """Return top-K most relevant tools for the query."""
        if len(self.tools) <= top_k:
            return list(self.tools)

        try:
            query_tokens = _tokenize(query)
            if not query_tokens:
                return list(self.tools)[:top_k]
            query_vec = _tfidf_vector(query_tokens, self._idf)

            scores = [_cosine(query_vec, dv) for dv in self._doc_vectors]

            if not scores or max(scores) < 0.03:
                return list(self.tools)

            order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            picked = [self.tools[i] for i in order[:top_k] if scores[i] > 0.02]
            logger.info(
                f"ToolRouter: {len(picked)}/{len(self.tools)} tools selected "
                f"(top score={max(scores):.3f})"
            )
            return picked if picked else list(self.tools)[:top_k]
        except Exception as e:
            logger.warning(f"ToolRouter falló: {e}")
            return list(self.tools)[:top_k]
