#!/usr/bin/env bash
# One timer cycle: publish machine edits for review and reconcile accepted or
# rejected PRs. All pushes name the machine branch explicitly, never main.
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
seen() { grep -qxF "$1" "$STATE" 2>/dev/null; }
remember() { seen "$1" || echo "$1" >> "$STATE"; }
dirty() { [ -n "$(git status --porcelain)" ]; }

exec 9>"$REPO/.git/skills-sync.lock"
flock -n 9 || exit 0

git check-ref-format "refs/heads/$BRANCH" >/dev/null || die "invalid SYNC_ID: $ID"
git config user.name >/dev/null && git config user.email >/dev/null ||
  die "git user.name / user.email are not configured; see machine-setup.md"
case "${1:-}" in ""|discard) ;; *) die "usage: sync.sh [discard]" ;; esac

remote_url="$(git config --get remote.origin.url)"
gh_mode=0
case "$remote_url" in
  git@github.com:*|ssh://git@github.com/*|https://github.com/*) gh_mode=1 ;;
esac
if [ "$gh_mode" = 1 ]; then
  command -v gh >/dev/null || die "gh CLI is required for a GitHub origin"
fi

# The latest PR is the lifecycle being reconciled. Historical rejections
# never apply to a later PR. Lookups assign in the parent shell so failures
# cannot masquerade as an empty (safe-to-delete) result.
read_pr() {
  local result
  pr_number="" pr_state="" pr_head="" pr_merge="" pr_owner=""
  [ "$gh_mode" = 1 ] || return 0
  result="$(gh pr list --head "$BRANCH" --base main --state all --limit 1 \
    --json number,state,headRefOid,mergeCommit,body --jq \
    '.[0] | if . == null then "" else [.number, .state, (.headRefOid | select(. != "") // "-"), (.mergeCommit.oid // "-"), ((.body | try capture("<!-- skills-sync-owner: (?<owner>[a-f0-9-]+) -->").owner) // "-")] | @tsv end')" ||
    die "cannot determine the state of PRs for $BRANCH; cycle aborted"
  if [ -n "$result" ]; then
    IFS=$'\t' read -r pr_number pr_state pr_head pr_merge pr_owner <<< "$result"
  fi
}

owner=""
[ ! -f "$IDENTITY" ] || owner="$(cat "$IDENTITY")"
check_pr_owner() {
  if [ -n "$pr_number" ] && { [ -z "$owner" ] || [ "$pr_owner" != "$owner" ]; }; then
    die "$BRANCH has no matching machine ownership; choose a unique SYNC_ID or migrate ownership explicitly"
  fi
}

# Fetch the exact branch snapshot used by our leases; a network failure is
# never interpreted as a deleted branch. Save the previous snapshot first.
old_remote="$(git rev-parse --verify --quiet "refs/remotes/origin/$BRANCH" || true)"
git fetch -q --prune origin || die "could not fetch origin"
remote_head="$(git rev-parse --verify --quiet "refs/remotes/origin/$BRANCH" || true)"
if [ -n "$remote_head" ]; then
  remote_owner="$(git log -1 --format=%B --fixed-strings \
    --grep="Skills-Sync-Owner: $ID " "$remote_head" | while IFS= read -r line; do
      case "$line" in "Skills-Sync-Owner: $ID "*) printf '%s\n' "${line#"Skills-Sync-Owner: $ID "}" ;; esac
    done)"
  if [ -z "$owner" ] || [ "$remote_owner" != "$owner" ]; then
    die "$BRANCH belongs to another or unrecorded machine; choose a unique SYNC_ID or migrate ownership explicitly"
  fi
fi
read_pr
check_pr_owner

if [ "$(git branch --show-current)" != "$BRANCH" ]; then
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git checkout -q "$BRANCH"
  else
    git switch -q -c "$BRANCH" main
  fi
fi
# Only advance the local main mirror; local divergence requires a decision.
git fetch -q origin main:main || die "could not fast-forward local main to origin/main"

reconcile_links() {
  if [ ! -f "$LINKED" ] || [ "$(cat "$LINKED")" != "$(git rev-parse HEAD)" ]; then
    bash "$REPO/link.sh" >/dev/null || die "link.sh failed; will retry next cycle"
    git rev-parse HEAD > "$LINKED"
  fi
}

delete_remote() {
  if [ -n "$remote_head" ]; then
    git push -q --force-with-lease="refs/heads/$BRANCH:$remote_head" origin ":refs/heads/$BRANCH"
    remote_head=""
  fi
}

discard_local() {
  git reset -q --hard main
  git clean -fd
  delete_remote
  reconcile_links
}

if [ "${1:-}" = discard ]; then
  discard_local
  if [ "$pr_state" = CLOSED ]; then remember "rejected:$pr_number"; fi
  note "done: local changes discarded"
  exit 0
fi

if [ "$pr_state" = CLOSED ] && ! seen "rejected:$pr_number"; then
  rejected_number="$pr_number"
  # Reopening before this final check cancels the rejection. GitHub and Git
  # cannot provide an atomic transaction across this check and the reset.
  read_pr
  check_pr_owner
  if [ "$pr_state" = CLOSED ] && [ "$pr_number" = "$rejected_number" ]; then
    discard_local
    remember "rejected:$pr_number"
    note "done: PR #$pr_number rejected; local changes discarded"
    exit 0
  fi
fi

ensure_identity() {
  if [ -z "$owner" ]; then
    owner="$(cat /proc/sys/kernel/random/uuid)"
    printf '%s\n' "$owner" > "$IDENTITY"
  fi
}

