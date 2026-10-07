#!/usr/bin/env bash
# MinerU Document Parser - CLI helper
# Usage: mineru-parse.sh <url_or_file> [options]
#
# Examples:
#   mineru-parse.sh https://example.com/doc.pdf
#   mineru-parse.sh https://example.com/doc.pdf --model vlm --ocr
#   mineru-parse.sh /path/to/local.pdf
#   mineru-parse.sh /path/to/local.pdf --output /tmp/result --extract
#   mineru-parse.sh doc.pdf --format docx --format latex
#   mineru-parse.sh doc.pdf --pages "1-5,8" --callback https://hook.example.com

set -euo pipefail

# ─── Configuration ─────────────────────────────────────────────
TOKEN_FILE="${MINERU_TOKEN_FILE:-$HOME/.config/mineru/token}"
BASE_URL="https://mineru.net/api/v4"
POLL_INTERVAL="${MINERU_POLL_INTERVAL:-5}"
MAX_POLL="${MINERU_MAX_POLL:-360}"  # 30 min max

# ─── Defaults ──────────────────────────────────────────────────
MODEL="hybrid"
OCR=false
FORMULA=true
TABLE=true
OUTPUT_DIR=""
PAGE_RANGES=""
CALLBACK=""
EXTRACT=false
EXTRA_FORMATS=()
DATA_ID=""
QUIET=false

# ─── Colors ────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
else
    GREEN=''; YELLOW=''; RED=''; CYAN=''; BOLD=''; NC=''
fi

log()   { [[ "$QUIET" == true ]] && return; echo -e "${CYAN}>>>${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*" >&2; }
error() { echo -e "${RED}✖${NC}  $*" >&2; exit 1; }
ok()    { echo -e "${GREEN}✔${NC}  $*"; }

# ─── Usage ─────────────────────────────────────────────────────
usage() {
    cat <<EOF
${BOLD}MinerU Document Parser${NC}

${BOLD}Usage:${NC} mineru-parse.sh <url_or_file> [options]

${BOLD}Arguments:${NC}
  url_or_file        URL to a document or local file path

${BOLD}Options:${NC}
  --model <m>        Model: hybrid (default), pipeline, vlm, MinerU-HTML
  --ocr              Enable OCR mode
  --no-formula       Disable formula recognition
  --no-table         Disable table recognition
  --output <dir>     Download results to this directory
  --extract          Auto-extract zip and show markdown content
  --pages <range>    Page ranges, e.g. "1-5,8"
  --format <fmt>     Extra output format: docx, html, latex (repeatable)
  --callback <url>   Webhook URL for async notification
  --data-id <id>     Custom identifier for tracking
  --quiet            Suppress progress output
  -h, --help         Show this help

${BOLD}Environment Variables:${NC}
  MINERU_TOKEN_FILE   Token file path (default: ~/.config/mineru/token)
  MINERU_POLL_INTERVAL  Poll interval in seconds (default: 5)
  MINERU_MAX_POLL     Max poll attempts (default: 360)

${BOLD}Supported formats:${NC} PDF, DOC, DOCX, PPT, PPTX, PNG, JPG, JPEG, HTML

${BOLD}Models:${NC}
  hybrid     Best of pipeline + vlm (default, recommended)
  pipeline   CPU-friendly, fast
  vlm        Higher accuracy, needs GPU
  MinerU-HTML  Preserves HTML formatting

${BOLD}Examples:${NC}
  mineru-parse.sh https://arxiv.org/pdf/2301.00001.pdf
  mineru-parse.sh paper.pdf --model vlm --ocr --output ./parsed
  mineru-parse.sh report.pdf --format docx --format html --extract
  mineru-parse.sh slides.pptx --pages "1-10" --output ./out
EOF
    exit 0
}

# ─── Check dependencies ───────────────────────────────────────
for cmd in curl jq; do
    command -v "$cmd" &>/dev/null || error "$cmd is required but not installed"
done

# ─── Check token ───────────────────────────────────────────────
if [[ ! -f "$TOKEN_FILE" ]]; then
    error "Token not found at $TOKEN_FILE
  Get one at: https://mineru.net/apiManage/token
  Then run:   mkdir -p ~/.config/mineru && echo 'YOUR_TOKEN' > $TOKEN_FILE && chmod 600 $TOKEN_FILE"
fi
TOKEN=$(cat "$TOKEN_FILE")

