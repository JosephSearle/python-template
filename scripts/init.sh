#!/usr/bin/env bash
# One-time setup for a repo created from python-template. Run it from the repo root, then commit
# the result. Safe to run again: finished steps are skipped.
#
# Org-level settings (rulesets, security configuration, the release app's variable and secret)
# come from the org, not from here. See docs/setup.md.
set -euo pipefail

TEMPLATE=python-template
TEMPLATE_MODULE=python_template
TEMPLATE_URL=https://github.com/JosephSearle/python-template

usage() {
  cat <<EOF
Usage: scripts/init.sh [options]

  --repo OWNER/NAME      GitHub repo (default: from gh, or the origin remote)
  --name NAME            Project name (default: the repo name). The module is the same with _ for -
  --team @ORG/TEAM       Code owner for everything outside the platform-owned paths
  --registry HOST        Sets the AZURE_REGISTRY repo variable, e.g. myacr.azurecr.io
  --resource-group NAME  Sets the AZURE_RESOURCE_GROUP repo variable
  --container-app NAME   Sets the AZURE_CONTAINER_APP repo variable (this turns on deploys)
  --no-github            Only change local files
  --dry-run              Print what would change, change nothing
  -h, --help             Show this help
EOF
}

repo="" name="" team="" registry="" resource_group="" container_app=""
github=true dry_run=false

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) repo="${2:?--repo needs a value}"; shift 2 ;;
    --name) name="${2:?--name needs a value}"; shift 2 ;;
    --team) team="${2:?--team needs a value}"; shift 2 ;;
    --registry) registry="${2:?--registry needs a value}"; shift 2 ;;
    --resource-group) resource_group="${2:?--resource-group needs a value}"; shift 2 ;;
    --container-app) container_app="${2:?--container-app needs a value}"; shift 2 ;;
    --no-github) github=false; shift ;;
    --dry-run) dry_run=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# Runs a command, or prints it in a dry run.
run() {
  if "$dry_run"; then
    printf '  would run:'; printf ' %q' "$@"; printf '\n'
  else
    "$@"
  fi
}

# Replaces every literal occurrence of OLD with NEW in FILE. No regex, so names are taken as-is.
replace() {
  local file="$1" old="$2" new="$3"
  grep -qF -- "$old" "$file" || return 0
  if "$dry_run"; then
    say "  would replace '$old' with '$new' in $file"
  else
    OLD="$old" NEW="$new" perl -pi -e 's/\Q$ENV{OLD}\E/$ENV{NEW}/g' "$file"
  fi
}

[ -f pyproject.toml ] && [ -f scripts/init.sh ] || die "run this from the repo root."

if "$github"; then
  command -v gh > /dev/null || die "gh isn't installed. Install it, or pass --no-github."
  gh auth status > /dev/null 2>&1 || die "gh isn't logged in. Run 'gh auth login', or pass --no-github."
fi

if [ -z "$repo" ]; then
  if "$github"; then
    repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2> /dev/null || true)"
  fi
  if [ -z "$repo" ]; then
    remote="$(git remote get-url origin 2> /dev/null || true)"
    repo="$(printf '%s' "$remote" | sed -E 's#^.*[:/]([^/]+/[^/]+)$#\1#; s#\.git$##')"
  fi
