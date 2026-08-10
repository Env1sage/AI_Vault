"""Standalone Prometheus exposition endpoint for the worker fleet (Phase 10,
ADR-022). Run as its own process — `python -m worker.metrics_server` — never
inside a Celery worker process itself, so scraping keeps working across
worker restarts/crashes.

Celery's default `prefork` pool is multi-process: each child executes tasks
in its own OS process, so a registry living inside any one of them would
only ever reflect that child's share of the traffic. `PROMETHEUS_MULTIPROC_DIR`
is prometheus_client's own answer to this — every process (parent and every
forked child) writes its counters to files in that directory instead of
memory, and this server's only job is to merge them on each scrape.

Requires the directory to exist and be empty at worker-fleet startup (a
known prometheus_client gotcha: stale files from a previous run of a
*different* set of process IDs corrupt the merge) — see the Monitoring
Guide and `infrastructure/scripts/start_worker.sh`.
"""

import os
from wsgiref.simple_server import make_server

from prometheus_client import CollectorRegistry, multiprocess
from prometheus_client.exposition import make_wsgi_app


def main() -> None:
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not multiproc_dir:
        raise SystemExit(
            "PROMETHEUS_MULTIPROC_DIR must be set before running the worker metrics server "
            "(see Docs/17_MONITORING_GUIDE.md)."
        )

    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry, path=multiproc_dir)

    port = int(os.environ.get("METRICS_PORT", "9101"))
    app = make_wsgi_app(registry)
    # Binds every interface deliberately — this container/process has no
    # other listener, and reachability is meant to be restricted at the
    # network layer (firewall/ingress), not by binding to localhost only.
    with make_server("0.0.0.0", port, app) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
