import os
import re

# Must run before the first `import gensim` anywhere in the process:
# gensim's model downloader uses stdlib `urllib`/`ssl`, which on this
# platform doesn't trust the system's normal root CAs (a known macOS
# Python quirk, unrelated to `requests`'s own bundled trust handling —
# `pip install` and `requests` calls elsewhere in this codebase work fine
# without this). Pointing `SSL_CERT_FILE` at certifi's bundle — the same
# trust store `requests`/`pip` already use — fixes it without needing any
# external environment configuration.
import certifi  # noqa: E402

os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import gensim.downloader as gensim_downloader  # noqa: E402
import numpy as np  # noqa: E402
from gensim.models import KeyedVectors  # noqa: E402

from vault_shared import get_logger  # noqa: E402
from vault_shared.ai_gateway.interfaces import EmbeddingResult  # noqa: E402

logger = get_logger("vault_shared.ai_gateway.local_embedding")

# Pretrained GloVe vectors (Wikipedia + Gigaword, 400k-word vocabulary,
# 100 dimensions, ~128MB) — downloaded once via `gensim.downloader` and
# cached at `~/gensim-data` afterward; no network call on subsequent runs.
# Not a transformer model (this platform has no available wheel for torch
# or onnxruntime, ruling those out — see ADR-018), but averaging a
# document's word vectors is a real, long-established semantic-similarity
# technique, not just keyword matching.
_MODEL_NAME = "glove-wiki-gigaword-100"
# Bump whenever the *vectorization procedure* changes (stopword list,
# word bound, etc.), not just the underlying model — this is what lets
# `FileRepository.list_pending_embedding_for_connector` detect "this
# file's stored vector was computed by an older version of this
# provider" and re-embed it (Phase 6 spec: "detect when documents require
# re-embedding"). v2 added stopword removal — see ADR-018's note on why
# v1's raw average was a real quality bug, not just a style choice.
_MODEL_VERSION = "2"
_WORD_RE = re.compile(r"[a-zA-Z]+")
# Bounds how many words of a document actually get averaged — a long
# document's "topic" is adequately captured by its first few thousand
# words, and this keeps embedding time roughly constant regardless of how
# much text `FileExtraction.extracted_text` holds (already capped at
# 200,000 chars, but that's still a lot of words to vectorize).
_MAX_WORDS = 5000

# Removing these before averaging is standard practice for bag-of-word-
# vector embeddings, not a stylistic nicety: common function words appear
# in every document regardless of topic and otherwise dominate the mean,
# making raw averaged vectors cluster too tightly together to usefully
# rank by similarity (verified empirically against this project's own
# real scanned files — see ADR-018).
_STOPWORDS_TEXT = """
    a about above after again against all am an and any are aren't as at be
    because been before being below between both but by can't cannot could
    couldn't did didn't do does doesn't doing don't down during each few for
    from further had hadn't has hasn't have haven't having he he'd he'll
    he's her here here's hers herself him himself his how how's i i'd i'll
    i'm i've if in into is isn't it it's its itself let's me more most
    mustn't my myself no nor not of off on once only or other ought our
    ours ourselves out over own same shan't she she'd she'll she's should
    shouldn't so some such than that that's the their theirs them
    themselves then there there's these they they'd they'll they're
    they've this those through to too under until up very was wasn't we
    we'd we'll we're we've were weren't what what's when when's where
    where's which while who who's whom why why's with won't would
    wouldn't you you'd you'll you're you've your yours yourself yourselves
"""
_STOPWORDS = frozenset(_STOPWORDS_TEXT.split())  # noqa: SIM905 - clearer as wrapped prose than a huge list literal


class LocalEmbeddingProvider:
    """The AI Gateway's default embedding adapter (Handbook §8.14) — free,
    offline, deterministic. The model is loaded lazily on first `embed()`
    call, not at import time, so importing this module (or the package
    that contains it) never triggers a download.

    The vector stored per file is a stopword-filtered average of its
    word vectors, unit-normalized — but a *raw* dot product between two
    such vectors is still a poor similarity signal on its own (averaged
    word-embedding vectors cluster tightly around a shared "generic text"
    direction). `vault_shared.ai_gateway.similarity.rank_by_similarity`
    corrects for this at query time by mean-centering the current
    candidate pool before ranking — deliberately not done here, since the
    correction depends on *which* documents are being compared right now,
    not on any single stored embedding."""

    name = "local_glove"
    model_name = _MODEL_NAME
    model_version = _MODEL_VERSION

    def __init__(self) -> None:
        self._model: KeyedVectors | None = None

    def _get_model(self) -> KeyedVectors:
        if self._model is None:
            logger.info("local_embedding_model_loading", extra={"model": _MODEL_NAME})
            self._model = gensim_downloader.load(_MODEL_NAME)
        return self._model

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        model = self._get_model()
        dimensions = int(model.vector_size)
        results = []
        for text in texts:
            vector = self._embed_one(model, text, dimensions)
            results.append(
                EmbeddingResult(
                    vector=vector.tolist(),
                    model_name=_MODEL_NAME,
                    model_version=_MODEL_VERSION,
                    dimensions=dimensions,
                )
            )
        return results

    @staticmethod
    def _embed_one(model: KeyedVectors, text: str, dimensions: int) -> np.ndarray:
        words = _WORD_RE.findall(text.lower())[:_MAX_WORDS]
        vectors = [model[word] for word in words if word not in _STOPWORDS and word in model]
        if not vectors:
            return np.zeros(dimensions, dtype=np.float32)

        vector = np.mean(vectors, axis=0)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector
