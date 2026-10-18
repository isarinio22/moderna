"""Content-addressed HTTP cache.

Keyed by a stable hash of the whole request, so the cache survives across runs
and machines. This is what makes the pipeline genuinely offline after a first
run, and what makes a fresh clone reproducible: the responses for the default
sample are committed as a cache seed.

List bodies are sorted before hashing, so requesting the same sample IDs in a
different order hits the same cache entry rather than forking it.
"""

from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neoag.util.hashing import canonical_json, digest


def _canonicalise(body: Any) -> Any:
    """Normalise a request body so equivalent requests hash identically."""
    if isinstance(body, dict):
        return {k: _canonicalise(v) for k, v in sorted(body.items())}
    if isinstance(body, list):
        canonical = [_canonicalise(v) for v in body]
        try:
            return sorted(canonical, key=canonical_json)
        except TypeError:
            return canonical
    return body


@dataclass(frozen=True)
class CacheKey:
    method: str
    url: str
    params: dict[str, str] | None = None
    body: Any = None

    def digest(self) -> str:
        return digest(
            {
                "method": self.method.upper(),
                "url": self.url,
                "params": _canonicalise(self.params or {}),
                "body": _canonicalise(self.body),
            }
        )


@dataclass(frozen=True)
class CachedResponse:
    status: int
    url: str
    body: Any
    fetched_utc: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "status": self.status,
                "url": self.url,
                "body": self.body,
                "fetched_utc": self.fetched_utc,
            },
            sort_keys=True,
            ensure_ascii=False,
        )

    @staticmethod
    def from_json(text: str) -> CachedResponse:
        d = json.loads(text)
        return CachedResponse(d["status"], d["url"], d["body"], d["fetched_utc"])


class HttpCache:
    """Gzipped JSON responses on disk, sharded by digest prefix."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for(self, key: CacheKey) -> Path:
        d = key.digest()
        return self.root / d[:2] / f"{d}.json.gz"

    def get(self, key: CacheKey) -> CachedResponse | None:
        path = self.path_for(key)
        if not path.exists():
            return None
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return CachedResponse.from_json(fh.read())

    def put(self, key: CacheKey, response: CachedResponse) -> None:
        """Store a response. Only successful responses should reach here."""
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as fh:
            fh.write(response.to_json())
        os.replace(tmp, path)

    def seed_from(self, seed_dir: Path) -> int:
        """Copy committed responses into the cache, skipping any already present.

        Lets a fresh clone reproduce the real sample with no network access.
        """
        if not seed_dir.exists():
            return 0
        copied = 0
        for src in seed_dir.rglob("*.json.gz"):
            dst = self.root / src.relative_to(seed_dir)
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            copied += 1
        return copied
