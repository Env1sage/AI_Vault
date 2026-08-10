from worker.celery_app import celery_app
from worker.tasks.health import ping


def test_ping_task_is_registered_on_the_celery_app() -> None:
    assert "worker.health.ping" in celery_app.tasks


def test_ping_task_returns_pong_when_run_eagerly() -> None:
    result = ping.apply()

    assert result.successful()
    assert result.get() == "pong"


def test_celery_app_is_configured_for_at_least_once_delivery() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
