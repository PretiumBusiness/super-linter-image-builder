#!/usr/bin/env bash
# Apply the repository settings described in docs/repository-settings.md.
#
# Usage: scripts/apply-repository-settings.sh OWNER/REPO [--apply]
#
# Without --apply the script only prints what it would send. It needs the gh
# CLI, logged in as an administrator of the repository.
set -euo pipefail

repo="${1:?usage: $0 OWNER/REPO [--apply]}"
apply="${2:-}"

call() {
  local method="$1" path="$2"
  shift 2
  if [ "$apply" = "--apply" ]; then
    gh api --method "$method" "repos/${repo}/${path}" "$@"
  else
    echo "would run: gh api --method ${method} repos/${repo}/${path} $*"
  fi
}

echo "Repository merge and feature settings"
call PATCH "" \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F allow_auto_merge=false -F delete_branch_on_merge=true -F allow_update_branch=true \
  -F has_wiki=false -F has_projects=false \
  -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY

echo "GitHub Actions: pin actions to commit SHAs, read-only default token"
call PUT "actions/permissions" -F enabled=true -f allowed_actions=all -F sha_pinning_required=true
call PUT "actions/permissions/workflow" -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false

echo "Branch ruleset for the default branch"
ruleset="$(mktemp)"
trap 'rm -f "$ruleset"' EXIT
cat > "$ruleset" <<'JSON'
{
  "name": "Enforce Main Protections",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true,
        "allowed_merge_methods": ["squash"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "Lint, type-check, test" },
          { "context": "Run Super-Linter" },
          { "context": "Validate PR Title" }
        ]
      }
    }
  ]
}
JSON
call POST "rulesets" --input "$ruleset"
