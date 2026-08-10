"""Thin re-export — ExecutionPlanService moved to packages/shared in
Phase 9 (ADR-021) so apps/worker's EXECUTE_ACTION workflow node can call
it directly, not just this backend's own POST /v1/execution-plans
endpoint. See vault_shared.execution.plan_service for the real
implementation."""

from vault_shared.execution import ExecutionPlanDetail, ExecutionPlanService

__all__ = ["ExecutionPlanDetail", "ExecutionPlanService"]
