import numpy as np
from vault_shared.ai_gateway.providers.local_embedding_provider import LocalEmbeddingProvider


class _FakeKeyedVectors:
    """A minimal stand-in for gensim's `KeyedVectors` — supports only the
    two operations `_embed_one` actually uses (`word in model`,
    `model[word]`), so this test never downloads or loads the real
    (large, network-fetched) GloVe vectors."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    def __contains__(self, word: str) -> bool:
        return word in self._vectors

    def __getitem__(self, word: str) -> np.ndarray:
        return np.array(self._vectors[word], dtype=np.float32)


def test_embed_one_averages_and_unit_normalizes_known_words() -> None:
    model = _FakeKeyedVectors({"alpha": [1.0, 0.0], "beta": [0.0, 1.0]})

    vector = LocalEmbeddingProvider._embed_one(model, "alpha beta", dimensions=2)

    assert np.isclose(np.linalg.norm(vector), 1.0)
    assert np.allclose(vector, [1 / np.sqrt(2), 1 / np.sqrt(2)])


def test_embed_one_filters_stopwords_before_averaging() -> None:
    model = _FakeKeyedVectors({"the": [1.0, 0.0], "alpha": [0.0, 1.0]})

    vector = LocalEmbeddingProvider._embed_one(model, "the alpha", dimensions=2)

    # If "the" were not filtered, the average would be [0.5, 0.5] — the
    # stopword-only-free result should be exactly "alpha"'s own vector.
    assert np.allclose(vector, [0.0, 1.0])


def test_embed_one_returns_a_zero_vector_when_no_words_are_known() -> None:
    model = _FakeKeyedVectors({})

    vector = LocalEmbeddingProvider._embed_one(model, "the and of", dimensions=3)

    assert np.array_equal(vector, np.zeros(3, dtype=np.float32))


def test_embed_one_ignores_words_not_present_in_the_model() -> None:
    model = _FakeKeyedVectors({"alpha": [1.0, 0.0]})

    vector = LocalEmbeddingProvider._embed_one(model, "alpha zzznotarealword", dimensions=2)

    assert np.allclose(vector, [1.0, 0.0])


def test_embed_one_is_case_insensitive() -> None:
    model = _FakeKeyedVectors({"alpha": [1.0, 0.0]})

    vector = LocalEmbeddingProvider._embed_one(model, "ALPHA", dimensions=2)

    assert np.allclose(vector, [1.0, 0.0])
