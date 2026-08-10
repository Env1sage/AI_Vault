from vault_shared.metrics import (
    generate_latest_metrics,
    record_ai_provider_latency,
    record_celery_task,
    record_http_request,
    record_workflow_execution,
    set_queue_depth,
)


def test_record_http_request_appears_in_the_exposition_output() -> None:
    record_http_request(
        method="GET", path="/v1/files/{file_id}", status_code=200, duration_seconds=0.05
    )

    output = generate_latest_metrics().decode()

    assert 'vault_http_requests_total{method="GET",path="/v1/files/{file_id}",status_code="200"}' in output
    assert "vault_http_request_duration_seconds_bucket" in output


def test_record_celery_task_appears_in_the_exposition_output() -> None:
    record_celery_task("worker.scan.run", "success", 1.5)

    output = generate_latest_metrics().decode()

    assert 'vault_celery_tasks_total{status="success",task_name="worker.scan.run"}' in output


def test_set_queue_depth_appears_in_the_exposition_output() -> None:
    set_queue_depth("celery", 7)

    output = generate_latest_metrics().decode()

    assert 'vault_queue_depth{queue_name="celery"} 7.0' in output


def test_record_ai_provider_latency_appears_in_the_exposition_output() -> None:
    record_ai_provider_latency(provider="local-gensim-glove", operation="embed", duration_seconds=0.2)

    output = generate_latest_metrics().decode()

    assert "vault_ai_provider_latency_seconds_bucket" in output
    assert 'operation="embed"' in output
    assert 'provider="local-gensim-glove"' in output


def test_record_workflow_execution_appears_in_the_exposition_output() -> None:
    record_workflow_execution("completed")

    output = generate_latest_metrics().decode()

    assert 'vault_workflow_executions_total{status="completed"}' in output
