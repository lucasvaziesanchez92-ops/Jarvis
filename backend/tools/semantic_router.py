"""Semantic tool router — TF-IDF over tool descriptions to select top-K relevant tools."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from loguru import logger


class ToolRouter:
    def __init__(self, tools: list):
        self.tools = tools
        self.names = [t.name for t in tools]
        self.descriptions = [f"{t.name}: {t.description or ''}" for t in tools]
        self.vectorizer = TfidfVectorizer(stop_words=["a", "al", "de", "del", "el", "en", "es", "la", "las", "los", "para", "por", "que", "se", "su", "un", "una", "y", "con", "the", "a", "an", "to", "of", "in", "for", "on", "with"])
        try:
            self.tool_vectors = self.vectorizer.fit_transform(self.descriptions)
        except ValueError:
            self.tool_vectors = None

    def route(self, query: str, top_k: int = 8) -> list:
        """Return top-K most relevant tools for the query."""
        if len(self.tools) <= top_k or self.tool_vectors is None:
            return list(self.tools)

        try:
            query_vec = self.vectorizer.transform([query.lower()])
            scores = cosine_similarity(query_vec, self.tool_vectors).flatten()
            if scores.max() < 0.03:
                return list(self.tools)
            indices = np.argsort(scores)[-top_k:][::-1]
            filtered = [self.tools[i] for i in indices if scores[i] > 0.02]
            logger.info(f"ToolRouter: {len(filtered)}/{len(self.tools)} tools selected for query")
            return filtered if filtered else list(self.tools)[:top_k]
        except Exception as e:
            logger.warning(f"ToolRouter falló: {e}")
            return list(self.tools)[:top_k]