# ─── Parse args ────────────────────────────────────────────────
INPUT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --model) MODEL="$2"; shift 2 ;;
        --ocr) OCR=true; shift ;;
        --no-formula) FORMULA=false; shift ;;
        --no-table) TABLE=false; shift ;;
        --output) OUTPUT_DIR="$2"; shift 2 ;;
        --extract) EXTRACT=true; shift ;;
        --pages) PAGE_RANGES="$2"; shift 2 ;;
        --format) EXTRA_FORMATS+=("$2"); shift 2 ;;
        --callback) CALLBACK="$2"; shift 2 ;;
        --data-id) DATA_ID="$2"; shift 2 ;;
        --quiet) QUIET=true; shift ;;
        -*) error "Unknown option: $1" ;;
        *) INPUT="$1"; shift ;;
    esac
done

[[ -z "$INPUT" ]] && error "No input file or URL provided. Use -h for help."

AUTH_HEADER="Authorization: Bearer $TOKEN"

# ─── Helper: build JSON body ──────────────────────────────────
build_task_json() {
    local url="$1"
    local json
    json=$(jq -n \
        --arg url "$url" \
        --arg model "$MODEL" \
        --argjson ocr "$OCR" \
        --argjson formula "$FORMULA" \
        --argjson table "$TABLE" \
        --arg pages "$PAGE_RANGES" \
        --arg callback "$CALLBACK" \
        --arg data_id "$DATA_ID" \
        '{
            url: $url,
            model_version: $model,
            is_ocr: $ocr,
            enable_formula: $formula,
            enable_table: $table
        }
        + (if $pages != "" then {page_ranges: $pages} else {} end)
        + (if $callback != "" then {callback: $callback} else {} end)
        + (if $data_id != "" then {data_id: $data_id} else {} end)')

    # Add extra_formats array if specified
    if [[ ${#EXTRA_FORMATS[@]} -gt 0 ]]; then
        local fmts
        fmts=$(printf '%s\n' "${EXTRA_FORMATS[@]}" | jq -R . | jq -s .)
        json=$(echo "$json" | jq --argjson fmts "$fmts" '. + {extra_formats: $fmts}')
    fi

    echo "$json"
}

# ─── Helper: API call with error handling ─────────────────────
api_call() {
    local method="$1" url="$2"
    shift 2
    local resp http_code body

    resp=$(curl -s -w "\n%{http_code}" "$@" -X "$method" "$url" \
        -H "$AUTH_HEADER" -H "Content-Type: application/json")

    http_code=$(echo "$resp" | tail -1)
    body=$(echo "$resp" | sed '$d')

    if [[ "$http_code" -ge 400 ]]; then
        error "API error (HTTP $http_code): $body"
    fi

    local code
    code=$(echo "$body" | jq -r '.code // 0')
    if [[ "$code" != "0" ]]; then
        local msg
        msg=$(echo "$body" | jq -r '.msg // "unknown error"')
        error "API error ($code): $msg"
    fi

    echo "$body"
}

# ─── Helper: download and optionally extract ──────────────────
download_result() {
    local zip_url="$1" filename="$2"

    if [[ -z "$OUTPUT_DIR" ]]; then
        ok "Download URL: $zip_url"
        return
    fi

    mkdir -p "$OUTPUT_DIR"
    local out_file="$OUTPUT_DIR/${filename%.*}_result.zip"
    curl -s -o "$out_file" "$zip_url"
    ok "Saved to: $out_file"

    if [[ "$EXTRACT" == true ]]; then
        local extract_dir="$OUTPUT_DIR/${filename%.*}"
        mkdir -p "$extract_dir"
        unzip -qo "$out_file" -d "$extract_dir"
        ok "Extracted to: $extract_dir"

        # Show markdown content if found
        local md_file
        md_file=$(find "$extract_dir" -name "*.md" -type f | head -1)
        if [[ -n "$md_file" ]]; then
            echo ""
            echo -e "${BOLD}─── Markdown Output ───${NC}"
            cat "$md_file"
            echo ""
            echo -e "${BOLD}───────────────────────${NC}"
            ok "Markdown file: $md_file"
        fi

        # List all extracted files
        log "Extracted files:"
        find "$extract_dir" -type f | while read -r f; do
            echo "    $(basename "$f")"
        done
    fi
}

# ─── Helper: poll with progress ───────────────────────────────
poll_progress() {
    local kind="$1"  # "task" or "batch"
    local id="$2"
    local filename="$3"
    local attempt=0

    log "Polling for results..."
    while [[ $attempt -lt $MAX_POLL ]]; do
        ((++attempt))

        if [[ "$kind" == "task" ]]; then
            local result
            result=$(curl -s "$BASE_URL/extract/task/$id" -H "$AUTH_HEADER")
            local state
            state=$(echo "$result" | jq -r '.data.state')

            case "$state" in
                done)
                    ok "Done!"
                    local zip_url
                    zip_url=$(echo "$result" | jq -r '.data.full_zip_url')
                    download_result "$zip_url" "$filename"
                    return 0
                    ;;
                failed)
                    error "Task failed: $(echo "$result" | jq -c '.data')"
                    ;;
                *)
                    local pages total
                    pages=$(echo "$result" | jq -r '.data.extracted_page_count // "?"')
                    total=$(echo "$result" | jq -r '.data.total_page_count // "?"')
                    log "[$state] $pages/$total pages... (${attempt}/${MAX_POLL})"
                    ;;
            esac

        elif [[ "$kind" == "batch" ]]; then
            local result
            result=$(curl -s "$BASE_URL/extract-results/batch/$id" -H "$AUTH_HEADER")
            local state
            state=$(echo "$result" | jq -r '.data.extract_result[0].state')

            case "$state" in
                done)
                    ok "Done!"
                    local zip_url
                    zip_url=$(echo "$result" | jq -r '.data.extract_result[0].full_zip_url')
                    download_result "$zip_url" "$filename"
                    return 0
                    ;;
                failed)
                    error "Task failed: $(echo "$result" | jq -c '.data.extract_result[0]')"
                    ;;
                *)
                    local pages total
                    pages=$(echo "$result" | jq -r '.data.extract_result[0].extracted_page_count // "?"')
                    total=$(echo "$result" | jq -r '.data.extract_result[0].page_count // "?"')
                    log "[$state] $pages/$total pages... (${attempt}/${MAX_POLL})"
                    ;;
            esac
        fi

        sleep "$POLL_INTERVAL"
    done

    error "Timed out after $((MAX_POLL * POLL_INTERVAL)) seconds"
}

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if [[ "$INPUT" =~ ^https?:// ]]; then
    # ─── URL Mode ──────────────────────────────────────────────
    log "Submitting URL: ${BOLD}$INPUT${NC}"
    log "Model: $MODEL | OCR: $OCR | Formula: $FORMULA | Table: $TABLE"
    [[ ${#EXTRA_FORMATS[@]} -gt 0 ]] && log "Extra formats: ${EXTRA_FORMATS[*]}"

    json_body=$(build_task_json "$INPUT")

    resp=$(api_call POST "$BASE_URL/extract/task" -d "$json_body")
    task_id=$(echo "$resp" | jq -r '.data.task_id')
    ok "Task ID: $task_id"

    if [[ -n "$CALLBACK" ]]; then
        ok "Callback registered: $CALLBACK (results will be POSTed)"
        ok "Task ID: $task_id"
        exit 0
    fi

    filename=$(basename "$INPUT")
    poll_progress "task" "$task_id" "$filename"

else
    # ─── Local File Mode ───────────────────────────────────────
    [[ ! -f "$INPUT" ]] && error "File not found: $INPUT"

    filename=$(basename "$INPUT")
    filesize=$(stat -f%z "$INPUT" 2>/dev/null || stat -c%s "$INPUT" 2>/dev/null)
    filesize_mb=$((filesize / 1048576))

    [[ $filesize -gt 209715200 ]] && error "File too large (${filesize_mb}MB). Max 200MB."

    log "Uploading: ${BOLD}$filename${NC} (${filesize_mb}MB)"
    log "Model: $MODEL | OCR: $OCR | Formula: $FORMULA | Table: $TABLE"
    [[ ${#EXTRA_FORMATS[@]} -gt 0 ]] && log "Extra formats: ${EXTRA_FORMATS[*]}"

    # Build upload request body
    upload_body=$(jq -n \
        --arg name "$filename" \
        --argjson ocr "$OCR" \
        --arg model "$MODEL" \
        --argjson formula "$FORMULA" \
        --argjson table "$TABLE" \
        '{files: [{name: $name, is_ocr: $ocr, model_version: $model, enable_formula: $formula, enable_table: $table}]}')

    # Add extra_formats to upload body
    if [[ ${#EXTRA_FORMATS[@]} -gt 0 ]]; then
        local_fmts=$(printf '%s\n' "${EXTRA_FORMATS[@]}" | jq -R . | jq -s .)
        upload_body=$(echo "$upload_body" | jq --argjson fmts "$local_fmts" '.files[0] += {extra_formats: $fmts}')
    fi

    resp=$(api_call POST "$BASE_URL/file-urls/batch" -d "$upload_body")

    upload_url=$(echo "$resp" | jq -r '.data.file_urls[0].url')
    batch_id=$(echo "$resp" | jq -r '.data.batch_id')

    # Upload file
    curl -s -X PUT "$upload_url" \
        -H "Content-Type: application/octet-stream" \
        --data-binary "@$INPUT"

    ok "Uploaded. Batch ID: $batch_id"

    poll_progress "batch" "$batch_id" "$filename"
fi
