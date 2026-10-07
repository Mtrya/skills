#!/usr/bin/env bash
# Poll an existing MinerU extraction task or batch and download the result.
# Usage: mineru-poll.sh <task_id_or_batch_id> [options]

set -euo pipefail

TOKEN_FILE="${MINERU_TOKEN_FILE:-$HOME/.config/mineru/token}"
BASE_URL="https://mineru.net/api/v4"
POLL_INTERVAL="${MINERU_POLL_INTERVAL:-5}"
MAX_POLL="${MINERU_MAX_POLL:-360}"

KIND="task"
OUTPUT_DIR=""
FILENAME="mineru_result"
EXTRACT=false
PRINT_MD=false
COPY_MD=""
QUIET=false

if [[ -t 1 ]]; then
    GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
else
    GREEN=''; YELLOW=''; RED=''; CYAN=''; BOLD=''; NC=''
fi

log()   { [[ "$QUIET" == true ]] && return; echo -e "${CYAN}>>>${NC} $*"; }
warn()  { echo -e "${YELLOW}WARN${NC} $*" >&2; }
error() { echo -e "${RED}ERROR${NC} $*" >&2; exit 1; }
ok()    { echo -e "${GREEN}OK${NC} $*"; }

usage() {
    cat <<EOF
${BOLD}MinerU Task Poller${NC}

${BOLD}Usage:${NC} mineru-poll.sh <task_id_or_batch_id> [options]

${BOLD}Options:${NC}
  --kind <task|batch>  Poll task endpoint or batch endpoint (default: task)
  --output <dir>       Download result zip to this directory
  --filename <name>    Base name for downloaded files (default: mineru_result)
  --extract            Extract the result zip after download
  --copy-md <path>     Copy the first extracted Markdown file to this path
  --print-md           Print the first extracted Markdown file to stdout
  --quiet              Suppress progress output
  -h, --help           Show this help

${BOLD}Environment Variables:${NC}
  MINERU_TOKEN_FILE    Token file path (default: ~/.config/mineru/token)
  MINERU_POLL_INTERVAL Poll interval in seconds (default: 5)
  MINERU_MAX_POLL      Max poll attempts (default: 360)
EOF
    exit 0
}

need_value() {
    local opt="$1"
    local value="${2:-}"
    [[ -n "$value" && "$value" != -* ]] || error "$opt requires a value"
}

for cmd in curl jq; do
    command -v "$cmd" &>/dev/null || error "$cmd is required but not installed"
done

[[ -f "$TOKEN_FILE" ]] || error "Token not found at $TOKEN_FILE"
TOKEN=$(<"$TOKEN_FILE")
AUTH_HEADER="Authorization: Bearer $TOKEN"

ID=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --kind) need_value "$1" "${2:-}"; KIND="$2"; shift 2 ;;
        --output) need_value "$1" "${2:-}"; OUTPUT_DIR="$2"; shift 2 ;;
        --filename) need_value "$1" "${2:-}"; FILENAME="$2"; shift 2 ;;
        --extract) EXTRACT=true; shift ;;
        --copy-md) need_value "$1" "${2:-}"; COPY_MD="$2"; EXTRACT=true; shift 2 ;;
        --print-md) PRINT_MD=true; EXTRACT=true; shift ;;
        --quiet) QUIET=true; shift ;;
        -*) error "Unknown option: $1" ;;
        *) [[ -z "$ID" ]] || error "Unexpected argument: $1"; ID="$1"; shift ;;
    esac
done

[[ -n "$ID" ]] || error "No task or batch ID provided. Use -h for help."
[[ "$KIND" == "task" || "$KIND" == "batch" ]] || error "--kind must be task or batch"
[[ "$EXTRACT" == false || -n "$OUTPUT_DIR" ]] || error "--extract requires --output"

download_and_extract() {
    local zip_url="$1"

    if [[ -z "$OUTPUT_DIR" ]]; then
        ok "Download URL: $zip_url"
        return
    fi

    mkdir -p "$OUTPUT_DIR"
    local out_file="$OUTPUT_DIR/${FILENAME}_result.zip"
    curl -L -f -sS --retry 2 --connect-timeout 10 --max-time 300 -o "$out_file" "$zip_url"
    ok "Saved to: $out_file"

    if [[ "$EXTRACT" == true ]]; then
        command -v unzip &>/dev/null || error "unzip is required for --extract"

        local extract_dir="$OUTPUT_DIR/${FILENAME}"
        mkdir -p "$extract_dir"

        if unzip -Z1 "$out_file" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
            error "Refusing to extract zip with unsafe paths"
        fi

        unzip -qo "$out_file" -d "$extract_dir"
        ok "Extracted to: $extract_dir"

        local md_file
        md_file=$(find "$extract_dir" -type f -name '*.md' -print -quit)
        if [[ -n "$md_file" ]]; then
            ok "Markdown file: $md_file"
            if [[ -n "$COPY_MD" ]]; then
                cp "$md_file" "$COPY_MD"
                ok "Copied Markdown to: $COPY_MD"
            fi
            if [[ "$PRINT_MD" == true ]]; then
                echo ""
                echo -e "${BOLD}--- Markdown Output ---${NC}"
                cat "$md_file"
                echo -e "${BOLD}-----------------------${NC}"
            fi
        else
            warn "No Markdown file found in extracted result"
        fi
    fi
}

log "Polling MinerU $KIND: $ID"
for _ in $(seq 1 "$MAX_POLL"); do
    if [[ "$KIND" == "task" ]]; then
        result=$(curl -sS "$BASE_URL/extract/task/$ID" -H "$AUTH_HEADER")
        state=$(printf '%s' "$result" | jq -r '.data.state // "unknown"')
        zip_url=$(printf '%s' "$result" | jq -r '.data.full_zip_url // ""')
        progress=$(printf '%s' "$result" | jq -r '"\(.data.extracted_page_count // "?")/\(.data.total_page_count // "?")"')
    else
        result=$(curl -sS "$BASE_URL/extract-results/batch/$ID" -H "$AUTH_HEADER")
        state=$(printf '%s' "$result" | jq -r '.data.extract_result[0].state // "unknown"')
        zip_url=$(printf '%s' "$result" | jq -r '.data.extract_result[0].full_zip_url // ""')
        progress=$(printf '%s' "$result" | jq -r '"\(.data.extract_result[0].extracted_page_count // "?")/\(.data.extract_result[0].page_count // "?")"')
    fi

    case "$state" in
        done)
            ok "Done"
            download_and_extract "$zip_url"
            exit 0
            ;;
        failed)
            printf '%s\n' "$result" | jq -c '.data'
            error "MinerU $KIND failed"
            ;;
        *)
            log "[$state] pages: $progress"
            sleep "$POLL_INTERVAL"
            ;;
    esac
done

error "Timed out after $((MAX_POLL * POLL_INTERVAL)) seconds"
