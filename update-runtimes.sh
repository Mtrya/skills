#!/usr/bin/env bash
# Install/update runtimes and let their own installers manage companion skills.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "Usage: $0 {lark|hf|hyperframes|all}"
}

if [[ $# -eq 1 && ( $1 == --help || $1 == -h ) ]]; then
  usage
  exit 0
fi
if [[ $# -ne 1 ]]; then
  usage >&2
  exit 2
fi
case "$1" in
  lark|hf|hyperframes) runtimes=("$1") ;;
  all) runtimes=(lark hf hyperframes) ;;
  *) usage >&2; exit 2 ;;
esac

# Detach old repository links before an upstream installer can write through them.
detach_repo_links() {
  local source="$1" skill_root link
  for skill_root in "$HOME/.agents/skills" "$HOME/.claude/skills" "${CODEX_HOME:-$HOME/.codex}/skills"; do
    for link in "$skill_root"/*; do
      [[ -L "$link" ]] || continue
      case "$(readlink "$link")" in
        "$source"|"$source"/*)
          rm "$link"
          echo "detached: $link"
          ;;
      esac
    done
  done
}

for runtime in "${runtimes[@]}"; do
  echo "Updating $runtime and its skills..."
  case "$runtime" in
    lark)
      detach_repo_links "$REPO/lark"
      if command -v lark-cli >/dev/null 2>&1; then
        lark-cli update --force
      else
        # Non-interactive installation omits app configuration and login.
        npx --yes @larksuite/cli@latest install </dev/null
      fi
      ;;
    hf)
      uv tool install --upgrade huggingface_hub
      detach_repo_links "$REPO/tools/hf-cli"
      "$(uv tool dir --bin)/hf" skills add hf-cli --global --force
      ;;
    hyperframes)
      npm install --global hyperframes@latest
      "$(npm prefix --global)/bin/hyperframes" skills update
      ;;
  esac
done
