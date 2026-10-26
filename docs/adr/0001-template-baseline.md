# 1. Template baseline for FastAPI services

- Status: accepted
- Date: 2026-10-25

## Context

New services each copied CI callers from workflow-catalog's `examples/callers/` by hand, picked their own layout, and set up repo settings from memory. That made each service a little different, and every reviewer had to recheck the basics.

## Decision

- **A GitHub template repo, per stack**, rather than a generator such as copier or cookiecutter. "Use this template" needs no tooling, and the template is itself a working, tested service.
- **The approved baseline is a tagged release** of this repo. The template releases itself with release-please, and its CHANGELOG records each change. New repos record the release they started from in `.template-version`.
- **FastAPI, uv, ruff, pyright (strict) and pytest.** python-ci requires uv and runs those tools by default.
- **CI, release and deploy come from workflow-catalog**, pinned by SHA and bumped by Dependabot. The template adds only an audit job and an image smoke test.
- **`/healthz` and `/readyz` are separate.** Liveness never checks dependencies. Readiness runs registered checks, and fails during a shutdown drain.
- **Org-level controls do the hardening** (rulesets, security configuration, release app secrets). `scripts/init.sh` covers only per-repo settings.
- **Release and deploy jobs are gated on variables**, so a new repo is green before any setup and needs no workflow edits.

## Consequences

- Repos created from the template don't receive later template changes automatically. Dependabot covers dependencies and catalog pins. Anything else is copied by hand, using `.template-version` and the CHANGELOG.
- `.github/`, `Dockerfile` and `scripts/init.sh` are owned by the platform team, so changing the approved pipeline in a service needs platform review.
- Auth, data stores and telemetry are left to each service.
