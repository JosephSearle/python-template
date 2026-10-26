# Production image. Build: docker build -t app . Run: docker run -p 8080:8080 app

# Pinned bases. Dependabot bumps the tag and digest together.
FROM ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff AS uv
FROM python:3.15.1-slim-trixie@sha256:533b0b2f9b5d46fd097091cf826f27902f1d6c3bca714b6dc74551356aa97a51 AS base
WORKDIR /app

# Build the virtualenv from the lockfile, without dev dependencies.
FROM base AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
	UV_LINK_MODE=copy \
	UV_PYTHON_DOWNLOADS=never
# Dependencies first, so code changes don't invalidate this layer.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM base AS runtime
ENV PATH=/app/.venv/bin:$PATH \
	PYTHONUNBUFFERED=1 \
	ENVIRONMENT=production \
	PORT=8080 \
	SHUTDOWN_DRAIN_MS=5000
# Files stay owned by root, so the app can't modify its own code. No uv or source in the image:
# the project is installed into the virtualenv.
COPY --from=build /app/.venv ./.venv
# A fixed non-root user, by number so runtimes can verify it isn't root.
USER 1000:1000
EXPOSE 8080
# Python runs as PID 1 and handles SIGTERM itself (DrainingServer), so no init wrapper is needed.
CMD ["python", "-m", "python_template"]
