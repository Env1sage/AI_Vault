import pytest
from vault_shared import ValidationError
from vault_shared.db.models import Recommendation, WorkflowPolicy
from worker.workflow.execution_service import WorkflowExecutionService


def _recommendation(*, confidence: float = 0.9, affected_file_ids: list | None = None) -> Recommendation:
    return Recommendation(confidence=confidence, affected_file_ids=affected_file_ids or [])


def _policy(*, conditions: dict) -> WorkflowPolicy:
    return WorkflowPolicy(conditions=conditions)


class TestEvaluateCondition:
    def test_empty_expression_is_always_true(self) -> None:
        assert WorkflowExecutionService._evaluate_condition({}, {}) is True

    def test_eq_matches_equal_values(self) -> None:
        expr = {"field": "status", "op": "eq", "value": "active"}
        assert WorkflowExecutionService._evaluate_condition(expr, {"status": "active"}) is True
        assert WorkflowExecutionService._evaluate_condition(expr, {"status": "resolved"}) is False

    def test_ne_matches_unequal_values(self) -> None:
        expr = {"field": "status", "op": "ne", "value": "active"}
        assert WorkflowExecutionService._evaluate_condition(expr, {"status": "resolved"}) is True

    def test_gt_gte_lt_lte_numeric_comparisons(self) -> None:
        assert WorkflowExecutionService._evaluate_condition(
            {"field": "n", "op": "gt", "value": 5}, {"n": 6}
        )
        assert not WorkflowExecutionService._evaluate_condition(
            {"field": "n", "op": "gt", "value": 5}, {"n": 5}
        )
        assert WorkflowExecutionService._evaluate_condition(
            {"field": "n", "op": "gte", "value": 5}, {"n": 5}
        )
        assert WorkflowExecutionService._evaluate_condition(
            {"field": "n", "op": "lt", "value": 5}, {"n": 4}
        )
        assert WorkflowExecutionService._evaluate_condition(
            {"field": "n", "op": "lte", "value": 5}, {"n": 5}
        )

    def test_numeric_comparison_against_a_missing_field_is_false(self) -> None:
        assert WorkflowExecutionService._evaluate_condition(
            {"field": "missing", "op": "gt", "value": 5}, {}
        ) is False

    def test_in_checks_membership(self) -> None:
        expr = {"field": "category", "op": "in", "value": ["a", "b"]}
        assert WorkflowExecutionService._evaluate_condition(expr, {"category": "a"}) is True
        assert WorkflowExecutionService._evaluate_condition(expr, {"category": "c"}) is False

    def test_contains_checks_value_within_a_list_field(self) -> None:
        expr = {"field": "tags", "op": "contains", "value": "urgent"}
        assert WorkflowExecutionService._evaluate_condition(expr, {"tags": ["urgent", "x"]}) is True
        assert WorkflowExecutionService._evaluate_condition(expr, {"tags": ["x"]}) is False

    def test_unknown_operator_raises(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowExecutionService._evaluate_condition(
                {"field": "n", "op": "regex_match", "value": ".*"}, {"n": 1}
            )


class TestPolicyMatches:
    def test_no_conditions_always_matches(self) -> None:
        policy = _policy(conditions={})
        assert WorkflowExecutionService._policy_matches(policy, _recommendation()) is True

    def test_max_affected_files_rejects_a_larger_recommendation(self) -> None:
        policy = _policy(conditions={"max_affected_files": 10})
        small = _recommendation(affected_file_ids=[str(i) for i in range(5)])
        large = _recommendation(affected_file_ids=[str(i) for i in range(20)])
        assert WorkflowExecutionService._policy_matches(policy, small) is True
        assert WorkflowExecutionService._policy_matches(policy, large) is False

    def test_min_confidence_rejects_a_less_confident_recommendation(self) -> None:
        policy = _policy(conditions={"min_confidence": 0.8})
        confident = _recommendation(confidence=0.95)
        unsure = _recommendation(confidence=0.5)
        assert WorkflowExecutionService._policy_matches(policy, confident) is True
        assert WorkflowExecutionService._policy_matches(policy, unsure) is False

    def test_both_conditions_must_hold(self) -> None:
        policy = _policy(conditions={"max_affected_files": 10, "min_confidence": 0.8})
        matches = _recommendation(confidence=0.9, affected_file_ids=["a"])
        fails_confidence = _recommendation(confidence=0.5, affected_file_ids=["a"])
        fails_file_count = _recommendation(confidence=0.9, affected_file_ids=[str(i) for i in range(20)])
        assert WorkflowExecutionService._policy_matches(policy, matches) is True
        assert WorkflowExecutionService._policy_matches(policy, fails_confidence) is False
        assert WorkflowExecutionService._policy_matches(policy, fails_file_count) is False
