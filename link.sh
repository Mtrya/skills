#!/usr/bin/env bash
# Link maintained skills into ~/.agents/skills so agent harnesses
# (kimi-code, Codex) discover them. Re-run after adding/retiring a skill.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:-$HOME/.agents/skills}"

mkdir -p "$DEST"

# Include new, untracked skills, but exclude ignored files and retired buckets.
while IFS= read -r -d '' skill_path; do
  skill_md="$REPO/$skill_path"
  [[ -f "$skill_md" ]] || continue
  skill_dir="$(dirname "$skill_md")"
  name="$(basename "$skill_dir")"
  target="$DEST/$name"

  if [ -L "$target" ]; then
    case "$(readlink "$target")" in
      "$REPO"/*) ;;
      *) echo "WARNING: $target is managed elsewhere; skipping $name" >&2; continue ;;
    esac
  elif [ -e "$target" ]; then
    echo "WARNING: $target exists and is not a symlink; skipping $name" >&2
    continue
  fi

  ln -sfn "$skill_dir" "$target"
  echo "linked: $name -> $skill_dir"
done < <(git -C "$REPO" ls-files --cached --others --exclude-standard -z -- \
  ':(glob)research/*/SKILL.md' ':(glob)tools/*/SKILL.md')

# Prune broken symlinks directly under $DEST that point into this repo
# (this is how retiring a skill to deprecated/ cleans up).
while IFS= read -r -d '' link; do
  if [ ! -e "$link" ]; then
    case "$(readlink "$link")" in
      "$REPO"/*)
        rm "$link"
        echo "pruned: $(basename "$link") (broken link into repo)"
        ;;
    esac
  fi
done < <(find "$DEST" -maxdepth 1 -type l -print0)