fi
[ -n "$repo" ] || die "couldn't work out the repo. Pass --repo OWNER/NAME."
[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || die "--repo must look like OWNER/NAME, got '$repo'."

name="${name:-${repo#*/}}"
name="$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')"
[[ "$name" =~ ^[a-z][a-z0-9-]*$ ]] ||
  die "name must start with a letter and use lowercase letters, digits and dashes, got '$name'."
module="${name//-/_}"
[ "$name" != "$TEMPLATE" ] || die "this is the template itself. Run init.sh in a repo created from it."
# AZURE_CONTAINER_APP turns deploys on, so all three go together or not at all.
azure_set="${registry:+x}${resource_group:+x}${container_app:+x}"
[ -z "$azure_set" ] || [ "$azure_set" = xxx ] ||
  die "pass --registry, --resource-group and --container-app together."
[ -z "$team" ] || [[ "$team" =~ ^@[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)?$ ]] || die "--team must look like @org/team, got '$team'."

say "Repo: $repo"
say "Name: $name (module $module)"
"$dry_run" && say "Dry run: nothing will change."

step "Rename the project"
if [ -f .template-version ]; then
  say "  already done (.template-version exists)"
else
  command -v uv > /dev/null || die "uv isn't installed."
  # The template's pyproject.toml version is the template release this repo starts from.
  template_version="$(sed -nE 's/^version = "([^"]+)"$/\1/p' pyproject.toml | head -n 1)"
  [ -n "$template_version" ] || die "couldn't read the version from pyproject.toml."

  # The new project releases from 0.0.0.
  replace pyproject.toml "name = \"$TEMPLATE\"" "name = \"$name\""
  replace pyproject.toml "version = \"$template_version\"" 'version = "0.0.0"'
  replace src/$TEMPLATE_MODULE/app.py "title=\"$TEMPLATE\"" "title=\"$name\""
  if [ -d "src/$TEMPLATE_MODULE" ]; then
    run git mv "src/$TEMPLATE_MODULE" "src/$module"
  fi
  # Every import and the Dockerfile CMD use the module name.
  while IFS= read -r file; do
    replace "$file" "$TEMPLATE_MODULE" "$module"
  done < <(git ls-files src tests Dockerfile AGENTS.md README.md)
  # uv.lock records the project's name and version.
  run uv lock --quiet
  replace README.md "# $TEMPLATE" "# $name"
  if [ "$template_version" != 0.0.0 ]; then
    replace .release-please-manifest.json "\"$template_version\"" '"0.0.0"'
  fi
  # The template's changelog isn't this project's history.
  if [ -f CHANGELOG.md ]; then run rm CHANGELOG.md; fi

  if "$dry_run"; then
    say "  would write .template-version ($TEMPLATE $template_version)"
  else
    cat > .template-version <<EOF
# The approved template release this repo started from. Written once by scripts/init.sh.
# Compare against the template's CHANGELOG to see what has changed since.
template=$TEMPLATE
version=$template_version
source=$TEMPLATE_URL/releases/tag/v$template_version
initialised=$(date -u +%Y-%m-%d)
EOF
  fi
fi

step "Set the code owner"
if [ -z "$team" ]; then
  say "  skipped (no --team). The platform team owns everything until you set one."
else
  # Only the catch-all line changes. Platform-owned paths keep their owner.
  if grep -qE "^\* +$team\$" .github/CODEOWNERS; then
    say "  already $team"
  elif "$dry_run"; then
    say "  would set the catch-all owner to $team in .github/CODEOWNERS"
  else
    TEAM="$team" perl -pi -e 's/^\*(\s+)\S+$/*$1$ENV{TEAM}/' .github/CODEOWNERS
  fi
fi

if ! "$github"; then
  step "GitHub setup skipped (--no-github)"
else
  step "Create the production environment (deploys from main only)"
  run gh api --method PUT "repos/$repo/environments/production" --silent \
    --input - <<< '{"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}'
  if "$dry_run"; then
    say "  would add the 'main' branch policy"
  elif gh api "repos/$repo/environments/production/deployment-branch-policies" \
    --jq '.branch_policies[].name' | grep -qx main; then
    say "  'main' branch policy already set"
  else
    gh api --method POST "repos/$repo/environments/production/deployment-branch-policies" \
      -f name=main -f type=branch --silent
  fi

  step "Set the Azure repo variables"
  if [ -z "$container_app" ]; then
    say "  skipped (no --container-app). Deploys stay off until AZURE_CONTAINER_APP is set."
  else
    run gh variable set AZURE_REGISTRY --repo "$repo" --body "$registry"
    run gh variable set AZURE_RESOURCE_GROUP --repo "$repo" --body "$resource_group"
    # Last, so deploys turn on only once the other two are in place.
    run gh variable set AZURE_CONTAINER_APP --repo "$repo" --body "$container_app"
  fi
fi

step "Still to do by hand"
cat <<EOF
  1. Commit the changes: git add -A && git commit -m "chore: initialise from $TEMPLATE"
  2. Azure (once per app): follow docs/azure-container-apps.md in workflow-catalog. The
     federated credential subject for this repo is:
       repo:$repo:environment:production
  3. Put the Azure IDs on the production environment:
       gh secret set AZURE_CLIENT_ID --env production --repo $repo
       gh secret set AZURE_TENANT_ID --env production --repo $repo
       gh secret set AZURE_SUBSCRIPTION_ID --env production --repo $repo
  4. Check the org prerequisites in docs/setup.md are in place (rulesets, release app).
EOF
