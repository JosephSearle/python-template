# Setup

The template is built for a GitHub Enterprise org. Most hardening is set once at org level and applies to every repo created from the template. `scripts/init.sh` does only what has to be set per repo.

## Org prerequisites (org admins, once)

### Rulesets

Create org rulesets aimed at these repos, e.g. by a custom property such as `stack` = `node` or `python`, or at all repos:

- **`main`**, aimed at the default branch:
  - Require a pull request, with 1 approval and code-owner review. Dismiss stale approvals.
  - Required status checks: `ci-ok` and `PR title`.
  - Allowed merge methods: squash only.
  - Block force pushes and deletion.
  - Optionally **require workflows**, with CI from a central repo, so a project can't weaken its own `ci.yml`.
- **`release tags`**, aimed at tags `v*`: block creation, update and deletion, with the release app as the only bypass actor. Merging the release PR is then the only way to tag a release.

Rulesets can't set the squash commit message. Set **Default to pull request title** on each repo (Settings → General → Pull Requests), because release-please reads those titles.

### Security configuration

Apply a security configuration to new repos by default, covering Dependabot alerts and security updates, secret scanning with push protection, and CodeQL **default setup**. With default setup on, delete `.github/workflows/codeql.yml`, because GitHub rejects advanced-setup uploads while default setup is enabled. Without it, keep the file.

### Release app

Releases need a GitHub App token, because PRs created with `GITHUB_TOKEN` don't trigger CI. See [release-please.md](https://github.com/JosephSearle/workflow-catalog/blob/main/docs/release-please.md) in workflow-catalog.

1. Install the release app on the org, either for all repos or for the ones that release.
2. Org variable `RELEASE_APP_CLIENT_ID` and org secret `RELEASE_APP_PRIVATE_KEY`, both visible to those repos.

### Actions policy

If the org limits which actions can run, allow `JosephSearle/workflow-catalog/*` and the third-party actions on its [allowlist](https://github.com/JosephSearle/workflow-catalog/blob/main/docs/security.md). A called workflow's actions are checked against the caller's policy.

## Per repo (each new service)

Run `scripts/init.sh` (see the README). It:

1. Renames the project, module and README from the repo name, resets the version to 0.0.0, removes the template's CHANGELOG, and writes `.template-version`.
2. Sets the catch-all code owner to `--team`. Platform-owned paths (`.github/`, `Dockerfile`, `scripts/init.sh`) keep the platform team.
3. Creates the `production` environment, with deploys allowed from `main` only. Environments can't be set at org level.
4. Sets the `AZURE_REGISTRY`, `AZURE_RESOURCE_GROUP` and `AZURE_CONTAINER_APP` repo variables when you pass them. Deploys start once `AZURE_CONTAINER_APP` is set.

What `init.sh` can't do, which it prints at the end:

- **Azure:** create the Container App and its federated credential using [azure-container-apps.md](https://github.com/JosephSearle/workflow-catalog/blob/main/docs/azure-container-apps.md) in workflow-catalog. The subject is `repo:<org>/<repo>:environment:production`.
- **Azure IDs:** set the `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID` secrets on the `production` environment.

The deploy variables are repo variables, not environment variables, because the job that decides whether to deploy runs before the environment is entered.

## What turns each job on

| Job              | Runs when                                                   |
| ---------------- | ----------------------------------------------------------- |
| `ci` (all jobs)  | Always, plus weekly to catch new advisories                 |
| `release-please` | `RELEASE_APP_CLIENT_ID` is visible to the repo              |
| `deploy`         | A release was just created and `AZURE_CONTAINER_APP` is set |
