#!/usr/bin/env bash
# Example: Parse a single PDF from URL
# Usage: ./examples/parse_single.sh

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Parse a PDF from URL ==="
"$SCRIPT_DIR/scripts/mineru-parse.sh" \
    "https://arxiv.org/pdf/2301.00001.pdf" \
    --model hybrid \
    --output /tmp/mineru-example \
    --extract

echo ""
echo "=== Done! Check /tmp/mineru-example/ for results ==="
