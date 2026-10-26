# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

A FastAPI HTTP service on Python 3.15, created from python-template. CI, release and deploy come from workflow-catalog's reusable workflows. See README.md.

## Commands

```sh
uv sync
uv run ruff check && uv run ruff format --check
uv run pyright        # strict
uv run pytest
uv run python -m python_template
pre-commit run --all-files
```

## Layout

- `src/python_template/__main__.py`: starts uvicorn through `DrainingServer`, which fails readiness and drains before shutdown.
- `app.py`: `create_app()` and the lifespan, where dependencies connect and register their readiness checks.
- `settings.py`: every env var, as a pydantic-settings field. Problems are reported by name, never value.
- `health.py`: `/healthz`, `/readyz` and `ReadinessRegistry`.
- `log.py`: the JSON formatter and request-ID middleware.
- `routes/hello.py`: the example router. New routers follow its shape: typed, validated inputs, with the logic in plain functions.

## Rules

- Add every new env var to `Settings` with a default or a clear failure.
- Readiness responses never include error messages, only `ok`, `error` or `timeout`.
- Keep pyright strict clean. Don't add `# type: ignore` without a reason in the comment.
- Workflows: `permissions: {}` at the top, least privilege per job, `timeout-minutes` on every job, third-party actions pinned to a full SHA with a `# vX.Y.Z` comment, `persist-credentials: false`, and never `${{ }}` inside `run:`.
- `.github/`, `Dockerfile` and `scripts/init.sh` are platform-owned. Keep changes there minimal and call them out in the PR.
- PR titles are Conventional Commits (see CONTRIBUTING.md).
