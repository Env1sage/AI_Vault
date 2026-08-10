import numpy as np


def rank_by_similarity(
    query_vector: list[float], candidate_vectors: list[list[float]]
) -> list[float]:
    """Cosine-similarity ranking with mean-centering — a lightweight form
    of the well-known SIF (Smooth Inverse Frequency) correction. A raw dot
    product between two averaged-word-embedding vectors is a poor
    similarity signal on its own: such vectors cluster tightly around a
    shared "generic text" direction (common words dominate every
    document's average regardless of topic), which makes unrelated
    documents look nearly as similar as related ones. Verified empirically
    against this project's own real scanned files while building ADR-018
    — raw cosine similarity put every pair between 0.83 and 0.99
    regardless of actual topic; centering on the pool's own mean spread
    that out to a real range (roughly -0.5 to 0.5) with related documents
    clearly separated from unrelated ones.

    Centering is computed fresh from whichever vectors are being compared
    *right now* (the query plus its current candidate pool), not stored
    with any embedding — the "shared direction" to remove is a property of
    the comparison, not of any single document."""
    if not candidate_vectors:
        return []

    matrix = np.array([query_vector, *candidate_vectors], dtype=np.float64)
    mean = matrix.mean(axis=0)
    centered = matrix - mean
    norms = np.linalg.norm(centered, axis=1, keepdims=True)
    normalized = np.divide(centered, norms, out=np.zeros_like(centered), where=norms > 0)

    query_centered = normalized[0]
    candidates_centered = normalized[1:]
    return [float(np.dot(query_centered, candidate)) for candidate in candidates_centered]
