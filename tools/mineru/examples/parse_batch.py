#!/usr/bin/env python3
"""Example: Batch parse multiple documents via MinerU API.

Usage:
    python3 examples/parse_batch.py url1 url2 url3 ...
    python3 examples/parse_batch.py https://arxiv.org/pdf/2301.00001.pdf https://arxiv.org/pdf/2301.00002.pdf
"""

import os
import sys
import time
import requests

TOKEN_FILE = os.path.expanduser("~/.config/mineru/token")
BASE = os.environ.get("MINERU_API_BASE", "https://mineru.net/api/v4")


def load_token():
    if not os.path.exists(TOKEN_FILE):
        print(f"Error: Token not found at {TOKEN_FILE}")
        print("Get one at: https://mineru.net/apiManage/token")
        sys.exit(1)
    return open(TOKEN_FILE).read().strip()


def batch_parse(urls, model="hybrid"):
    """Submit multiple URLs for parsing and wait for all results."""
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Submit batch
    print(f"Submitting {len(urls)} documents...")
    resp = requests.post(
        f"{BASE}/extract/task/batch",
        headers=headers,
        json={"files": [{"url": u, "model_version": model} for u in urls]},
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        print(f"Error: {data.get('msg')}")
        sys.exit(1)

    batch_id = data["data"]["batch_id"]
    print(f"Batch ID: {batch_id}")

    # Poll for results
    while True:
        result = requests.get(
            f"{BASE}/extract-results/batch/{batch_id}", headers=headers
        ).json()
        items = result["data"]["extract_result"]
        states = [item["state"] for item in items]

        done = sum(1 for s in states if s == "done")
        failed = sum(1 for s in states if s == "failed")
        total = len(states)

        print(f"  Progress: {done}/{total} done, {failed} failed")

        if all(s in ("done", "failed") for s in states):
            break
        time.sleep(5)

    # Print results
    print("\n=== Results ===")
    for i, item in enumerate(items):
        if item["state"] == "done":
            print(f"  [{i+1}] OK: {item.get('full_zip_url', 'N/A')}")
        else:
            print(f"  [{i+1}] FAILED")

    return items


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    batch_parse(sys.argv[1:])
