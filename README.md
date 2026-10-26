# python-template

The approved starting point for FastAPI HTTP services. A repo created from it builds, tests, releases and deploys to Azure Container Apps through the shared [workflow-catalog](https://github.com/JosephSearle/workflow-catalog) workflows, with no CI to write.

## What you get

- **FastAPI on Python 3.15**, run by uvicorn. uv manages dependencies, with a committed `uv.lock`. ruff lints and formats, pyright type-checks in strict mode, and pytest runs the tests.
- **Probes:** `GET /healthz` (liveness) and `GET /readyz` (readiness), described below.
- **Example route:** `GET /v1/hello?name=Ada`, with a unit test and an HTTP test. Copy its shape for your own routers.
- **Config** from environment variables, validated at startup by [settings.py](src/python_template/settings.py). A bad value stops the process with a list of every problem, without echoing values.
- **JSON logs** on stdout, with a request ID per request (an incoming `x-request-id` is reused). Probe requests aren't logged.
- **Container:** a multi-stage [Dockerfile](Dockerfile) with pinned base images. It runs as a non-root user, with no uv, dev tools or source tree in the runtime image.
- **CI** ([ci.yml](.github/workflows/ci.yml)): python-ci (ruff, pyright, pytest), shell-lint (shellcheck and gitleaks), a `pip-audit` of the locked production dependencies, and an image smoke test. A single `ci-ok` check sums them up.
- **Release and deploy** ([release.yml](.github/workflows/release.yml)): release-please keeps a release PR open. Merging it tags `vX.Y.Z`, and that tag is deployed to Azure Container Apps.

## Start a new service

1. Create a repo from this template (**Use this template** on GitHub, or `gh repo create <org>/<name> --template <org>/python-template --private --clone`).
2. Run the one-time setup, then commit what it changed:

   ```sh
   scripts/init.sh --team @<org>/<team>
   git add -A && git commit -m "chore: initialise from python-template"
   ```

   It renames the project and the `python_template` module (to `orders_api` for a repo named `orders-api`), records the template version in `.template-version`, sets your team as code owner, and creates the `production` environment. Pass `--dry-run` first to see what it'll do. Deploy settings can be passed now or later; see [docs/setup.md](docs/setup.md).
3. Replace the `hello` router with your own, and register a readiness check for each dependency.

Until the release app and Azure are set up, the release and deploy jobs are skipped and CI stays green.

## Develop

```sh
uv sync
uv run uvicorn python_template.app:create_app --factory --reload --port 8080
uv run ruff check && uv run ruff format --check
uv run pyright
uv run pytest
```

Copy [.env.example](.env.example) to `.env` to change settings locally.

## Health probes

| Endpoint   | Meaning                                                                                                 | Returns                                  |
| ---------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| `/healthz` | The process is up. It never checks dependencies, so a slow database can't get the container restarted. | `200 {"status":"ok"}`                    |
| `/readyz`  | Every readiness check passed and the service isn't shutting down.                                      | `200`, or `503` with each check's status |

Register a check for each dependency the service can't serve without, in the lifespan in [app.py](src/python_template/app.py):

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    database = await Database.connect(settings.database_url)
    readiness.register("database", database.ping)  # sync or async
    yield
    await database.close()
```

Checks time out after 2 s. Sync checks run in a thread, so a slow one can't block the event loop. The response gives only `ok`, `error` or `timeout` per check. Error details go to the logs, because they can name internal hosts.

On SIGTERM, `/readyz` returns 503 for `SHUTDOWN_DRAIN_MS` (5000 in the image) while the server keeps serving, then uvicorn shuts down. A second signal stops it at once. Point the Container App's liveness probe at `/healthz` and its readiness probe at `/readyz`.

## Configuration

| Variable            | Default       | Notes                                                 |
| ------------------- | ------------- | ----------------------------------------------------- |
| `PORT`              | `8080`        |                                                       |
| `LOG_LEVEL`         | `info`        | `critical`, `error`, `warning`, `info` or `debug`     |
| `ENVIRONMENT`       | `development` | `development`, `test` or `production` (in the image)  |
| `SHUTDOWN_DRAIN_MS` | `0`           | `5000` in the image                                   |

Add new variables as fields on `Settings` in [settings.py](src/python_template/settings.py).

## Not included

There's no auth, database, OpenTelemetry or rate limiting, because those choices differ per service.

## Keeping up with the template

A repo created from a template has no link back to it. Dependabot keeps dependencies, the base images and the workflow-catalog pins current. For anything else, compare `.template-version` against the template's [CHANGELOG](CHANGELOG.md) and copy what you need.

## Docs

- [docs/setup.md](docs/setup.md): org prerequisites and per-repo setup
- [docs/adr/](docs/adr/): decisions behind this template
- [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md)
