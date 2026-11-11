# Machine setup

Hand this document to an agent running on a machine that is not yet managed, and it will make that machine a full participant in the skills-repo workflow: skills and the harness guide linked from the local clone, a sync service that publishes local changes as a per-machine PR and adopts merged upstream work, and a weekly runtime update. Perform the steps in order and run each verification before continuing. Ask the user whenever a step needs interactive input or stored credentials.

## 1. Clone the repository

Clone https://github.com/Mtrya/skills.git to `~/.agents/skills-repo`. If the directory already exists, fast-forward its local `main` to `origin/main` instead of re-cloning, and report any local commits or uncommitted changes you find rather than discarding them.

Configure a git identity for commits (clone-local config is enough): `user.name` may be the machine's hostname and `user.email` the owner's email. The sync service fails with a clear error while the identity is missing, so this cannot be skipped.

Verify: `git -C ~/.agents/skills-repo log --oneline -1` prints the newest commit on main, and `git -C ~/.agents/skills-repo config user.email` is non-empty.

## 2. Link skills and the harness guide

Run `./link.sh` in the clone. If any of `~/.kimi-code/AGENTS.md`, `~/.codex/AGENTS.md` or `~/.config/opencode/AGENTS.md` already exists as a regular file, show its diff against `agents/AGENTS.md` to the user, move it aside next to itself (`AGENTS.md.bak`), and run `./link.sh` again so the path becomes a symlink into the repo. The linker never touches a file it does not own.

Verify: `readlink ~/.kimi-code/AGENTS.md` and `readlink ~/.codex/AGENTS.md` point into `~/.agents/skills-repo`, and `ls ~/.agents/skills` shows the managed skills.

## 3. GitHub authentication

Check `gh auth status`. If not logged in, ask the user to run `gh auth login` interactively; this step cannot be automated. Then run `gh auth setup-git` so pushes over HTTPS use the gh credential helper.

Verify: `git -C ~/.agents/skills-repo ls-remote origin` succeeds without prompting.

## 4. Install the systemd user units

Copy `systemd/skills-sync.service`, `systemd/skills-sync.timer`, `systemd/runtime-update.service` and `systemd/runtime-update.timer` from the clone into `~/.config/systemd/user/`. In both `.service` files, extend the `PATH` environment line with the actual executable directories: `$(npm prefix -g)/bin` (the `bin` directory of the npm global prefix, not the prefix itself) and `$(uv tool dir --bin)` when those tools are installed, plus the directory containing the `gh` executable (`dirname "$(command -v gh)"`) so the sync service finds gh even when it lives outside the system PATH. Report any tool that is missing instead of silently dropping it. Then run `systemctl --user daemon-reload` and `systemctl --user enable --now skills-sync.timer runtime-update.timer`. If the user expects the timers to keep running after logout, run `loginctl enable-linger` for the user.

Verify: `systemctl --user list-timers` lists both timers with a next run scheduled, and `systemctl --user start skills-sync.service` completes without error; inspect its output with `journalctl --user -u skills-sync.service -n 20`.

## 5. First sync and runtime refresh

Start `skills-sync.service` once. A successful cycle with nothing to publish is silent. If the machine had pre-existing local edits in the clone, they are now published; check with `gh pr list --head "sync/$(hostname -s)"` and report the PR URL to the user for review.

Then run `./update-runtimes.sh all` to bring the companion runtimes and their skills up to date. This needs network access and may take several minutes.

Verify: `gh pr list --head "sync/$(hostname -s)"` shows the expected PR (or none on a clean machine), and `./update-runtimes.sh all --check` passes.

## Notes

- Edit a skill locally and the next cycle commits and publishes it as the machine's open PR. The timer runs every 15 minutes while the machine and user service are running; network failures retry on the next cycle.
- Merge the PR and every machine adopts main on its next successful cycle, including added and removed skill links. The publishing machine drops the merged PR's commit prefix, including squash merges, and preserves work added after that PR.
- Close the PR without merging and the next cycle resets that machine to main, removes untracked non-ignored files and deletes its remote branch. The closed PR remains on GitHub. Each rejection is acknowledged by PR number, so later edits can create a new PR. Reopening before the cycle's final rejection check cancels the discard; that check and the local reset are separate operations, so reopening after the check may be too late.
- Edits committed on the PR page are adopted before publication. Remote history rewrites replay only unpublished local commits; conflicts preserve local work for a human decision.
- A conflict with main leaves the machine's work on an open PR, where GitHub can show its conflict status, and adds one comment per upstream-main SHA, recorded in `.git/skills-sync.state`. Repeated cycles do not repeat the comment. `flock` skips overlapping cycles.
- Each clone creates `.git/skills-sync.identity` on first publication and records its token in commit trailers and the PR body. Do not copy that file to another machine. If hostnames collide, set a unique `SYNC_ID` in the service environment before first publication. Existing branches or PRs without a matching ownership marker stop before adoption or deletion; upgrading an older installation requires explicit ownership migration after verifying which machine owns the branch.
- The sync service never pushes to `main`; everything lands through a PR the user merges. Enable GitHub branch protection on `main` as a separate repository administration step.
- After updating the timer file, copy it into `~/.config/systemd/user/` again and run `systemctl --user daemon-reload` followed by `systemctl --user restart skills-sync.timer`.
- Local `main` must never receive local commits — all work happens on the checked-out `sync/<hostname>` branch, which the service manages. If local `main` has diverged, the service stops with an error and the situation needs a human decision.
