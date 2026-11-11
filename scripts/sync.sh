#!/usr/bin/env bash
# One sync cycle between this clone and the GitHub source of truth. Local
# edits are committed to sync/<hostname> and published as that machine's
# open PR; merged upstream work is pulled and rebased automatically; a
# rejected (closed) PR makes the machine wipe its own local state. Installed
# as a systemd user timer; see machine-setup.md.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ID="${SYNC_ID:-$(hostname -s 2>/dev/null || hostname)}"
BRANCH="sync/$ID"
STATE="$REPO/.git/skills-sync.state"
IDENTITY="$REPO/.git/skills-sync.identity"
LINKED="$REPO/.git/skills-sync.linked"
cd "$REPO"

note() { echo "skills-sync[$ID]: $*"; }
die() { echo "skills-sync[$ID]: ERROR: $*" >&2; exit 1; }

exec 9>"$REPO/.git/skills-sync.lock"
flock -n 9 || exit 0

dirty() { [ -n "$(git status --porcelain)" ]; }

remote_branch_exists() {
  git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1
}

# One line of the machine's PR: "number mergedAt" (mergedAt empty when the
# PR is unmerged). A gh failure aborts the cycle; a successful lookup with
# no PR prints an empty line.
gh_pr_state() {
  local result
  result="$(gh pr list --head "$BRANCH" --state "$1" --json number,mergedAt \
    --jq '.[0] | if . == null then "" else "\(.number) \(.mergedAt)" end')" ||
    die "cannot determine the state of PRs for $BRANCH; cycle aborted"
  printf '%s\n' "$result"
}

discard_local() {
  note "discarding local state back to main"
  git reset --hard main
  git clean -fd
  if remote_branch_exists; then
    git push origin --delete "$BRANCH"
  fi
}

rebase_onto() {
  local onto="$1"
  if [ "$(git rev-parse HEAD)" = "$(git rev-parse "$onto")" ]; then
    return 0
  fi
  if ! git rebase "$onto"; then
    git rebase --abort 2>/dev/null || true
    local message="Rebase onto $onto ($(git rev-parse --short "$onto")) conflicts with local changes on $ID. Local changes are preserved on $BRANCH; resolve them on this machine, or reject them by closing the PR."
    if [ "$gh_mode" = 1 ]; then
      local key="conflict:$onto:$(git rev-parse "$onto")"
      if ! grep -qxF "$key" "$STATE" 2>/dev/null; then
        local number
        number="$(gh pr list --head "$BRANCH" --state open --json number --jq '.[0].number' 2>/dev/null || true)"
        if [ -n "$number" ]; then
          gh pr comment "$number" --body "$message"
        else
          gh issue create --title "skills-sync($ID): rebase conflict" --body "$message" >/dev/null
        fi
        echo "$key" >> "$STATE"
      fi
    else
      note "$message"
    fi
    die "rebase onto $onto conflicts; resolve locally or reject the PR"
  fi
}

# (rejected | none) for the machine's closed PRs: "rejected" means at least
# one closed, unmerged PR exists.
rejection_status() {
  local result line
  result="$(gh pr list --head "$BRANCH" --state closed --json number,mergedAt \
    --jq '[.[] | select(.mergedAt == null)] | length')" ||
    die "cannot determine the state of PRs for $BRANCH; cycle aborted"
  [ "$result" != "0" ] && echo rejected || echo none
}

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  die "$REPO is not a git working tree"
fi
if ! git config user.name >/dev/null || ! git config user.email >/dev/null; then
  die "git user.name / user.email are not configured; see machine-setup.md step 1"
fi

# The machine branch always starts from main, never from whatever happens to
# be checked out (first sync on a clone can sit on any branch).
if [ "$(git branch --show-current)" != "$BRANCH" ]; then
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git checkout "$BRANCH"
  else
    git switch -c "$BRANCH" main
  fi
fi

remote_url="$(git remote get-url origin)"
case "$remote_url" in
  git@github.com:*|ssh://git@github.com/*|https://github.com/*) gh_mode=1 ;;
  *)
    gh_mode=0
    note "origin is not GitHub (${remote_url%%@*}@...); PR operations are skipped"
    ;;
esac
if [ "$gh_mode" = 1 ] && ! command -v gh >/dev/null 2>&1; then
  die "gh CLI is required for a GitHub origin; see machine-setup.md step 3"
fi

case "${1:-}" in
  discard)
    git fetch --prune origin main:main 2>/dev/null ||
      die "could not fast-forward local main to origin/main"
    discard_local
    note "done: local changes discarded"
    exit 0
    ;;
  "")
    ;;
  *)
    die "usage: sync.sh [discard]"
    ;;
esac

# Pull side: move the main mirror to origin/main, fast-forward only. A
# failure here means local main has diverged, which no automation fixes.
if ! git fetch --prune origin main:main 2>/dev/null; then
  die "could not fast-forward local main to origin/main; has local main diverged?"
fi

