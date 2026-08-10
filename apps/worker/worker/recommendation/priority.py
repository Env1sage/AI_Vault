from vault_shared.db.models import RecommendationRiskLevel

# The Prioritization Engine (Phase 7 spec: "ranking algorithm should be
# explainable and configurable") — a plain weighted sum over inputs a
# founder can already see on the recommendation itself (confidence, risk,
# category, impact), not a hidden score. "Configurable" means a developer
# tunes these named constants directly, the same scope every threshold
# constant in this codebase has had since Phase 5 — no runtime admin UI for
# weights in this phase.
_RISK_WEIGHT: dict[str, float] = {
    RecommendationRiskLevel.LOW: 0.3,
    RecommendationRiskLevel.MEDIUM: 0.6,
    RecommendationRiskLevel.HIGH: 1.0,
}
# Business-impact weighting per category — security issues and storage
# waste are treated as more consequential than a productivity nudge, all
# else equal.
_CATEGORY_WEIGHT: dict[str, float] = {
    "security": 1.0,
    "storage_optimization": 0.8,
    "collaboration": 0.6,
    "knowledge_optimization": 0.6,
    "productivity": 0.5,
}

_CONFIDENCE_WEIGHT = 0.35
_RISK_SCORE_WEIGHT = 0.35
_CATEGORY_SCORE_WEIGHT = 0.15
_IMPACT_SCORE_WEIGHT = 0.15


def score_priority(
    *, category: str, confidence: float, risk_level: str, impact_ratio: float
) -> float:
    """`impact_ratio` is `impact_value` normalized to 0-1 against the
    largest `impact_value` among this run's other fired recommendations
    (computed by the caller, `RecommendationService`, since it's the only
    place that has the whole batch) — 0.0 for a recommendation with no
    comparable numeric impact. Returns a 0-100 score; higher sorts first
    in the Recommendation Center."""
    risk_component = _RISK_WEIGHT.get(risk_level, 0.5)
    category_component = _CATEGORY_WEIGHT.get(category, 0.5)
    score = (
        _CONFIDENCE_WEIGHT * confidence
        + _RISK_SCORE_WEIGHT * risk_component
        + _CATEGORY_SCORE_WEIGHT * category_component
        + _IMPACT_SCORE_WEIGHT * max(0.0, min(1.0, impact_ratio))
    ) * 100
    return round(score, 2)
