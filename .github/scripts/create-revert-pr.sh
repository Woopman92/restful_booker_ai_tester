#!/usr/bin/env bash
# Propose the inverse of a failed main update without modifying main directly.
set -euo pipefail

branch="revert/failed-main-${FAILED_SHA}"

if [[ "$BEFORE_SHA" =~ ^0+$ ]]; then
  echo "::error::Cannot revert the initial creation of main automatically."
  exit 1
fi

# Only merged PRs are eligible; direct pushes and merged revert PRs need review.
original_pr=$(gh api "repos/${GH_REPO}/commits/${FAILED_SHA}/pulls" \
  --paginate --jq ".[] | select(.merged_at != null and .base.ref == \"main\" and .merge_commit_sha == \"${FAILED_SHA}\") | .number" | head -n 1)
if [[ -z "$original_pr" ]]; then
  echo "::warning::No merged PR matches the failed commit; no revert PR was created."
  exit 0
fi

original_branch=$(gh pr view "$original_pr" --json headRefName --jq .headRefName)
if [[ "$original_branch" == revert/failed-main-* ]]; then
  echo "::warning::The failed update is already an automatic revert; no further revert was proposed."
  exit 0
fi

existing_pr=$(gh pr list --base main --head "$branch" --state all --json url --jq '.[0].url // empty')
if [[ -n "$existing_pr" ]]; then
  echo "Revert PR already exists: ${existing_pr}"
  exit 0
fi

git fetch origin main
git merge-base --is-ancestor "$BEFORE_SHA" "$FAILED_SHA"
git merge-base --is-ancestor "$FAILED_SHA" origin/main
git switch --create "$branch" origin/main
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'

# First-parent traversal selects the whole update for merge, squash, and rebase.
while read -r commit; do
  parents=$(git rev-list --parents --max-count=1 "$commit")
  read -ra revisions <<< "$parents"
  if (( ${#revisions[@]} > 2 )); then
    git revert --no-commit -m 1 "$commit"
  else
    git revert --no-commit "$commit"
  fi
done < <(git rev-list --first-parent "${BEFORE_SHA}..${FAILED_SHA}")

if git diff --cached --quiet; then
  echo "::notice::The failed update has no remaining changes to revert."
  exit 0
fi

git commit -m "revert: propose rollback of PR #${original_pr}"

# A previous attempt may have pushed the branch before PR creation failed.
if git ls-remote --exit-code --heads origin "$branch" > /dev/null; then
  echo "Reusing the existing revert branch: ${branch}"
else
  git push origin "HEAD:refs/heads/${branch}"
fi

body_file=$(mktemp)
trap 'rm -f "$body_file"' EXIT
cat > "$body_file" <<EOF
The post-merge API test workflow failed after PR #${original_pr}.

- Failed commit: ${FAILED_SHA}
- Workflow run: ${RUN_URL}
- Reverted update: ${BEFORE_SHA}..${FAILED_SHA}

This PR proposes a revert for manual review. A failed run may reflect a service,
build, or infrastructure issue rather than a regression. Inspect the run before
deciding whether to merge; this workflow never approves or merges the PR.

The branch was pushed with GITHUB_TOKEN, so push-triggered CI does not start
automatically. Run the API tests workflow manually against this branch before
merging. If that branch does not contain workflow_dispatch support, publish a
reviewed commit to it to trigger the normal push checks instead.
EOF

gh pr create --base main --head "$branch" \
  --title "revert: propose rollback of PR #${original_pr}" --body-file "$body_file"
