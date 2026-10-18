"""Stable hashing.

Never uses :func:`hash`, which is randomised per process and would make cache
keys and record identifiers differ between runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_DIGEST_SIZE = 16


def canonical_json(obj: Any) -> str:
    """Serialise to JSON in a form that is stable across runs and platforms."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(obj: Any) -> str:
    """Return a stable hex digest of any JSON-serialisable object."""
    payload = canonical_json(obj).encode("utf-8")
    return hashlib.blake2b(payload, digest_size=_DIGEST_SIZE).hexdigest()


def digest_text(text: str) -> str:
    """Return a stable hex digest of a string."""
    return hashlib.blake2b(text.encode("utf-8"), digest_size=_DIGEST_SIZE).hexdigest()


def digest_file(path: Path) -> str:
    """Return a stable hex digest of a file's contents."""
    h = hashlib.blake2b(digest_size=_DIGEST_SIZE)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def unit_interval(*parts: str) -> float:
    """Map strings deterministically into [0, 1).

    Used by the stub predictor so that a model-free run still exercises every
    downstream code path, including ties, with reproducible pseudo-scores.
    """
    h = hashlib.blake2b("\x1f".join(parts).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big") / float(1 << 64)
