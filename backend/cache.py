"""
Disk cache utility for LLM generation and external API calls.

Keys on tuples like:
  - (prompt_version, module_id, hash_of_paper_text) for LLM calls
  - (endpoint, identifier) for metadata APIs

Features:
  - Persistent JSON disk storage in backend/cache/
  - Exponential backoff with jitter on rate limits (429 / RESOURCE_EXHAUSTED)
  - Eliminates repeated LLM costs and rate limits during development
"""

import json
import time
import hashlib
import random
import os
from pathlib import Path

# Resolve cache directory relative to backend folder
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_hash(text: str) -> str:
    """Helper to compute sha1 hash of long text strings."""
    if text is None:
        return "none"
    return hashlib.sha1(str(text).encode("utf-8")).hexdigest()[:16]


def cached(key_parts, fn):
    """
    Wrap an expensive external call (LLM / API) in a disk cache.

    key_parts: list or tuple of strings/identifiers uniquely identifying the input
    fn: callable zero-arg function that executes the actual external call
    """
    key_str = "||".join(map(str, key_parts))
    k = hashlib.sha1(key_str.encode("utf-8")).hexdigest()
    cache_file = CACHE_DIR / f"{k}.json"

    # 1. Return from disk cache if available
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass  # If corrupt, re-compute

    # 2. Execute with exponential backoff + jitter for rate limits
    for attempt in range(6):
        try:
            out = fn()
            # Save to disk cache
            cache_file.write_text(
                json.dumps(out, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return out
        except Exception as e:
            err_str = str(e)
            # Handle rate-limit errors
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "rate" in err_str.lower():
                wait = min(60, (2 ** attempt) * 2 + random.random())
                tag = str(key_parts[:2]) if len(key_parts) >= 2 else str(key_parts)
                print(f"[Cache Backoff] Rate-limited on {tag}, sleeping {wait:.1f}s (attempt {attempt + 1}/6)...")
                time.sleep(wait)
            else:
                # Fatal/other exceptions should be raised immediately
                raise e

    raise RuntimeError(f"Still rate-limited or failing after 6 attempts: {key_parts[:2]}")
