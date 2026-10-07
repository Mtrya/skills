#!/usr/bin/env bash
# Example: Upload and parse a local file
# Usage: ./examples/parse_local.sh /path/to/document.pdf

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INPUT="${1:?Usage: $0 <file_path>}"

echo "=== Upload and parse local file ==="
"$SCRIPT_DIR/scripts/mineru-parse.sh" \
    "$INPUT" \
    --model hybrid \
    --ocr \
    --output /tmp/mineru-local \
    --extract

echo ""
echo "=== Done! Check /tmp/mineru-local/ for results ==="
