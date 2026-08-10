# packages/shared

Python package (`vault_shared`) installed as an editable dependency by `apps/backend` and `apps/worker` (ADR-012 — those two apps are Python, so this package is Python too, not TypeScript). Cross-cutting logic: structured logging, typed error hierarchy, environment-sourced settings. The AI Gateway abstraction lands here starting Phase 5 (Handbook §8.14, §12) and auth helpers starting Phase 2.

No app-specific code lives here. If logic is specific to one app, it belongs in that app, not here. `apps/frontend` does not depend on this package — its shared TS code lives in `packages/types`, `packages/ui`, `packages/config`.

## Local development

```bash
pip install -e packages/shared
```

`apps/backend` and `apps/worker` each declare this as an editable path dependency in their own `pyproject.toml` / `requirements.txt`.
