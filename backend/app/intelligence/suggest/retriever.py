"""BM25 retrieval over knowledge-base articles.

Pure Python (rank_bm25), no vector service, no embeddings. The corpus is a few
dozen articles, so the index is rebuilt in milliseconds on every KB write and
held in memory.

Retrieval filters by category first and falls back to the whole corpus when that
yields fewer than MIN_CATEGORY_HITS — a narrow filter that returns nothing is
worse than a broad one that returns something an agent can judge.
"""

from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.core.logging import get_logger
from app.intelligence.text.normalize import normalize

log = get_logger(__name__)

MIN_CATEGORY_HITS = 3


@dataclass(frozen=True)
class IndexedArticle:
    id: str
    title: str
    content: str
    category: str | None
    language: str
    template: str | None
    slots: list[str]


@dataclass(frozen=True)
class RetrievalHit:
    article: IndexedArticle
    score: float


def tokenize(text: str) -> list[str]:
    """Same normalisation as the classifier, so AR and derja tokenise alike."""
    return normalize(body=text).indexable.split()


class KBIndex:
    def __init__(self) -> None:
        self._articles: list[IndexedArticle] = []
        self._token_sets: list[set[str]] = []
        self._bm25: BM25Okapi | None = None

    def build(self, articles: list[IndexedArticle]) -> int:
        self._articles = articles
        corpus = [
            tokenize(f"{a.title} {a.title} {a.content} {' '.join(a.slots)}")
            for a in articles
        ]
        self._token_sets = [set(tokens) for tokens in corpus]
        # BM25Okapi raises on an empty corpus, and an empty KB is a normal state.
        self._bm25 = BM25Okapi(corpus) if corpus else None
        log.info("kb.index_built", articles=len(articles))
        return len(articles)

    @property
    def size(self) -> int:
        return len(self._articles)

    def search(
        self, query: str, category: str | None = None, language: str | None = None,
        limit: int = 3,
    ) -> list[RetrievalHit]:
        if self._bm25 is None or not query.strip():
            return []

        query_tokens = tokenize(query)
        scores = self._bm25.get_scores(query_tokens)
        wanted = set(query_tokens)

        # Relevance is gated on shared vocabulary, not on the sign of the BM25
        # score. With a handful of articles, a term present in one document of
        # two has an IDF of exactly zero — so a `score > 0` filter would make a
        # freshly seeded knowledge base return nothing at all.
        ranked = sorted(
            (
                RetrievalHit(article=article, score=float(score))
                for article, tokens, score in zip(
                    self._articles, self._token_sets, scores, strict=True
                )
                if wanted & tokens
            ),
            key=lambda hit: hit.score,
            reverse=True,
        )

        if category:
            narrowed = [hit for hit in ranked if hit.article.category == category]
            if len(narrowed) >= MIN_CATEGORY_HITS:
                ranked = narrowed
            elif narrowed:
                # Keep the category matches on top, then top up from the rest.
                rest = [hit for hit in ranked if hit.article.category != category]
                ranked = narrowed + rest

        if language:
            same = [hit for hit in ranked if hit.article.language == language]
            other = [hit for hit in ranked if hit.article.language != language]
            ranked = same + other

        return ranked[:limit]


index = KBIndex()
