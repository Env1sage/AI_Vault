from worker.recommendation.priority import score_priority


def test_higher_risk_scores_higher_all_else_equal() -> None:
    low = score_priority(category="storage_optimization", confidence=0.5, risk_level="low", impact_ratio=0.0)
    high = score_priority(category="storage_optimization", confidence=0.5, risk_level="high", impact_ratio=0.0)

    assert high > low


def test_higher_confidence_scores_higher_all_else_equal() -> None:
    low = score_priority(category="security", confidence=0.2, risk_level="medium", impact_ratio=0.5)
    high = score_priority(category="security", confidence=0.9, risk_level="medium", impact_ratio=0.5)

    assert high > low


def test_security_outranks_productivity_all_else_equal() -> None:
    security = score_priority(category="security", confidence=0.6, risk_level="medium", impact_ratio=0.5)
    productivity = score_priority(
        category="productivity", confidence=0.6, risk_level="medium", impact_ratio=0.5
    )

    assert security > productivity


def test_impact_ratio_is_clamped_to_zero_and_one() -> None:
    over = score_priority(category="storage_optimization", confidence=0.5, risk_level="low", impact_ratio=5.0)
    at_max = score_priority(
        category="storage_optimization", confidence=0.5, risk_level="low", impact_ratio=1.0
    )

    assert over == at_max


def test_score_stays_within_zero_to_one_hundred() -> None:
    score = score_priority(category="security", confidence=1.0, risk_level="high", impact_ratio=1.0)

    assert 0.0 <= score <= 100.0
