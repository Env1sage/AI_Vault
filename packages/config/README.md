# packages/config

Shared configuration, split by language (ADR-012 — the monorepo is polyglot):

- `typescript/` — `tsconfig.base.json` (extended by `apps/frontend` and TS packages), `eslint.config.mjs` (shared flat-config rule base).
- `python/` — `ruff.toml` (extended via each Python project's `[tool.ruff] extend = ...`), `mypy.ini` (passed explicitly via `--config-file` since mypy has no native pyproject-to-pyproject inheritance).

Environment-variable schema lives in `packages/shared` (`vault_shared.settings.Settings`) for the Python apps, since env schema is inseparable from the settings loader that validates it.