# A rejected (closed, unmerged) PR wipes the local state, unless there is
# nothing left to wipe.
delta=false
if dirty; then delta=true; fi
if [ "$(git rev-parse HEAD)" != "$(git rev-parse main)" ]; then delta=true; fi
if remote_branch_exists; then delta=true; fi
rejected_baseline=no
if [ "$gh_mode" = 1 ] && [ "$(rejection_status)" = rejected ]; then
  rejected_baseline=yes
fi
if [ "$gh_mode" = 1 ] && [ "$delta" = true ] && [ "$rejected_baseline" = yes ] &&
  [ -z "$(gh_pr_state OPEN)" ]; then
  # Re-check just before acting: a reopen between the check and the wipe
  # must abort the discard, not race it.
  if [ -z "$(gh_pr_state OPEN)" ] && [ "$(rejection_status)" = rejected ]; then
    discard_local
    note "done: PR was rejected; local changes discarded"
    exit 0
  fi
fi

# Push side, step 1: commit whatever is lying around in the work tree.
if dirty; then
  git add -A
  if ! git diff --cached --quiet; then
    git commit -q -m "sync($ID): publish local changes"
  fi
fi

# Push side, step 2: adopt adjustments pushed to the machine branch from
# elsewhere (e.g. edited in the PR on github.com), then converge onto main.
# Commits already merged upstream become empty here and drop away. A rewound
# remote branch (rewritten history) is adopted as-is.
old_remote="$(git rev-parse --verify --quiet "refs/remotes/origin/$BRANCH" 2>/dev/null || true)"
git fetch --prune --force origin "$BRANCH" 2>/dev/null || true
remote_head="$(git rev-parse --verify --quiet "refs/remotes/origin/$BRANCH" 2>/dev/null || true)"
if [ -n "$remote_head" ] && [ -n "$old_remote" ] &&
  ! git merge-base --is-ancestor "$old_remote" "$remote_head" 2>/dev/null; then
  note "remote $BRANCH was rewound; adopting the rewritten history"
  git reset --hard "$remote_head"
fi
if [ -n "$remote_head" ]; then
  rebase_onto "refs/remotes/origin/$BRANCH"
fi
rebase_onto "main"

# Nothing local left to publish: tidy the remote branch if its PR is gone.
if [ "$(git rev-parse HEAD)" = "$(git rev-parse main)" ]; then
  if [ "$gh_mode" = 1 ] && remote_branch_exists && [ -z "$(gh_pr_state OPEN)" ]; then
    git push origin --delete "$BRANCH"
  fi
  note "done: no local changes to publish"
  exit 0
fi

# Two machines sharing one short hostname would share this branch and PR;
# refuse to adopt the remote branch if another identity owns it.
if [ "$gh_mode" = 1 ] && [ -n "$remote_head" ] && [ -n "$old_remote" ] && [ -f "$IDENTITY" ]; then
  current_identity="$(git config user.name) <$(git config user.email)>"
  recorded="$(cat "$IDENTITY")"
  if [ "$recorded" != "$current_identity" ] && git cat-file -e "$old_remote^{commit}" 2>/dev/null &&
    [ "$(git log -1 --format='%an <%ae>' "$old_remote")" != "$current_identity" ]; then
    die "remote $BRANCH was last pushed by another identity ('$recorded'); this machine cannot publish under it"
  fi
  echo "$current_identity" > "$IDENTITY"
fi

git push --force-with-lease origin "$BRANCH:refs/heads/$BRANCH"

if [ "$gh_mode" = 1 ]; then
  body="$(mktemp)"
  {
    echo "Local changes from \`$ID\` accumulated on \`$BRANCH\`, published for review."
    echo
    echo "## Commits"
    echo
    git log --reverse --oneline main..HEAD | sed 's/^/- /'
    echo
    echo "## Files"
    echo
    echo '```'
    git diff --stat main..HEAD
    echo '```'
  } > "$body"
  open="$(gh_pr_state OPEN)"
  if [ -n "$open" ]; then
    gh pr edit "${open%% *}" --body-file "$body" >/dev/null
  else
    # A PR that was open at cycle start but is closed-unmerged now was
    # rejected while we published; recreating it would resurrect rejected
    # changes, so keep them local for the next cycle. Historical rejected
    # PRs (already handled above) do not block publishing.
    if [ "$rejected_baseline" = no ] && [ "$(rejection_status)" = rejected ]; then
      rm -f "$body"
      note "PR was rejected while publishing; changes kept for the next cycle"
      exit 1
    fi
    gh pr create --head "$BRANCH" --title "sync($ID): publish local changes" \
      --body-file "$body" >/dev/null
  fi
  rm -f "$body"
fi

# Pulls can add or remove skills; keep ~/.agents/skills in step with the
# tracked set. A successful link records what it covered.
if git diff --quiet HEAD -- research tools deprecated && [ -f "$LINKED" ] &&
  [ "$(cat "$LINKED")" = "$(git rev-parse HEAD)" ]; then
  :
else
  if bash "$REPO/link.sh" >/dev/null; then
    git rev-parse HEAD > "$LINKED"
  else
    note "link.sh failed; re-run it after the next sync"
  fi
fi

note "done: published $(git rev-parse --short HEAD)"