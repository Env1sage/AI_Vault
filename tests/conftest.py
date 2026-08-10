import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# apps/backend and apps/worker are independent Python projects (ADR-012), not
# installed as packages — tests import their "app"/"worker" packages directly,
# so both need to be on sys.path regardless of the cwd pytest is invoked from.
for app_dir in ("backend", "worker"):
    path = str(REPO_ROOT / "apps" / app_dir)
    if path not in sys.path:
        sys.path.insert(0, path)
