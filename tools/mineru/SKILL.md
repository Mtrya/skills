---
name: mineru
description: MinerU document parsing API - convert PDF/DOC/PPT/images to Markdown/JSON. Supports OCR, formula recognition, table extraction, and batch processing.
---

# MinerU API Skill

## Overview
MinerU converts PDF, DOC, DOCX, PPT, PPTX, PNG, JPG, JPEG, HTML into machine-readable Markdown/JSON. Supports OCR (109 languages), formula/table recognition, cross-page table merging, and batch processing.

**Mode:** Cloud API at `https://mineru.net/api/v4` (token-based).

## Authentication (Cloud API)

- **Token file**: `~/.config/mineru/token`
- **Header**: `Authorization: Bearer <token>`
- **Get token**: https://mineru.net/apiManage/token

```bash
mkdir -p ~/.config/mineru
echo "YOUR_TOKEN" > ~/.config/mineru/token
chmod 600 ~/.config/mineru/token
```

## Default Agent Workflow

When a user asks to parse a document and save the result:

1. Use a temporary artifact directory by default, for example `/tmp/mineru-<task-or-source-id>`. Download and extract the MinerU zip there.
2. Do not leave zip files, JSON sidecars, images, or full extracted directories in the user's target directory unless the user explicitly asks for them.
3. Inspect the extracted Markdown and copy only the desired final artifact to the target location. In most requests, this is the main Markdown transcript (`full.md` or the first `.md` file).
4. Rename the copied Markdown to something meaningful. Prefer a slug derived from the first level-one Markdown title. If there is no usable title, derive the name from the source filename, URL basename, arXiv id, DOI, or task id.
5. Keep the filename filesystem-safe: lowercase when natural, replace spaces with hyphens, remove shell-sensitive punctuation, and use `.md`.
6. Avoid printing the Markdown body to stdout unless the user asks to see it.

Example:

```bash
tmp_dir="/tmp/mineru-1811.12114"
target_dir="$PWD"

mineru-parse.sh https://arxiv.org/pdf/1811.12114 --model pipeline --output "$tmp_dir" --extract

md_file=$(find "$tmp_dir" -type f -name '*.md' -print -quit)
title=$(sed -n 's/^# //p' "$md_file" | head -1)
# Derive a safe slug from the title, then copy only the final Markdown artifact.
cp "$md_file" "$target_dir/a-mixed-integer-linear-programming-model-for-multi-satellite-scheduling.md"
```

## Limits (Cloud API)

| Item | Limit |
|------|-------|
| Single file size | 200MB max |
| Single file pages | 600 pages max |
| Daily priority pages | 2000 pages/account |
| Batch upload | 200 files/request |
| Token validity | 90 days |

## Model Versions

| Model | Use Case | Speed | Notes |
|-------|----------|-------|-------|
| `hybrid` | **Default since v2.7.0** — best of pipeline + vlm | Medium | Recommended for most use |
| `pipeline` | General documents, CPU-friendly | Fast | Pure CPU support |
| `vlm` | Complex layouts, higher accuracy | Slower | Higher-accuracy cloud model |
| `MinerU-HTML` | HTML output, preserves formatting | Medium | For web content |

## API Endpoints (Cloud)

Base URL: `https://mineru.net/api/v4`

### 1. Create Extraction Task (Single File)
```
POST /extract/task
```

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| url | string | yes | - | File URL (no direct upload) |
| model_version | string | no | hybrid | `hybrid` / `pipeline` / `vlm` / `MinerU-HTML` |
| is_ocr | bool | no | false | Enable OCR |
| enable_formula | bool | no | true | Formula recognition |
| enable_table | bool | no | true | Table recognition |
| language | string | no | ch | Document language |
| data_id | string | no | - | Custom identifier |
| page_ranges | string | no | - | e.g. "2,4-6" |
| callback | string | no | - | Callback URL for async results |
| extra_formats | array | no | - | `["docx"]`, `["html"]`, `["latex"]` |

**Response:**
```json
{"code": 0, "data": {"task_id": "xxx"}, "msg": "ok"}
```

### 2. Get Task Results
```
GET /extract/task/{task_id}
```

**States:** `pending` → `running` → `done` / `failed` / `converting`

**Done response:** includes `full_zip_url` (download link)

### 3. Batch Upload Local Files
```
POST /file-urls/batch
```
Returns presigned upload URLs (valid 24h). System auto-submits extraction after upload.

### 4. Batch URL Extraction
```
POST /extract/task/batch
```
Submit multiple URLs at once, returns `batch_id`.

### 5. Batch Results
```
GET /extract-results/batch/{batch_id}
```

## Error Codes

| Code | Issue | Fix |
|------|-------|-----|
| A0202 | Token invalid | Check Bearer prefix and token |
| A0211 | Token expired | Recreate at mineru.net |
| -60002 | Unrecognized format | Check file extension |
| -60005 | File too large | Max 200MB |
| -60006 | Too many pages | Max 600, split document |
| -60008 | URL timeout | Check URL accessibility |
| -60012 | Task not found | Verify task_id |

## Helper Script

`~/.claude/skills/mineru/scripts/mineru-parse.sh` — submit a document and wait for results.

`~/.claude/skills/mineru/scripts/mineru-poll.sh` — resume polling an existing task or batch ID and download results.

```bash
# URL mode
mineru-parse.sh https://example.com/doc.pdf

# Local file with options
mineru-parse.sh /path/to/file.pdf --model vlm --ocr --output /tmp/result

# Extra formats
mineru-parse.sh doc.pdf --format docx --format latex

# Page ranges
mineru-parse.sh doc.pdf --pages "1-5,8" --output ./results

# Auto-extract markdown from zip
mineru-parse.sh doc.pdf --output ./results --extract

# Resume a task and copy the first Markdown file
mineru-poll.sh <task_id> --output ./results --filename paper --extract --copy-md ./paper.md
```

## Quick Parse (Python)

```python
import requests, time

TOKEN = open("~/.config/mineru/token").read().strip()
BASE = "https://mineru.net/api/v4"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def parse_document(url, model="hybrid", ocr=False, extra_formats=None):
    """Parse a document from URL, return download link."""
    body = {
        "url": url, "model_version": model,
        "is_ocr": ocr, "enable_formula": True, "enable_table": True,
    }
    if extra_formats:
        body["extra_formats"] = extra_formats

    resp = requests.post(f"{BASE}/extract/task", headers=HEADERS, json=body)
    task_id = resp.json()["data"]["task_id"]

    while True:
        result = requests.get(f"{BASE}/extract/task/{task_id}", headers=HEADERS).json()
        state = result["data"]["state"]
        if state == "done":
            return result["data"]["full_zip_url"]
        elif state == "failed":
            raise Exception(f"Task failed: {result}")
        time.sleep(5)
```

## Quick Parse (curl)

```bash
TOKEN=$(cat ~/.config/mineru/token)

# Submit
curl -s -X POST "https://mineru.net/api/v4/extract/task" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/doc.pdf","model_version":"hybrid"}'

# Check result
curl -s "https://mineru.net/api/v4/extract/task/{task_id}" \
  -H "Authorization: Bearer $TOKEN"
```
