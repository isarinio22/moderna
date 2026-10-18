"""Reading and writing stage artifacts.

Two invariants:

* **Atomic writes.** Write to a temporary file, then rename. An interrupted run
  leaves the previous artifact intact rather than a half-written one that the
  next stage would happily parse.
* **Canonical serialisation.** Sorted keys, fixed separators, trailing newline.
  Two runs producing the same data produce byte-identical files, so ``git diff``
  shows real changes rather than key-order churn.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from neoag.provenance import Provenance
from neoag.util.hashing import digest_file

M = TypeVar("M", bound=BaseModel)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def meta_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".meta.json")


def write_json(path: Path, model: BaseModel, provenance: Provenance | None = None) -> None:
    """Write a model as canonical JSON, with a provenance sidecar."""
    _atomic_write_text(path, canonical_dumps(model.model_dump(mode="json")))
    if provenance is not None:
        _atomic_write_text(meta_path(path), canonical_dumps(provenance.model_dump(mode="json")))


def read_json(path: Path, model_cls: type[M]) -> M:
    """Read and validate a model from canonical JSON."""
    return model_cls.model_validate(json.loads(path.read_text(encoding="utf-8")))


def write_jsonl(path: Path, models: list[BaseModel], provenance: Provenance | None = None) -> None:
    """Write one model per line, for streams large enough that one blob is unwieldy."""
    lines = [
        json.dumps(
            m.model_dump(mode="json"), sort_keys=True,
            ensure_ascii=False, separators=(",", ":"),
        )
        for m in models
    ]
    _atomic_write_text(path, "\n".join(lines) + ("\n" if lines else ""))
    if provenance is not None:
        _atomic_write_text(meta_path(path), canonical_dumps(provenance.model_dump(mode="json")))


def read_jsonl(path: Path, model_cls: type[M]) -> list[M]:
    text = path.read_text(encoding="utf-8")
    return [
        model_cls.model_validate(json.loads(line))
        for line in text.splitlines()
        if line.strip()
    ]


def read_provenance(path: Path) -> Provenance | None:
    mp = meta_path(path)
    return Provenance.model_validate(json.loads(mp.read_text())) if mp.exists() else None


def fingerprint(path: Path) -> str:
    """Content hash of an artifact, recorded by downstream stages."""
    return digest_file(path)
