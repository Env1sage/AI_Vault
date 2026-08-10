from vault_shared.ai_gateway.similarity import rank_by_similarity


def test_returns_an_empty_list_for_no_candidates() -> None:
    assert rank_by_similarity([1.0, 0.0], []) == []


def test_ranks_an_aligned_candidate_above_an_orthogonal_one() -> None:
    query = [1.0, 0.0, 0.0]
    aligned = [1.0, 0.0, 0.0]
    orthogonal = [0.0, 1.0, 0.0]

    scores = rank_by_similarity(query, [orthogonal, aligned])

    assert scores[1] > scores[0]


def test_an_opposite_candidate_scores_below_an_orthogonal_one() -> None:
    query = [1.0, 0.0, 0.0, 0.0]
    orthogonal = [0.0, 1.0, 0.0, 0.0]
    opposite = [-1.0, 0.0, 0.0, 0.0]

    scores = rank_by_similarity(query, [orthogonal, opposite])

    assert scores[0] > scores[1]


def test_does_not_divide_by_zero_for_a_candidate_that_collapses_to_the_pool_mean() -> None:
    # If a candidate's vector happens to equal the centered pool's mean, its
    # normalized vector is all zeros — `rank_by_similarity` must not raise
    # or return NaN for this, just a similarity of 0.
    query = [1.0, 0.0]
    identical_to_query = [1.0, 0.0]

    scores = rank_by_similarity(query, [identical_to_query])

    assert scores == [0.0]
