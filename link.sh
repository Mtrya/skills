#!/usr/bin/env bash
# Link every skill in this repo into ~/.agents/skills so agent harnesses
# (kimi-code, Codex) discover them. Re-run after adding/retiring a skill.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.agents/skills"

mkdir -p "$DEST"

# Link each SKILL.md's parent dir, skipping deprecated/ and node_modules/.
while IFS= read -r -d '' skill_md; do
  skill_dir="$(dirname "$skill_md")"
  name="$(basename "$skill_dir")"
  target="$DEST/$name"

  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "WARNING: $target exists and is not a symlink; skipping $name" >&2
    continue
  fi

  ln -sfn "$skill_dir" "$target"
  echo "linked: $name -> $skill_dir"
done < <(find "$REPO" -name SKILL.md \
  -not -path '*/deprecated/*' \
  -not -path '*/node_modules/*' \
  -print0)

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