if dirty; then
  ensure_identity
  git add -A
  if ! git diff --cached --quiet; then
    git commit -q -m "sync($ID): publish local changes" -m "Skills-Sync-Owner: $ID $owner"
  fi
fi

# Rebase failure always restores the pre-rebase work. The caller decides
# whether it can publish safely (main conflict) or must leave the remote alone.
replay() {
  if ! git rebase "$@" >/dev/null; then
    git rebase --abort
    return 1
  fi
}

report_conflict() {
  local key="conflict:$(git rev-parse main)"
  if [ "$gh_mode" = 1 ] && [ "$pr_state" = OPEN ] && ! seen "$key"; then
    gh pr comment "$pr_number" --body "Sync on $ID conflicts with upstream main ($(git rev-parse --short main)) or PR adjustments. Local work is preserved on $BRANCH. Resolve the conflict, or close this PR to discard this machine's work." >/dev/null
    remember "$key"
  fi
  die "rebase conflicts; local work preserved, resolve the conflict or close the PR"
}

# A merged PR can contain web edits this clone has never fetched, even if
# GitHub has already deleted its branch. Its pull ref preserves that boundary.
adoption_head="$remote_head"
if [ "$pr_state" = MERGED ] && ! seen "merged:$pr_number"; then
  if [ "$pr_head" = - ] || ! git cat-file -e "$pr_head^{commit}" 2>/dev/null; then
    git fetch -q origin "refs/pull/$pr_number/head"
    pr_head="$(git rev-parse FETCH_HEAD)"
  fi
  [ -n "$adoption_head" ] || adoption_head="$pr_head"
fi

# Use the previous remote tip as the replay boundary even after a force
# push, so newer local commits survive remote history adjustments.
if [ -n "$adoption_head" ] && [ "$(git rev-parse HEAD)" != "$adoption_head" ]; then
  if [ -n "$old_remote" ] && git merge-base --is-ancestor "$old_remote" HEAD; then
    replay --onto "$adoption_head" "$old_remote" || report_conflict
  else
    replay "$adoption_head" || report_conflict
  fi
fi

# Squash/rebase merges do not preserve the individual commit identities.
# Drop the merged PR's entire prefix onto its merge result first. A later
# upstream conflict can then be published as a new PR without the old prefix.
main_conflict=0
if [ "$pr_state" = MERGED ] && ! seen "merged:$pr_number"; then
  git merge-base --is-ancestor "$pr_merge" main ||
    die "PR merge is not yet in fetched main; retry next cycle"
  if git merge-base --is-ancestor "$pr_head" HEAD; then
    if replay --onto "$pr_merge" "$pr_head"; then
      remember "merged:$pr_number"
    else
      # Do not publish the merged prefix again on failure.
      report_conflict
    fi
  elif git merge-base --is-ancestor "$pr_merge" HEAD; then
    remember "merged:$pr_number"
  else
    die "cannot locate merged PR boundary in local history; work preserved"
  fi
fi
replay main || main_conflict=1

# Successful pull-only and rejection cycles reconcile installations too.
if [ "$(git rev-parse HEAD)" = "$(git rev-parse main)" ]; then
  read_pr
  check_pr_owner
  if [ "$pr_state" != OPEN ]; then delete_remote; fi
  reconcile_links
  exit 0
fi

# Check again before publication: closing/merging during this cycle must
# not resurrect the old PR. The next cycle reconciles that decision.
read_pr
check_pr_owner
if { [ "$pr_state" = CLOSED ] && ! seen "rejected:$pr_number"; } ||
   { [ "$pr_state" = MERGED ] && ! seen "merged:$pr_number"; }; then
  die "PR changed while syncing; work preserved for the next cycle"
fi

# An ownership trailer survives ordinary PR-page edits regardless of author.
# A fresh clone with the same hostname cannot adopt or overwrite this branch.
ensure_identity
if ! git log --format=%B main..HEAD | grep -qxF "Skills-Sync-Owner: $ID $owner"; then
  git commit -q --allow-empty -m "sync($ID): record machine ownership" -m "Skills-Sync-Owner: $ID $owner"
fi
published=0
if [ "$(git rev-parse HEAD)" != "$remote_head" ]; then
  git push -q --force-with-lease="refs/heads/$BRANCH:$remote_head" origin "HEAD:refs/heads/$BRANCH"
  published=1
fi

if [ "$gh_mode" = 1 ]; then
  read_pr
  check_pr_owner
  if { [ "$pr_state" = CLOSED ] && ! seen "rejected:$pr_number"; } ||
     { [ "$pr_state" = MERGED ] && ! seen "merged:$pr_number"; }; then
    die "PR changed while publishing; work preserved for the next cycle"
  fi
  if [ "$pr_state" != OPEN ] || [ "$published" = 1 ]; then
    body="$(mktemp)"
    trap 'rm -f "$body"' EXIT
    {
      echo "Local changes from \`$ID\` on \`$BRANCH\`, published for review."
      echo
      echo "<!-- skills-sync-owner: $owner -->"
      echo
      echo '## Commits'
      echo
      git log --reverse --oneline main..HEAD | sed 's/^/- /'
      echo
      echo '## Files'
      echo
      echo '```'
      git diff --stat main..HEAD
      echo '```'
    } > "$body"
    if [ "$pr_state" = OPEN ]; then
      gh pr edit "$pr_number" --body-file "$body" >/dev/null
    else
      gh pr create --base main --head "$BRANCH" --title "sync($ID): publish local changes" --body-file "$body" >/dev/null
      read_pr
      check_pr_owner
    fi
  fi
fi

[ "$main_conflict" = 0 ] || report_conflict
reconcile_links
[ "$published" = 0 ] || note "done: published $(git rev-parse --short HEAD)"
