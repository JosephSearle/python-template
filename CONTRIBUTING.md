# Contributing

## Workflow

1. Branch from `main`.
2. Make the change, with tests. Run `uv run ruff check && uv run ruff format --check && uv run pyright && uv run pytest` before pushing. `pre-commit install` adds the YAML and workflow checks as a git hook.
3. Open a PR whose title is a Conventional Commit. It becomes the squash commit and drives the release:

   | Type                                               | Release |
   | -------------------------------------------------- | ------- |
   | `feat`                                             | minor   |
   | `fix`, `deps`, `perf`, `refactor`, `revert`        | patch   |
   | `!` after the type, or a `BREAKING CHANGE:` footer | major   |
   | `docs`, `ci`, `chore`, `test`                      | none    |

4. `ci-ok` and `PR title` must pass, and code owners must approve. Changes to `.github/`, `Dockerfile` or `scripts/init.sh` need platform team review.

## Releasing

Don't tag by hand. Merging the open `chore: release x.y.z` PR tags the release and deploys it.

## Changing this template

A change here changes the approved starting point for every new service. Say in the PR what existing services should copy, if anything. That text ends up in the CHANGELOG.
